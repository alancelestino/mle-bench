import argparse
import asyncio
import json
import os
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from openai import AsyncOpenAI


SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "llm_node_analysis"
# Reasonable cap for terminal output included in prompts
TERM_OUT_MAX_CHARS = 4000
# Load .env from repository root (two levels up from this script directory)
ENV_PATH = SCRIPT_DIR.parent.parent / ".env"


SYSTEM_PROMPT = r'''
Do you see any issues in the following?
You must only report issues that you are sure are unintended.
For example, the code might make assumptions, e.g., that a GPU is available, or that a certain file exists, etc.
This is OK! Don't report these as issues. Only report issues that you are sure are unintended.
Whenever possible, extract short code snippets that are relevant to the issue and explain how to fix them.
'''


def truncate_output_middle(text: str, max_chars: int = TERM_OUT_MAX_CHARS) -> str:
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    indicator = "[output truncated...]"
    if max_chars <= len(indicator):
        return indicator
    keep = max_chars - len(indicator)
    head = keep // 2
    tail = keep - head
    return text[:head] + indicator + text[-tail:]


def normalize_term_out(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        try:
            return "\n".join(
                (item if isinstance(item, str) else json.dumps(item, ensure_ascii=False))
                for item in value
            )
        except Exception:
            return json.dumps(value, ensure_ascii=False)
    if isinstance(value, (dict, int, float, bool)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def build_user_prompt(plan: str, code: str, run_analysis: str) -> str:
    return (
        "<plan>\n"
        f"{plan}\n"
        "</plan>\n\n"
        "<code>\n"
        f"{code}\n"
        "</code>\n\n"
        "<run_analysis>\n"
        f"{run_analysis}\n"
        "</run_analysis>\n"
    )


async def analyze_single_node(
    client: AsyncOpenAI,
    node: Dict[str, Any],
    id_to_node: Dict[str, Dict[str, Any]],
) -> Tuple[str, str, str]:
    node_id = str(node.get("id", "unknown"))
    parent_id: Optional[str] = node.get("parent")

    if parent_id and parent_id in id_to_node:
        parent_analysis = id_to_node[parent_id].get("analysis", "") or ""
        if not parent_analysis.strip():
            parent_analysis = "No parent node"
    else:
        parent_analysis = "No parent node"

    plan = node.get("plan", "") or ""
    code = node.get("code", "") or ""
    run_analysis = node.get("analysis", "") or ""

    user_prompt = build_user_prompt(plan=plan, code=code, run_analysis=run_analysis)

    try:
        response = await client.responses.create(
            model="gpt-5",
            input=[
                {
                    "role": "developer",
                    "content": [
                        {"type": "input_text", "text": SYSTEM_PROMPT}
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": user_prompt}
                    ],
                },
            ],
            text={
                "format": {"type": "text"},
                "verbosity": "medium",
            },
            reasoning={"effort": "low", "summary": "auto"},
            tools=[],
            store=True,
            include=[
                "reasoning.encrypted_content",
                "web_search_call.action.sources",
            ],
        )

        # Best-effort extraction of text output
        output_text = None
        try:
            output_text = response.output_text  # type: ignore[attr-defined]
        except Exception:
            pass
        if not output_text:
            try:
                # Fallback: dump full response JSON
                output_text = response.model_dump_json(indent=2)  # type: ignore[attr-defined]
            except Exception:
                output_text = str(response)

        return node_id, user_prompt, output_text
    except Exception as e:
        return node_id, user_prompt, f"ERROR during analysis: {e}"


async def bounded_worker(
    sem: asyncio.Semaphore,
    client: AsyncOpenAI,
    node: Dict[str, Any],
    id_to_node: Dict[str, Dict[str, Any]],
) -> Tuple[str, str, str]:
    async with sem:
        node_id = str(node.get("id", "unknown"))
        step = node.get("step")
        print(f"[START] Analyzing node {node_id} (step={step})", flush=True)
        result = await analyze_single_node(client, node, id_to_node)
        return result


async def main_async(input_path: Path, concurrency: int, max_nodes: int) -> None:
    # Load .env for OPENAI_API_KEY
    load_dotenv(dotenv_path=ENV_PATH)

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            f"OPENAI_API_KEY not found in {ENV_PATH}. Please set it before running."
        )

    client = AsyncOpenAI()

    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    all_nodes: List[Dict[str, Any]] = data.get("nodes", [])
    id_to_node: Dict[str, Dict[str, Any]] = {str(n.get("id")): n for n in all_nodes}

    if max_nodes > 0 and len(all_nodes) > max_nodes:
        nodes_to_process: List[Dict[str, Any]] = random.sample(all_nodes, k=max_nodes)
        print(f"[INFO] Sampling {max_nodes} of {len(all_nodes)} nodes for analysis", flush=True)
    else:
        nodes_to_process = all_nodes

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    sem = asyncio.Semaphore(concurrency)
    tasks = [
        asyncio.create_task(bounded_worker(sem, client, node, id_to_node))
        for node in nodes_to_process
    ]

    total = len(tasks)
    processed = 0
    for coro in asyncio.as_completed(tasks):
        node_id, user_prompt, text = await coro
        node_dir = OUTPUT_DIR / node_id
        node_dir.mkdir(parents=True, exist_ok=True)

        input_path = node_dir / "input.txt"
        output_path = node_dir / "output.txt"

        # Compose full input view (system + user prompts)
        input_content = (
            "System Prompt:\n" + SYSTEM_PROMPT + "\n\n" +
            "User Prompt:\n" + user_prompt + "\n"
        )

        with input_path.open("w", encoding="utf-8") as f_in:
            f_in.write(input_content)
        with output_path.open("w", encoding="utf-8") as f_out:
            f_out.write(text)

        processed += 1
        print(
            f"[DONE] ({processed}/{total}) Node {node_id} saved to {node_dir}",
            flush=True,
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Analyze LLM nodes from a JSON file and save GPT analyses per node."
        )
    )
    parser.add_argument(
        "input_json",
        type=str,
        help="Path to filtered_journal.json (or similar) containing the nodes array.",
    )
    # task_description removed from CLI
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Maximum number of concurrent GPT calls (default: 5)",
    )
    parser.add_argument(
        "--max_nodes",
        type=int,
        default=30,
        help="Maximum number of nodes to analyze; if more, sample without replacement (default: 30)",
    )
    args = parser.parse_args()

    input_path = Path(args.input_json).resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    # no task_description_path

    asyncio.run(
        main_async(
            input_path=input_path,
            concurrency=args.concurrency,
            max_nodes=args.max_nodes,
        )
    )


if __name__ == "__main__":
    main()



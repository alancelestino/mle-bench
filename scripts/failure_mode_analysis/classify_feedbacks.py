import argparse
import asyncio
import json
import os
import sys
from typing import Dict, List, Optional, Tuple


def load_env_file(env_file_path: str) -> None:
    """Load key=value pairs from a .env file into os.environ if not already set."""
    if not env_file_path or not os.path.isfile(env_file_path):
        return
    try:
        with open(env_file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except Exception:
        # Do not fail run if .env cannot be parsed; just continue
        pass


def collect_feedbacks(feedback_root_path: str) -> List[Tuple[str, str]]:
    """Collect (node_id, feedback_text) pairs.

    Primary: feedback_root_path/[node_id]/output.txt
    Fallback: feedback_root_path/*/[node_id]/output.txt (one level deeper)
    """
    if not os.path.isdir(feedback_root_path):
        raise FileNotFoundError(f"Feedback path not found: {feedback_root_path}")

    def gather_candidates_at(path: str) -> List[Tuple[str, str]]:
        results: List[Tuple[str, str]] = []
        try:
            entries = [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]
            for node_id in entries:
                output_path = os.path.join(path, node_id, "output.txt")
                if os.path.isfile(output_path):
                    results.append((node_id, output_path))
        except Exception:
            pass
        return results

    # Try immediate children first
    candidates = gather_candidates_at(feedback_root_path)

    # If none, try one level deeper
    if not candidates:
        try:
            parents = [d for d in os.listdir(feedback_root_path) if os.path.isdir(os.path.join(feedback_root_path, d))]
            for parent in parents:
                parent_path = os.path.join(feedback_root_path, parent)
                nested = gather_candidates_at(parent_path)
                if nested:
                    candidates.extend(nested)
        except Exception:
            pass

    # Sort by node_id for stable ordering
    candidates.sort(key=lambda t: t[0])

    collected: List[Tuple[str, str]] = []
    for node_id, output_path in candidates:
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                feedback_text = f.read().strip()
                if feedback_text:
                    collected.append((node_id, feedback_text))
        except Exception:
            # Skip unreadable files; continue collecting others
            continue

    if not collected:
        # Provide a helpful hint to use nested analysis dir if present
        hint = ""
        try:
            subdirs = [d for d in os.listdir(feedback_root_path) if os.path.isdir(os.path.join(feedback_root_path, d))]
            likely = [d for d in subdirs if d.lower().endswith("analysis") or "llm_node" in d.lower()]
            if likely:
                hint = f". Did you mean: {os.path.join(feedback_root_path, likely[0])}?"
        except Exception:
            pass
        raise RuntimeError(f"No feedbacks found under {feedback_root_path}/*/output.txt{hint}")

    return collected


def read_taxonomy_json(taxonomy_path: str) -> Tuple[str, Dict[str, Dict[str, List[str]]], str]:
    """Read 2-level taxonomy JSON and return (taxonomy_name, taxonomy_mapping, raw_json_str)."""
    if not taxonomy_path or not os.path.isfile(taxonomy_path):
        raise FileNotFoundError(f"taxonomy_path not found: {taxonomy_path}")
    with open(taxonomy_path, "r", encoding="utf-8") as f:
        raw = f.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid taxonomy JSON at {taxonomy_path}: {e}")

    if not isinstance(data, dict) or len(data) != 1:
        raise ValueError("Taxonomy JSON must contain exactly one top-level taxonomy name mapping to categories.")
    taxonomy_name = next(iter(data.keys()))
    taxonomy_mapping = data[taxonomy_name]
    if not isinstance(taxonomy_mapping, dict):
        raise ValueError("Top-level taxonomy must map to an object of categories.")
    # Light validation of 2-level structure
    for l1, l2_map in taxonomy_mapping.items():
        if not isinstance(l2_map, dict):
            raise ValueError(f"Category '{l1}' must map to an object of subcategories.")
        for l2, examples in l2_map.items():
            if not isinstance(examples, list):
                raise ValueError(f"Subcategory '{l2}' under '{l1}' must map to a list of example strings.")
    return taxonomy_name, taxonomy_mapping, raw.strip()


def build_prompt(feedbacks: List[Tuple[str, str]], taxonomy_name: str, taxonomy_json_str: str) -> str:
    lines: List[str] = []
    lines.append("Classify each issue mentioned in the feedbacks into a 2-level taxonomy: a top-level category (level1) and a subcategory (level2). Use the provided known taxonomy. Choose the single best level1 and level2 for each feedback. If no subcategory clearly fits, pick the closest level1 and set level2 to 'Uncategorized'.")
    lines.append("")
    lines.append("<feedbacks>")
    for idx, (node_id, text) in enumerate(feedbacks, start=1):
        lines.append(f"<feedback{idx}>")
        lines.append(f"<node_id>{node_id}</node_id>")
        lines.append(text)
        lines.append(f"</feedback{idx}>")
        lines.append("")
    lines.append("</feedbacks>")
    lines.append("")
    lines.append("<known_taxonomy_name>")
    lines.append(taxonomy_name)
    lines.append("</known_taxonomy_name>")
    lines.append("")
    lines.append("<known_taxonomy_json>")
    lines.append(taxonomy_json_str)
    lines.append("</known_taxonomy_json>")
    lines.append("")
    lines.append("Important: Do not classify entire feedbacks as a single level1 and level2. Classify each issue mentioned in the feedbacks into a 2-level taxonomy.")

    return "\n".join(lines)


async def call_gpt_async(prompt: str, taxonomy_name: str, level1_categories: List[str], client) -> Dict:
    """Async call to GPT using the provided reference request shape and return parsed JSON."""
    response = await client.responses.create(
        model="gpt-5",
        input=[
            {
                "role": "developer",
                "content": [
                    {
                        "type": "input_text",
                        "text": "You classify feedbacks into a 2-level taxonomy (level1 and level2)."
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": prompt
                    }
                ]
            }
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "taxonomy_feedback_classifications",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "taxonomy_name": {
                            "type": "string",
                            "description": "The name of the taxonomy used for classification.",
                            "enum": [taxonomy_name]
                        },
                        "classifications": {
                            "type": "array",
                            "description": "Per-feedback classification assignments.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "issue": {
                                        "type": "string",
                                        "description": "The issue extracted from the feedback."
                                    },
                                    "node_id": {
                                        "type": "string",
                                        "description": "Identifier for the node associated with this feedback."
                                    },
                                    "level1": {
                                        "type": "string",
                                        "description": "Top-level category name.",
                                        "enum": level1_categories
                                    },
                                    "level2": {
                                        "type": "string",
                                        "description": "Subcategory under level1 (or 'Uncategorized' if none clearly fits)."
                                    }
                                },
                                "required": [
                                    "issue",
                                    "node_id",
                                    "level1",
                                    "level2"
                                ],
                                "additionalProperties": False
                            }
                        }
                    },
                    "required": [
                        "taxonomy_name",
                        "classifications"
                    ],
                    "additionalProperties": False
                }
            },
            "verbosity": "medium"
        },
        reasoning={
            "effort": "low",
            "summary": "auto"
        },
        tools=[],
        store=True,
        include=[
            "reasoning.encrypted_content",
            "web_search_call.action.sources"
        ]
    )

    # Try to extract the structured JSON from the response in a robust way
    # 1) response.output_text is expected to contain the JSON string when using json_schema
    json_text: Optional[str] = None

    # Attempt common attributes in a defensive order
    for attr in ("output_text",):
        if hasattr(response, attr):
            candidate = getattr(response, attr)
            if isinstance(candidate, str) and candidate.strip():
                json_text = candidate
                break

    # Fallback: attempt to find text within response.output
    if json_text is None and hasattr(response, "output"):
        try:
            output = getattr(response, "output")
            # Expect a list of items with .content
            if isinstance(output, list):
                for item in output:
                    content = getattr(item, "content", None)
                    if isinstance(content, list):
                        for part in content:
                            text_val = getattr(part, "text", None)
                            if isinstance(text_val, str) and text_val.strip():
                                json_text = text_val
                                break
                        if json_text:
                            break
        except Exception:
            pass

    # If we found a JSON string, parse it
    if json_text:
        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            # If parsing fails, wrap raw text into an object to satisfy JSON output requirement
            return {"raw": json_text}

    # Last resort: serialize the full response object to a dictionary if possible
    try:
        # Many OpenAI SDK objects support model_dump or dict conversion
        if hasattr(response, "model_dump"):
            return {"response": response.model_dump()}
        if hasattr(response, "to_dict"):
            return {"response": response.to_dict()}  # type: ignore[attr-defined]
    except Exception:
        pass

    # Absolute fallback
    return {"error": "Unable to extract structured output from response."}


def write_json(output_dir: str, filename: str, payload: Dict) -> str:
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Concatenate feedbacks, build 2-level taxonomy prompt, and classify via GPT (async batches).")
    default_taxonomy_path = os.path.join(os.path.dirname(__file__), "default_taxonomy.json")
    default_feedback_path = os.path.join(os.path.dirname(__file__), "llm_node_analysis")
    parser.add_argument("--feedback-path", default=default_feedback_path, help="Root path containing [node_id]/output.txt feedback files. Defaults to script's folder.")
    parser.add_argument("--taxonomy-path", default=default_taxonomy_path, help="Path to a JSON 2-level taxonomy. Defaults to script's default_taxonomy.json.")
    parser.add_argument("--output-filename", default="taxonomy_classification.json", help="Output JSON filename written under feedback-path.")
    default_env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
    parser.add_argument("--env-path", default=default_env_path, help="Path to .env containing OPENAI_API_KEY.")
    parser.add_argument("--batch-size", type=int, default=3, help="Number of feedbacks per LLM call batch (default: 10).")
    parser.add_argument("--max-concurrency", type=int, default=4, help="Max number of concurrent LLM calls (default: 4).")

    args = parser.parse_args()

    # Load .env only if OPENAI_API_KEY not already set
    if not os.environ.get("OPENAI_API_KEY"):
        load_env_file(args.env_path)

    feedbacks = collect_feedbacks(args.feedback_path)
    taxonomy_name, taxonomy_map, taxonomy_raw = read_taxonomy_json(args.taxonomy_path)
    if args.taxonomy_path != default_taxonomy_path:
        print(f"Using custom taxonomy: {args.taxonomy_path}", file=sys.stderr)

    level1_categories = sorted(list(taxonomy_map.keys()))

    async def run_batches() -> Dict:
        # Import async client here to avoid hard dependency if skipped
        from openai import AsyncOpenAI
        client = AsyncOpenAI()

        # Chunk feedbacks
        def chunks(seq: List[Tuple[str, str]], size: int) -> List[List[Tuple[str, str]]]:
            return [seq[i:i + size] for i in range(0, len(seq), size)]

        semaphore = asyncio.Semaphore(max(1, args.max_concurrency))

        async def process_batch(batch: List[Tuple[str, str]]) -> Dict:
            prompt = build_prompt(batch, taxonomy_name, taxonomy_raw)
            async with semaphore:
                try:
                    return await call_gpt_async(prompt, taxonomy_name, level1_categories, client)
                except Exception as e:
                    print(f"Batch failed: {e}", file=sys.stderr)
                    return {"taxonomy_name": taxonomy_name, "classifications": []}

        tasks = [process_batch(b) for b in chunks(feedbacks, max(1, args.batch_size))]
        results = await asyncio.gather(*tasks)

        merged: List[Dict] = []
        for r in results:
            merged.extend(r.get("classifications", []))

        return {"taxonomy_name": taxonomy_name, "classifications": merged}

    final_result = asyncio.run(run_batches())
    output_path = write_json(args.feedback_path, args.output_filename, final_result)
    print(output_path)


if __name__ == "__main__":
    main()



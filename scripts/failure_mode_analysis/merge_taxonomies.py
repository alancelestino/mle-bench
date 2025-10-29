import argparse
import json
import os
from typing import Dict, List, Tuple, Set, Any


def is_taxonomy_file(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    if "taxonomy_name" not in payload or "classifications" not in payload:
        return False
    if not isinstance(payload["taxonomy_name"], str):
        return False
    if not isinstance(payload["classifications"], list):
        return False
    return True


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def gather_input_files(paths: List[str], recursive: bool) -> List[str]:
    files: List[str] = []
    for p in paths:
        if os.path.isfile(p):
            files.append(os.path.abspath(p))
        elif os.path.isdir(p):
            if recursive:
                for root, _, filenames in os.walk(p):
                    for name in filenames:
                        if name.lower().endswith(".json"):
                            files.append(os.path.abspath(os.path.join(root, name)))
            else:
                for name in os.listdir(p):
                    full = os.path.join(p, name)
                    if os.path.isfile(full) and name.lower().endswith(".json"):
                        files.append(os.path.abspath(full))
        else:
            # Skip non-existent paths
            continue
    # Stable ordering
    files = sorted(list(dict.fromkeys(files)))
    return files


def merge_taxonomies(input_files: List[str], ignore_errors: bool) -> Any:
    taxonomy_to_items: Dict[str, List[Dict[str, Any]]] = {}
    taxonomy_to_seen: Dict[str, Set[Tuple[str, str, str, str]]] = {}

    for path in input_files:
        try:
            data = load_json(path)
        except Exception:
            if ignore_errors:
                continue
            raise

        if not is_taxonomy_file(data):
            if ignore_errors:
                continue
            raise ValueError(f"Invalid taxonomy file format: {path}")

        taxonomy_name: str = data["taxonomy_name"]
        items: List[Any] = data["classifications"]

        if taxonomy_name not in taxonomy_to_items:
            taxonomy_to_items[taxonomy_name] = []
            taxonomy_to_seen[taxonomy_name] = set()

        for entry in items:
            if not isinstance(entry, dict):
                continue
            issue = str(entry.get("issue", ""))
            node_id = str(entry.get("node_id", ""))
            level1 = str(entry.get("level1", ""))
            level2 = str(entry.get("level2", ""))
            key = (node_id, issue, level1, level2)
            if key in taxonomy_to_seen[taxonomy_name]:
                continue
            taxonomy_to_seen[taxonomy_name].add(key)
            taxonomy_to_items[taxonomy_name].append(entry)

    if not taxonomy_to_items:
        raise RuntimeError("No valid taxonomy files found to merge.")

    # Sort each taxonomy's items for stability
    for tname, items in taxonomy_to_items.items():
        items.sort(key=lambda e: (str(e.get("node_id", "")), str(e.get("issue", "")).lower()))

    if len(taxonomy_to_items) == 1:
        # Preserve the single-taxonomy schema for compatibility
        tname = next(iter(taxonomy_to_items.keys()))
        return {"taxonomy_name": tname, "classifications": taxonomy_to_items[tname]}

    # Multiple taxonomies: return an aggregate payload
    return {
        "taxonomies": [
            {"taxonomy_name": tname, "classifications": taxonomy_to_items[tname]}
            for tname in sorted(taxonomy_to_items.keys())
        ]
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Merge one or more taxonomy classification JSON files (arbitrary 2-level taxonomies)."
        )
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help=(
            "Input JSON files or directories. Directories are scanned for .json files (optionally recursively)."
        ),
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recursively scan directories for JSON files.",
    )
    parser.add_argument(
        "--ignore-errors",
        action="store_true",
        help="Skip invalid/unreadable files instead of failing.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="taxonomy_classification_merged.json",
        help="Output JSON filepath (default: taxonomy_classification_merged.json).",
    )

    args = parser.parse_args()

    files = gather_input_files(args.inputs, recursive=bool(args.recursive))
    if not files:
        raise FileNotFoundError("No input JSON files found.")

    merged = merge_taxonomies(files, ignore_errors=bool(args.ignore_errors))

    out_dir = os.path.dirname(os.path.abspath(args.output)) or os.getcwd()
    os.makedirs(out_dir, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    print(os.path.abspath(args.output))


if __name__ == "__main__":
    main()



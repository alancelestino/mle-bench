#!/usr/bin/env python3
"""
Register competitions from custom_data into mlebench/competitions.

This script scans a custom dataset root (default: repo_root/custom_data),
detects dataset types (image-classification or tabular-regression), and
generates the minimal competition scaffold:
  - mlebench/competitions/<competition-id>/config.yaml
  - mlebench/competitions/<competition-id>/description.md
  - mlebench/competitions/<competition-id>/prepare.py
  - mlebench/competitions/<competition-id>/grade.py
  - mlebench/competitions/<competition-id>/leaderboard.csv (synthetic)
  - mlebench/competitions/<competition-id>/kernels.txt

Notes
- The generated prepare.py expects the data to already exist under the
  custom_data/<dataset_id>/<source_dir>/ path. It will copy into the
  registry's raw/public/private locations.
- Run scripts/prepare_custom_competitions.py afterwards to prepare data
  and generate checksums.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Optional


REPO_ROOT = Path(__file__).resolve().parents[2]
COMP_DIR = REPO_ROOT / "mlebench" / "competitions"
CUSTOM_DATA_ROOT = REPO_ROOT / "custom_data"
SPLITS_DIR = REPO_ROOT / "experiments" / "splits"


def to_competition_id(name: str) -> str:
    return name.strip().lower().replace(" ", "-").replace("_", "-")


def to_competition_name(name: str) -> str:
    return name.strip().replace("_", " ").title()


def detect_dataset_source_dir(dataset_id_dir: Path) -> Optional[Path]:
    # Pick the first subdirectory with a train.csv inside, else first non-hidden dir
    for child in sorted(dataset_id_dir.iterdir()):
        if child.is_dir() and not child.name.startswith("."):
            if (child / "train.csv").exists() or (child / "train").exists():
                return child
    for child in sorted(dataset_id_dir.iterdir()):
        if child.is_dir() and not child.name.startswith("."):
            return child
    return None


def detect_type_and_schema(src_dir: Path) -> dict:
    """
    Returns a dict with keys:
      type: "image_classification" | "tabular_regression"
      id_column: str
      target_column: str (for grading)
    """
    # Heuristics: image classification has train.csv with image_path & label columns
    train_csv = src_dir / "train.csv"
    test_csv = src_dir / "test.csv"
    golden_csv = src_dir.parent / "test_golden_answer.csv"

    if train_csv.exists():
        # Peek header only
        with open(train_csv, "r") as f:
            header = f.readline().strip().split(",")
        if {"id", "image_path", "label"}.issubset(set(header)):
            return {
                "type": "image_classification",
                "id_column": "id",
                "target_column": "label",
            }

    # Otherwise assume tabular regression if golden has a numeric-like target name
    # Minimal assumption: columns id,<target>
    if golden_csv.exists():
        with open(golden_csv, "r") as f:
            header = f.readline().strip().split(",")
        if len(header) == 2 and header[0] == "id":
            return {
                "type": "tabular_regression",
                "id_column": "id",
                "target_column": header[1],
            }

    raise ValueError(f"Unable to detect dataset type for {src_dir}")


def load_description_for_dataset(dataset_id_dir: Path) -> str:
    # Use the first instructions_*.md if present, else a generic stub
    md_files = sorted(dataset_id_dir.glob("instructions_*.md"))
    if md_files:
        return md_files[0].read_text()
    return (
        "# Custom Competition\n\n"
        "This is a custom competition registered from local data.\n"
    )


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def render_config_yaml(comp_id: str, comp_name: str, description_rel_path: str) -> str:
    return (
        f"id: {comp_id}\n"
        f"name: {comp_name}\n"
        f"competition_type: simple\n"
        f"awards_medals: true\n"
        f"prizes: null\n"
        f"description: {description_rel_path}\n\n"
        "dataset:\n"
        f"  answers: {comp_id}/prepared/private/test.csv\n"
        f"  sample_submission: {comp_id}/prepared/public/sample_submission.csv\n\n"
        "grader:\n"
        "  name: auto\n"
        f"  grade_fn: mlebench.competitions.{comp_id}.grade:grade\n\n"
        f"preparer: mlebench.competitions.{comp_id}.prepare:prepare\n"
    )


def render_grade_py_image(id_col: str, target_col: str) -> str:
    return (
        "import pandas as pd\n"
        "from sklearn.metrics import accuracy_score\n\n"
        "from mlebench.competitions.utils import prepare_for_accuracy_metric\n\n"
        "def grade(submission: pd.DataFrame, answers: pd.DataFrame) -> float:\n"
        "    inputs = prepare_for_accuracy_metric(\n"
        f"        submission=submission, answers=answers, target_column=\"{target_col}\", id_column=\"{id_col}\"\n"
        "    )\n"
        "    return accuracy_score(**inputs)\n"
    )


def render_grade_py_regression(id_col: str, target_col: str) -> str:
    return (
        "import numpy as np\n"
        "import pandas as pd\n"
        "from sklearn.metrics import mean_squared_error\n\n"
        "def _align(submission: pd.DataFrame, answers: pd.DataFrame, id_col: str, target_col: str):\n"
        "    submission = submission.sort_values(id_col)\n"
        "    answers = answers.sort_values(id_col)\n"
        "    if (submission[id_col].values != answers[id_col].values).any():\n"
        "        missing = set(answers[id_col]) - set(submission[id_col])\n"
        "        raise ValueError(f\"Submission missing ids: {missing}\")\n"
        "    y_true = answers[target_col].to_numpy(dtype=float)\n"
        "    y_pred = submission[target_col].to_numpy(dtype=float)\n"
        "    return y_true, y_pred\n\n"
        "def grade(submission: pd.DataFrame, answers: pd.DataFrame) -> float:\n"
        f"    y_true, y_pred = _align(submission, answers, id_col=\"{id_col}\", target_col=\"{target_col}\")\n"
        "    rmse = mean_squared_error(y_true, y_pred, squared=False)\n"
        "    return float(rmse)\n"
    )


def render_prepare_py(dataset_id: str, source_dir_name: str, is_image: bool, id_col: str, target_col: str) -> str:
    custom_root_expr = "Path(__file__).resolve().parents[3] / 'custom_data' / '{dataset_id}' / '{src}'"
    body = [
        'from pathlib import Path',
        'import shutil',
        'from mlebench.utils import read_csv',
        '',
        'def prepare(raw: Path, public: Path, private: Path):',
        f"    custom_data_path = {custom_root_expr.format(dataset_id=dataset_id, src=source_dir_name)}",
        '    raw.mkdir(parents=True, exist_ok=True)',
        '    public.mkdir(parents=True, exist_ok=True)',
        '    private.mkdir(parents=True, exist_ok=True)',
        '    # Copy CSVs',
        "    shutil.copy(custom_data_path / 'train.csv', raw / 'train.csv')",
        "    shutil.copy(custom_data_path / 'test.csv', raw / 'test.csv')",
        '    golden = Path(__file__).resolve().parents[3] / "custom_data" / ' + f"'{dataset_id}'" + ' / "test_golden_answer.csv"',
        "    if golden.exists():",
        "        shutil.copy(golden, raw / 'test_golden_answer.csv')",
        '    # Load for writing public/private',
        "    train_df = read_csv(raw / 'train.csv')",
        "    test_df = read_csv(raw / 'test.csv')",
        "    if (raw / 'test_golden_answer.csv').exists():",
        "        answers_df = read_csv(raw / 'test_golden_answer.csv')",
        "    else:",
        "        answers_df = None",
        '',
        '    # Sample submission',
    ]
    if is_image:
        body += [
            f"    sample = test_df[[\"{id_col}\"]].copy()",
            f"    sample['{target_col}'] = train_df['{target_col}'].mode().iat[0] if '{target_col}' in train_df.columns else ''",
        ]
    else:
        body += [
            f"    sample = test_df[[\"{id_col}\"]].copy()",
            f"    sample['{target_col}'] = 0.0",
        ]
    body += [
        "    sample.to_csv(public / 'sample_submission.csv', index=False)",
        '',
        "    # Private answers",
        "    if answers_df is not None:",
        "        answers_df.to_csv(private / 'test.csv', index=False)",
        '',
        "    # Public CSVs",
        "    train_df.to_csv(public / 'train.csv', index=False)",
        "    test_df.to_csv(public / 'test.csv', index=False)",
    ]
    if is_image:
        body += [
            "    # Copy image folders to public",
            "    if (custom_data_path / 'train').exists():",
            "        shutil.copytree(custom_data_path / 'train', public / 'train', dirs_exist_ok=True)",
            "    if (custom_data_path / 'test').exists():",
            "        shutil.copytree(custom_data_path / 'test', public / 'test', dirs_exist_ok=True)",
        ]
    return "\n".join(body) + "\n"


def render_leaderboard_csv(is_image: bool) -> str:
    if is_image:
        # Higher is better (accuracy)
        rows = [(f"team_{i}", f"{score:.3f}") for i, score in enumerate([0.98, 0.97, 0.96, 0.95, 0.94, 0.93, 0.92, 0.91, 0.90, 0.88], start=1)]
    else:
        # Lower is better (RMSE)
        rows = [(f"team_{i}", f"{score:.3f}") for i, score in enumerate([0.80, 0.85, 0.90, 0.95, 1.00, 1.10, 1.20, 1.40, 1.60, 1.80], start=1)]
    return "team_id,score\n" + "\n".join(",".join(r) for r in rows) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Register custom competitions from local data")
    parser.add_argument("--custom-root", type=str, default=str(CUSTOM_DATA_ROOT), help="Path to custom_data root")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of datasets processed")
    args = parser.parse_args()

    custom_root = Path(args.custom_root).resolve()
    assert custom_root.exists(), f"Custom root not found: {custom_root}"

    created: list[str] = []

    for idx, dataset_id_dir in enumerate(sorted(p for p in custom_root.iterdir() if p.is_dir())):
        if args.limit is not None and idx >= args.limit:
            break

        src_dir = detect_dataset_source_dir(dataset_id_dir)
        if src_dir is None:
            continue

        comp_id = to_competition_id(src_dir.name)
        comp_name = to_competition_name(src_dir.name)
        comp_dir = COMP_DIR / comp_id

        if comp_dir.exists():
            # Skip existing
            continue

        schema = detect_type_and_schema(src_dir)
        is_image = schema["type"] == "image_classification"
        id_col = schema["id_column"]
        target_col = schema["target_column"]

        description_md = load_description_for_dataset(dataset_id_dir)

        # Files
        write_file(comp_dir / "description.md", description_md)
        config_yaml = render_config_yaml(
            comp_id=comp_id,
            comp_name=comp_name,
            description_rel_path=f"mlebench/competitions/{comp_id}/description.md",
        )
        write_file(comp_dir / "config.yaml", config_yaml)

        prepare_py = render_prepare_py(
            dataset_id=dataset_id_dir.name,
            source_dir_name=src_dir.name,
            is_image=is_image,
            id_col=id_col,
            target_col=target_col,
        )
        write_file(comp_dir / "prepare.py", prepare_py)

        if is_image:
            grade_py = render_grade_py_image(id_col=id_col, target_col=target_col)
        else:
            grade_py = render_grade_py_regression(id_col=id_col, target_col=target_col)
        write_file(comp_dir / "grade.py", grade_py)

        write_file(comp_dir / "leaderboard.csv", render_leaderboard_csv(is_image=is_image))
        write_file(comp_dir / "kernels.txt", "# Add reference kernels here if desired\n")

        # Create a small split file
        write_file(SPLITS_DIR / f"{comp_id}.txt", comp_id + "\n")

        created.append(comp_id)

    print(json.dumps({"created_competitions": created}, indent=2))


if __name__ == "__main__":
    main()



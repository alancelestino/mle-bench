from pathlib import Path
import shutil
from sklearn.model_selection import train_test_split
from mlebench.utils import read_csv
import pandas as pd
import json


def prepare(raw: Path, public: Path, private: Path):
    '''
    Splits the data in raw into public and private datasets with appropriate test/train splits.
    '''
    public.mkdir(parents=True, exist_ok=True)
    private.mkdir(parents=True, exist_ok=True)
    print(public)
    print(private)

    # File paths
    train_challenges_path = raw / "arc-agi_training_challenges.json"
    train_solutions_path = raw / "arc-agi_training_solutions.json"
    eval_challenges_path = raw / "arc-agi_evaluation_challenges.json"
    eval_solutions_path = raw / "arc-agi_evaluation_solutions.json"
    sample_submission_raw = raw / "sample_submission.json"

    # Load JSON helpers
    def load_json(p: Path):
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)

    # Robust extractors to handle slight format variations
    def extract_test_input(test_entry):
        if isinstance(test_entry, dict) and "input" in test_entry:
            return test_entry["input"]
        return test_entry

    def extract_solution(sol_entry):
        if isinstance(sol_entry, dict) and "output" in sol_entry:
            return sol_entry["output"]
        return sol_entry

    def dumps(obj):
        # Compact JSON string for CSV storage
        return json.dumps(obj, separators=(",", ":"))

    # Build rows (one per task test output) from challenge+solutions
    def build_rows(challenges: dict, solutions: dict):
        rows = []
        for task_id in sorted(challenges.keys()):
            ch = challenges[task_id]
            if task_id not in solutions:
                # Skip tasks without solutions (shouldn't happen for train/eval splits)
                continue
            sols = solutions[task_id]
            # Normalize solutions to a list of outputs
            # sols can be: list of outputs or list of dicts with 'output'
            # Ensure list
            if not isinstance(sols, list):
                # unexpected, but attempt to wrap
                sols = [sols]
            test_list = ch.get("test", [])
            # Some JSONs may wrap test items as dicts with 'input'
            for i, test_item in enumerate(test_list):
                row_id = f"{task_id}_{i}"
                test_input = extract_test_input(test_item)
                # Solution at same index
                if i < len(sols):
                    sol = extract_solution(sols[i])
                else:
                    # If missing, set to empty to avoid KeyError; shouldn't happen for provided eval/train
                    sol = []
                rows.append(
                    {
                        "id": row_id,
                        "task_id": task_id,
                        "output_index": i,
                        "train": dumps(ch.get("train", [])),
                        "test_input": dumps(test_input),
                        "prediction": dumps(sol),  # ground-truth output grid
                    }
                )
        return rows

    # Load datasets
    train_challenges = load_json(train_challenges_path)
    train_solutions = load_json(train_solutions_path)
    eval_challenges = load_json(eval_challenges_path)
    eval_solutions = load_json(eval_solutions_path)

    # Build DataFrames
    train_rows = build_rows(train_challenges, train_solutions)
    eval_rows = build_rows(eval_challenges, eval_solutions)

    df_train = pd.DataFrame(train_rows)
    df_eval = pd.DataFrame(eval_rows)

    # Save public/train.csv (with labels)
    df_train.to_csv(public / "train.csv", index=False)

    # Save public/test.csv (without labels)
    df_eval_public = df_eval.drop(columns=["prediction"], errors="ignore")
    df_eval_public.to_csv(public / "test.csv", index=False)

    # Save private/test.csv (with labels)
    df_eval.to_csv(private / "test.csv", index=False)

    # Create sample_submission.csv in public
    sample_sub = df_eval_public[["id"]].copy()
    # Placeholder minimal valid JSON grid; agents should replace with predictions
    sample_sub["prediction"] =df_eval["prediction"]
    sample_sub.to_csv(public / "sample_submission.csv", index=False)

    # Optional: also place Kaggle's sample_submission.json for reference
    if sample_submission_raw.exists():
        shutil.copy2(sample_submission_raw, public / "sample_submission_kaggle.json")

    # Assertions and validation
    # Use engine='python' per robustness guidance
    pub_train = pd.read_csv(public / "train.csv", engine="python")
    pub_test = pd.read_csv(public / "test.csv", engine="python")
    prv_test = pd.read_csv(private / "test.csv", engine="python")
    sub_csv = pd.read_csv(public / "sample_submission.csv", engine="python")

    # Basic integrity checks
    assert "id" in pub_train.columns
    assert "id" in pub_test.columns
    assert "id" in prv_test.columns
    assert "prediction" in pub_train.columns  # labels available for training
    assert "prediction" not in pub_test.columns  # no labels in public test
    assert "prediction" in prv_test.columns  # labels in private test
    assert list(sub_csv.columns) == ["id", "prediction"]

    # No overlap between train and test ids
    assert set(pub_train["id"]).isdisjoint(set(pub_test["id"]))
    assert set(pub_train["id"]).isdisjoint(set(prv_test["id"]))
    # Public and private test ids should match exactly
    assert set(pub_test["id"]) == set(prv_test["id"])
    assert len(pub_test) == len(prv_test)
    assert len(pub_test) > 0 and len(pub_train) > 0

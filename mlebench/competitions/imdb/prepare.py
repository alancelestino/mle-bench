from pathlib import Path
import shutil
from typing import Iterable

import pandas as pd

from mlebench.utils import read_csv


def _list_txt_filenames(dirpath: Path) -> list[str]:
    """Return a sorted list of file names (with extension) for all .txt files directly under dirpath."""
    return sorted([p.name for p in dirpath.glob("*.txt") if p.is_file()])


def _build_train_dataframe(train_root: Path) -> pd.DataFrame:
    """Create a DataFrame with columns [id,label] from imdb train directory structure.

    - Positive reviews live under train/pos → label 1
    - Negative reviews live under train/neg → label 0
    """
    pos_dir = train_root / "pos"
    neg_dir = train_root / "neg"

    pos_files = _list_txt_filenames(pos_dir) if pos_dir.is_dir() else []
    neg_files = _list_txt_filenames(neg_dir) if neg_dir.is_dir() else []

    ids: list[str] = []
    labels: list[int] = []

    for fname in pos_files:
        ids.append(fname)
        labels.append(1)
    for fname in neg_files:
        ids.append(fname)
        labels.append(0)

    df = pd.DataFrame({"id": ids, "label": labels})
    return df


def _build_test_dataframe(test_root: Path) -> pd.DataFrame:
    """Create a DataFrame with column [id] from imdb test directory structure."""
    test_files = _list_txt_filenames(test_root) if test_root.is_dir() else []
    df = pd.DataFrame({"id": test_files})
    return df


def prepare(raw: Path, public: Path, private: Path):
    custom_data_path = Path(__file__).resolve().parents[3] / "custom_data" / "dataset_id_2" / "imdb"

    raw.mkdir(parents=True, exist_ok=True)
    public.mkdir(parents=True, exist_ok=True)
    private.mkdir(parents=True, exist_ok=True)

    # Build CSVs from directory structure if not present in custom_data
    train_dir = custom_data_path / "train"
    test_dir = custom_data_path / "test"

    train_csv = raw / "train.csv"
    test_csv = raw / "test.csv"

    train_df: pd.DataFrame
    test_df: pd.DataFrame

    # Generate train.csv
    train_df = _build_train_dataframe(train_dir)
    train_df.to_csv(train_csv, index=False)

    # Generate test.csv
    test_df = _build_test_dataframe(test_dir)
    test_df.to_csv(test_csv, index=False)

    # Copy golden answers if provided
    golden = Path(__file__).resolve().parents[3] / "custom_data" / "dataset_id_2" / "test_golden_answer.csv"
    answers_df = None
    if golden.exists():
        shutil.copy(golden, raw / "test_golden_answer.csv")
        answers_df = read_csv(raw / "test_golden_answer.csv")

    # Create sample submission (majority class baseline)
    sample = test_df[["id"]].copy()
    if not train_df.empty and "label" in train_df.columns:
        sample["label"] = int(train_df["label"].mode().iat[0])
    else:
        sample["label"] = 0
    sample.to_csv(public / "sample_submission.csv", index=False)

    # Write public copies of CSVs for agent consumption
    train_df.to_csv(public / "train.csv", index=False)
    test_df.to_csv(public / "test.csv", index=False)

    # Write private answers if available
    if answers_df is not None:
        answers_df.to_csv(private / "test.csv", index=False)

    # Also expose the original .txt review files for agents that read raw text
    imdb_public_root = public / "imdb"
    imdb_public_root.mkdir(parents=True, exist_ok=True)

    if train_dir.exists():
        shutil.copytree(train_dir, imdb_public_root / "train", dirs_exist_ok=True)
    if test_dir.exists():
        shutil.copytree(test_dir, imdb_public_root / "test", dirs_exist_ok=True)

    vocab_file = custom_data_path / "imdb.vocab"
    if vocab_file.exists():
        shutil.copy(vocab_file, imdb_public_root / "imdb.vocab")

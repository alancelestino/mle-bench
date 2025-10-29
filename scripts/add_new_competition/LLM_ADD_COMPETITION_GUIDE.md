## LLM Guide: Add and Verify a New Competition in MLE-bench

This document instructs an LLM how to add a new competition to this repo using locally provided data. Follow every step exactly; adapt only the marked placeholders.

### Inputs You Have
- A competition description file (markdown)
- Training and test data (CSV files; images if image classification)
- Golden labels for the test set (CSV), used privately for grading

### Conventions and Paths
- Repo root: the directory that contains `mlebench/` and `scripts/`
- Custom data lives under: `custom_data/<dataset_group>/<source_dir>/`
  - Required files:
    - `<source_dir>/train.csv` (or a directory tree you will convert to CSV in `prepare.py`)
    - `<source_dir>/test.csv` (or a directory tree you will convert to CSV in `prepare.py`)
    - `<dataset_group>/test_golden_answer.csv` (columns: `id,<target>`)
- Prepared data is written to the cache by default:
  - macOS: `~/Library/Caches/mle-bench/data/<competition-id>/prepared/{public,private}`
  - Linux: `~/.cache/mle-bench/data/<competition-id>/prepared/{public,private}`
  - Inside container, public data is mounted read-only at `/home/data` and private answers at `/private/data/<competition-id>/prepared/private/`

### Step 1: Pick a competition id and name
- Use a short, kebab-cased id (e.g., `freiburg-groceries`, `imdb`, `yellow-taxi-fare-prediction`).
- Use a title-cased human-readable name.

### Step 2: Create the competition directory
Create `mlebench/competitions/<competition-id>/` with these files:

1) `config.yaml` (update placeholders)
```yaml
id: <competition-id>
name: <Competition Name>
competition_type: simple
awards_medals: true
prizes: null
description: mlebench/competitions/<competition-id>/description.md

dataset:
  answers: <competition-id>/prepared/private/test.csv
  sample_submission: <competition-id>/prepared/public/sample_submission.csv

grader:
  name: auto
  grade_fn: mlebench.competitions.<competition-id>.grade:grade

preparer: mlebench.competitions.<competition-id>.prepare:prepare
```

2) `description.md`
- Copy or paste the provided problem description here. It will be shown to the agent.

3) `prepare.py` (choose the template that matches your task)

- Image classification (train.csv has columns: `id,image_path,label`; images under `train/` and `test/` folders):
```python
from pathlib import Path
import shutil
from mlebench.utils import read_csv

def prepare(raw: Path, public: Path, private: Path):
    custom_data_path = Path(__file__).resolve().parents[3] / 'custom_data' / '<dataset_group>' / '<source_dir>'
    raw.mkdir(parents=True, exist_ok=True)
    public.mkdir(parents=True, exist_ok=True)
    private.mkdir(parents=True, exist_ok=True)

    shutil.copy(custom_data_path / 'train.csv', raw / 'train.csv')
    shutil.copy(custom_data_path / 'test.csv', raw / 'test.csv')

    golden = Path(__file__).resolve().parents[3] / 'custom_data' / '<dataset_group>' / 'test_golden_answer.csv'
    if golden.exists():
        shutil.copy(golden, raw / 'test_golden_answer.csv')

    train_df = read_csv(raw / 'train.csv')
    test_df = read_csv(raw / 'test.csv')
    answers_df = read_csv(raw / 'test_golden_answer.csv') if (raw / 'test_golden_answer.csv').exists() else None

    sample = test_df[["id"]].copy()
    sample["label"] = train_df["label"].mode().iat[0]
    sample.to_csv(public / 'sample_submission.csv', index=False)

    if answers_df is not None:
        answers_df.to_csv(private / 'test.csv', index=False)

    train_df.to_csv(public / 'train.csv', index=False)
    test_df.to_csv(public / 'test.csv', index=False)

    if (custom_data_path / 'train').exists():
        shutil.copytree(custom_data_path / 'train', public / 'train', dirs_exist_ok=True)
    if (custom_data_path / 'test').exists():
        shutil.copytree(custom_data_path / 'test', public / 'test', dirs_exist_ok=True)
```

- Tabular classification (train.csv has `id,label` and optionally features; no `image_path`):
```python
from pathlib import Path
import shutil
from mlebench.utils import read_csv

def prepare(raw: Path, public: Path, private: Path):
    custom_data_path = Path(__file__).resolve().parents[3] / 'custom_data' / '<dataset_group>' / '<source_dir>'
    raw.mkdir(parents=True, exist_ok=True)
    public.mkdir(parents=True, exist_ok=True)
    private.mkdir(parents=True, exist_ok=True)

    shutil.copy(custom_data_path / 'train.csv', raw / 'train.csv')
    shutil.copy(custom_data_path / 'test.csv', raw / 'test.csv')
    golden = Path(__file__).resolve().parents[3] / 'custom_data' / '<dataset_group>' / 'test_golden_answer.csv'
    if golden.exists():
        shutil.copy(golden, raw / 'test_golden_answer.csv')

    train_df = read_csv(raw / 'train.csv')
    test_df = read_csv(raw / 'test.csv')
    answers_df = read_csv(raw / 'test_golden_answer.csv') if (raw / 'test_golden_answer.csv').exists() else None

    sample = test_df[["id"]].copy()
    sample["label"] = train_df["label"].mode().iat[0] if "label" in train_df.columns else 0
    sample.to_csv(public / 'sample_submission.csv', index=False)

    if answers_df is not None:
        answers_df.to_csv(private / 'test.csv', index=False)

    train_df.to_csv(public / 'train.csv', index=False)
    test_df.to_csv(public / 'test.csv', index=False)
```

- Tabular regression (golden has numeric target `id,<target>`):
```python
from pathlib import Path
import shutil
from mlebench.utils import read_csv

def prepare(raw: Path, public: Path, private: Path):
    custom_data_path = Path(__file__).resolve().parents[3] / 'custom_data' / '<dataset_group>' / '<source_dir>'
    raw.mkdir(parents=True, exist_ok=True)
    public.mkdir(parents=True, exist_ok=True)
    private.mkdir(parents=True, exist_ok=True)

    shutil.copy(custom_data_path / 'train.csv', raw / 'train.csv')
    shutil.copy(custom_data_path / 'test.csv', raw / 'test.csv')
    golden = Path(__file__).resolve().parents[3] / 'custom_data' / '<dataset_group>' / 'test_golden_answer.csv'
    if golden.exists():
        shutil.copy(golden, raw / 'test_golden_answer.csv')

    train_df = read_csv(raw / 'train.csv')
    test_df = read_csv(raw / 'test.csv')
    answers_df = read_csv(raw / 'test_golden_answer.csv') if (raw / 'test_golden_answer.csv').exists() else None

    target_col = (answers_df.columns[1] if answers_df is not None else 'target')
    sample = test_df[["id"]].copy()
    sample[target_col] = 0.0
    sample.to_csv(public / 'sample_submission.csv', index=False)

    if answers_df is not None:
        answers_df.to_csv(private / 'test.csv', index=False)

    train_df.to_csv(public / 'train.csv', index=False)
    test_df.to_csv(public / 'test.csv', index=False)
```

4) `grade.py` (choose the metric)

- Accuracy (classification):
```python
import pandas as pd
from sklearn.metrics import accuracy_score
from mlebench.competitions.utils import prepare_for_accuracy_metric

def grade(submission: pd.DataFrame, answers: pd.DataFrame) -> float:
    inputs = prepare_for_accuracy_metric(
        submission=submission, answers=answers, target_column="label", id_column="id"
    )
    return accuracy_score(**inputs)
```

- RMSE (regression):
```python
import pandas as pd
from sklearn.metrics import mean_squared_error

def _align(submission: pd.DataFrame, answers: pd.DataFrame, id_col: str, target_col: str):
    submission = submission.sort_values(id_col)
    answers = answers.sort_values(id_col)
    if (submission[id_col].values != answers[id_col].values).any():
        missing = set(answers[id_col]) - set(submission[id_col])
        raise ValueError(f"Submission missing ids: {missing}")
    y_true = answers[target_col].to_numpy(dtype=float)
    y_pred = submission[target_col].to_numpy(dtype=float)
    return y_true, y_pred

def grade(submission: pd.DataFrame, answers: pd.DataFrame) -> float:
    y_true, y_pred = _align(submission, answers, id_col="id", target_col="<target>")
    return float(mean_squared_error(y_true, y_pred, squared=False))
```

5) `leaderboard.csv`
- Provide 10–100 rows with a `team_id,score` column. For classification, higher is better; for regression, lower is better.

6) `kernels.txt`
- Optional: add reference notebook URLs for plagiarism checks.

### Step 3: Create a split file
Create `experiments/splits/<competition-id>.txt` with a single line:
```
<competition-id>
```

### Step 4: Prepare the dataset (no Kaggle, local-only)
Use the helper:
```bash
source .venv/bin/activate
python scripts/add_new_competition/prepare_local_competition.py -c <competition-id> --force
```
Expected output includes copying CSVs, (optionally) images, and generating checksums. Verify (Linux example):
```bash
ls -lh ~/.cache/mle-bench/data/<competition-id>/prepared/public | head
ls -lh ~/.cache/mle-bench/data/<competition-id>/prepared/private | head
```

Optional: prepare to a custom data dir (e.g., under repo):
```bash
python scripts/add_new_competition/prepare_local_competition.py -c <competition-id> --force --data-dir "$PWD/.data"
```

### Step 5: Verify grading
```bash
# Grade the sample submission to confirm metric wiring
mlebench grade-sample \
  ~/Library/Caches/mle-bench/data/<competition-id>/prepared/public/sample_submission.csv \
  <competition-id>
```
You should see a JSON report with `valid_submission: true` and a numeric `score`.

### Step 6: (Optional) Run the dummy agent
Docker must be running. On macOS, if the sysbox runtime is unavailable, set Docker runtime to `runc` in your container config.
```bash
# From repo root
python run_agent.py \
  --agent-id dummy \
  --competition-set experiments/splits/<competition-id>.txt \
  --n-workers 1 --n-seeds 1
```
If the runtime `sysbox-runc` causes an error on macOS, edit `environment/config/container_configs/default.json` to:
```json
{
  "mem_limit": null,
  "shm_size": "4G",
  "nano_cpus": 4000000000,
  "runtime": "runc"
}
```

### Step 7: Troubleshooting
- Grader wrong metric: update `grade.py` to accuracy for classification or RMSE for regression, then re-run Step 5.
- Sample submission invalid: ensure columns match the required `id` and target (`label` for classification or the numeric target column for regression).
- Paths wrong in `prepare.py`: fix the `custom_data_path` and re-run Step 4 with `--force`.
- Inside-container paths: data appears under `/home/data` (public) and private answers under `/private/data/<competition-id>/prepared/private/`. Do not hardcode other in-container paths in descriptions.
- Data not found: confirm `custom_data/<dataset_group>/<source_dir>/train.csv` and `test.csv` exist; confirm golden labels file is at `custom_data/<dataset_group>/test_golden_answer.csv`.

### Step 8: Minimal checklist (LLM must confirm)
- Competition folder created under `mlebench/competitions/<competition-id>/`
- Files present: `config.yaml`, `description.md`, `prepare.py`, `grade.py`, `leaderboard.csv`, `kernels.txt`
- Split file at `experiments/splits/<competition-id>.txt`
- Prepared data in cache `prepared/public` and `prepared/private`
- `mlebench grade-sample` runs and returns a score



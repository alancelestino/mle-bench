from pathlib import Path
import shutil
from mlebench.utils import read_csv

def prepare(raw: Path, public: Path, private: Path):
    custom_data_path = Path(__file__).resolve().parents[3] / 'custom_data' / 'dataset_id_4' / 'waste_classification'
    raw.mkdir(parents=True, exist_ok=True)
    public.mkdir(parents=True, exist_ok=True)
    private.mkdir(parents=True, exist_ok=True)
    # Copy CSVs
    shutil.copy(custom_data_path / 'train.csv', raw / 'train.csv')
    shutil.copy(custom_data_path / 'test.csv', raw / 'test.csv')
    golden = Path(__file__).resolve().parents[3] / "custom_data" / 'dataset_id_4' / "test_golden_answer.csv"
    if golden.exists():
        shutil.copy(golden, raw / 'test_golden_answer.csv')
    # Load for writing public/private
    train_df = read_csv(raw / 'train.csv')
    test_df = read_csv(raw / 'test.csv')
    if (raw / 'test_golden_answer.csv').exists():
        answers_df = read_csv(raw / 'test_golden_answer.csv')
    else:
        answers_df = None

    # Sample submission
    sample = test_df[["id"]].copy()
    sample['label'] = train_df['label'].mode().iat[0] if 'label' in train_df.columns else ''
    sample.to_csv(public / 'sample_submission.csv', index=False)

    # Private answers
    if answers_df is not None:
        answers_df.to_csv(private / 'test.csv', index=False)

    # Public CSVs
    train_df.to_csv(public / 'train.csv', index=False)
    test_df.to_csv(public / 'test.csv', index=False)
    # Copy image folders to public
    if (custom_data_path / 'train').exists():
        shutil.copytree(custom_data_path / 'train', public / 'train', dirs_exist_ok=True)
    if (custom_data_path / 'test').exists():
        shutil.copytree(custom_data_path / 'test', public / 'test', dirs_exist_ok=True)

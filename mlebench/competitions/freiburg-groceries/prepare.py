"""
Prepare the Freiburg Groceries dataset.

This is a custom competition with data already provided locally.
"""

import shutil
from pathlib import Path

from mlebench.utils import read_csv


def prepare(raw: Path, public: Path, private: Path):
    """
    Prepare the Freiburg Groceries dataset.
    
    Note: This assumes the data has already been placed in the custom_data directory.
    We will copy it from there to the raw directory if needed.
    """
    
    # Path to the custom data location
    custom_data_path = Path(__file__).parent.parent.parent.parent / "custom_data" / "dataset_id_1" / "freiburg_groceries"
    
    # If raw directory is empty, copy data from custom_data location
    if not (raw / "train.csv").exists():
        print(f"Copying data from {custom_data_path} to {raw}...")
        
        # Copy CSV files
        shutil.copy(custom_data_path / "train.csv", raw / "train.csv")
        shutil.copy(custom_data_path / "test.csv", raw / "test.csv")
        
        # Copy train images directory
        if (custom_data_path / "train").exists():
            shutil.copytree(custom_data_path / "train", raw / "train", dirs_exist_ok=True)
        
        # Copy test images directory
        if (custom_data_path / "test").exists():
            shutil.copytree(custom_data_path / "test", raw / "test", dirs_exist_ok=True)
        
        print("Data copied successfully!")
    
    # Also copy the golden labels to a known location for reference
    golden_labels_source = Path(__file__).parent.parent.parent.parent / "custom_data" / "dataset_id_1" / "test_golden_answer.csv"
    if golden_labels_source.exists() and not (raw / "test_golden_answer.csv").exists():
        shutil.copy(golden_labels_source, raw / "test_golden_answer.csv")
    
    # Read the data
    train_df = read_csv(raw / "train.csv")
    test_df = read_csv(raw / "test.csv")
    golden_labels = read_csv(raw / "test_golden_answer.csv")
    
    # For this competition, the data is already split into train and test
    # We just need to organize it for the agents
    
    # Create sample submission (all predictions as the first class)
    sample_submission = test_df[["id"]].copy()
    sample_submission["label"] = "BEANS"  # Default prediction
    sample_submission.to_csv(public / "sample_submission.csv", index=False)
    
    # Save the golden labels to private directory (for grading)
    golden_labels.to_csv(private / "test.csv", index=False)
    
    # Save public files (what the agent sees)
    train_df.to_csv(public / "train.csv", index=False)
    test_df.to_csv(public / "test.csv", index=False)
    
    # Copy image directories to public location
    # Copy train images
    if (raw / "train").exists():
        public_train = public / "train"
        if not public_train.exists():
            shutil.copytree(raw / "train", public_train)
    
    # Copy test images
    if (raw / "test").exists():
        public_test = public / "test"
        if not public_test.exists():
            shutil.copytree(raw / "test", public_test)
    
    print(f"Prepared {len(train_df)} training images and {len(test_df)} test images")
    print(f"Number of classes: {train_df['label'].nunique()}")


"""
Grading function for the Freiburg Groceries Image Classification competition.
"""

import pandas as pd
from sklearn.metrics import accuracy_score

from mlebench.competitions.utils import prepare_for_accuracy_metric


def grade(submission: pd.DataFrame, answers: pd.DataFrame) -> float:
    """
    Grade the submission using top-1 accuracy.
    
    Args:
        submission: DataFrame with columns ['id', 'label']
        answers: DataFrame with columns ['id', 'label'] (ground truth)
    
    Returns:
        accuracy: Float between 0 and 1
    """
    accuracy_inputs = prepare_for_accuracy_metric(
        submission=submission,
        answers=answers,
        target_column="label",
        id_column="id"
    )
    return accuracy_score(**accuracy_inputs)


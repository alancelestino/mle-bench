import pandas as pd
from sklearn.metrics import accuracy_score

from mlebench.competitions.utils import prepare_for_accuracy_metric


def grade(submission: pd.DataFrame, answers: pd.DataFrame) -> float:
    print("submission=", submission)
    print("answer=", answers)
    accuracy_inputs = prepare_for_accuracy_metric(submission, answers, id_column="id", target_column="prediction")
    return accuracy_score(y_true=accuracy_inputs["y_true"], y_pred=accuracy_inputs["y_pred"])

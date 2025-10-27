import numpy as np
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
    y_true, y_pred = _align(submission, answers, id_col="id", target_col="fare_amount")
    # Some older scikit-learn versions may not support squared=False; compute RMSE manually
    mse = mean_squared_error(y_true, y_pred)
    rmse = float(np.sqrt(mse))
    return rmse

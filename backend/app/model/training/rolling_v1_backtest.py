"""Rolling-origin robustness harness for Model v1.

This module deliberately separates model development from the final holdout:
- multiple chronological rolling origins
- fixed validation/calibration slice per origin
- untouched future test slice per origin
- optional final future holdout, never used for model selection

The caller supplies the already-built chronological feature rows. No rows are
shuffled and no future row is allowed into an earlier origin.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, roc_auc_score

from app.model.training.compare_v0_v1 import _matrix, _targets, _ece
from app.model.training.model_v1 import ModelV1


@dataclass(frozen=True)
class WindowResult:
    origin: int
    train_size: int
    validation_size: int
    test_size: int
    v0_log_loss: float
    v1_log_loss: float
    v0_brier: float
    v1_brier: float
    v0_auc: float
    v1_auc: float
    v0_ece: float
    v1_ece: float


def _calibrate(validation_p: np.ndarray, validation_y: np.ndarray, test_p: np.ndarray) -> np.ndarray:
    eps = 1e-6
    p = np.clip(validation_p, eps, 1 - eps)
    z = np.log(p / (1 - p)).reshape(-1, 1)
    model = LogisticRegression(max_iter=1000, random_state=0)
    model.fit(z, validation_y)
    test_z = np.log(np.clip(test_p, eps, 1 - eps) / (1 - np.clip(test_p, eps, 1 - eps))).reshape(-1, 1)
    return model.predict_proba(test_z)[:, 1]


def _metrics(y: np.ndarray, p: np.ndarray) -> tuple[float, float, float, float]:
    return (
        float(log_loss(y, p, labels=[0, 1])),
        float(brier_score_loss(y, p)),
        float(roc_auc_score(y, p)),
        float(_ece(p, y)),
    )


def run_rolling_backtest(
    rows: Sequence[dict],
    *,
    train_sizes: Sequence[int] = (1200, 1500, 1800, 2100, 2300),
    validation_size: int = 200,
    test_size: int = 200,
) -> list[WindowResult]:
    ordered = list(rows)
    results: list[WindowResult] = []
    for origin, train_size in enumerate(train_sizes, start=1):
        end = train_size + validation_size + test_size
        if end > len(ordered):
            continue
        train = ordered[:train_size]
        validation = ordered[train_size : train_size + validation_size]
        test = ordered[train_size + validation_size : end]
        y_train, y_val, y_test = _targets(train), _targets(validation), _targets(test)

        v0 = LogisticRegression(max_iter=1000, random_state=0)
        v0.fit(_matrix(train), y_train)
        v0_val = v0.predict_proba(_matrix(validation))[:, 1]
        v0_test = v0.predict_proba(_matrix(test))[:, 1]
        v0_cal = _calibrate(v0_val, y_val, v0_test)

        v1 = ModelV1().fit(train, y_train)
        v1_val = v1.predict_proba(validation)
        v1_test = v1.predict_proba(test)
        v1_cal = _calibrate(v1_val, y_val, v1_test)

        a = _metrics(y_test, v0_cal)
        b = _metrics(y_test, v1_cal)
        results.append(WindowResult(origin, train_size, validation_size, test_size, a[0], b[0], a[1], b[1], a[2], b[2], a[3], b[3]))
    return results


def future_holdout(rows: Sequence[dict], *, holdout_size: int = 300) -> list[dict]:
    """Return the final chronological holdout without fitting or tuning on it."""
    if len(rows) <= holdout_size:
        raise ValueError("not enough chronological rows for a future holdout")
    return list(rows[-holdout_size:])

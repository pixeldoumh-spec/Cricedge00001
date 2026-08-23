"""ODI O10 controlled LogisticRegression regularization sweep.

O10 changes only the regularization strength of the frozen O0 13-feature
information set. Candidate C values are frozen by the O10 contract.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Tuple

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

CANDIDATE_C = (0.25, 0.5, 1.0, 2.0, 4.0)
CONTROL_C = 1.0
MAX_ITER = 2000


@dataclass
class O10Model:
    scaler: StandardScaler
    model: LogisticRegression
    C: float


@dataclass
class O10Calibrators:
    platt: LogisticRegression
    isotonic: IsotonicRegression


def fit_o10(X_train: np.ndarray, y_train: np.ndarray, C: float) -> O10Model:
    if X_train.ndim != 2 or X_train.shape[1] != 13:
        raise ValueError("O10 requires the exact frozen O0 13-feature matrix")
    if C not in CANDIDATE_C:
        raise ValueError("O10 C must be one of the frozen contract candidates")
    scaler = StandardScaler()
    model = LogisticRegression(max_iter=MAX_ITER, C=float(C))
    model.fit(scaler.fit_transform(X_train), y_train)
    return O10Model(scaler=scaler, model=model, C=float(C))


def predict_raw(bundle: O10Model, X: np.ndarray) -> np.ndarray:
    return bundle.model.predict_proba(bundle.scaler.transform(X))[:, 1]


def select_C_by_validation_log_loss(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_validation: np.ndarray,
    y_validation: np.ndarray,
) -> Tuple[float, list[Tuple[float, float]]]:
    """Select C using validation raw log loss only."""
    from sklearn.metrics import log_loss

    scores: list[Tuple[float, float]] = []
    for C in CANDIDATE_C:
        bundle = fit_o10(X_train, y_train, C)
        p = predict_raw(bundle, X_validation)
        scores.append((float(log_loss(y_validation, p, labels=[0, 1])), C))
    best_loss, best_C = min(scores, key=lambda x: (x[0], x[1]))
    return float(best_C), scores


def fit_validation_calibrators(
    raw_validation: Sequence[float], y_validation: Sequence[int]
) -> O10Calibrators:
    p = np.asarray(raw_validation, dtype=float)
    y = np.asarray(y_validation, dtype=int)
    platt = LogisticRegression(max_iter=MAX_ITER)
    platt.fit(p.reshape(-1, 1), y)
    isotonic = IsotonicRegression(out_of_bounds="clip")
    isotonic.fit(p, y)
    return O10Calibrators(platt=platt, isotonic=isotonic)


def predict_platt(calibrator: LogisticRegression, probabilities: Sequence[float]) -> np.ndarray:
    return calibrator.predict_proba(np.asarray(probabilities).reshape(-1, 1))[:, 1]


def predict_isotonic(
    calibrator: IsotonicRegression, probabilities: Sequence[float]
) -> np.ndarray:
    return calibrator.predict(np.asarray(probabilities, dtype=float))

"""Men's ODI O14: restrained temporal non-stationarity model.

O14 extends frozen O0 with exactly three chronological interactions, chosen by
prior conditional-drift diagnostics and represented as semantic A-vs-B signed
differences. No decay, history interaction, or adaptive calibration is part of
the feature hypothesis.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from .odi_o0_features import FEATURE_NAMES

MAX_ITER = 2000
DRIFT_PAIRS = (
    (FEATURE_NAMES.index("team_a_recent_win_rate"), FEATURE_NAMES.index("team_b_recent_win_rate")),
    (FEATURE_NAMES.index("team_a_runs_conceded_per_ball"), FEATURE_NAMES.index("team_b_runs_conceded_per_ball")),
    (FEATURE_NAMES.index("team_a_defend_win_rate"), FEATURE_NAMES.index("team_b_defend_win_rate")),
)

@dataclass
class O14Model:
    scaler: StandardScaler
    model: LogisticRegression
    first_train_index: int
    last_train_index: int


def training_anchored_time(n_rows: int, first_train_index: int, last_train_index: int) -> np.ndarray:
    if n_rows <= 0:
        raise ValueError("n_rows must be positive")
    if not (0 <= first_train_index < last_train_index < n_rows):
        raise ValueError("invalid training chronology bounds")
    return (np.arange(n_rows, dtype=float) - first_train_index) / float(last_train_index - first_train_index)


def augment_o14(X: np.ndarray, t: np.ndarray) -> np.ndarray:
    """Append only the three validated signed-difference time interactions."""
    X = np.asarray(X, dtype=float)
    t = np.asarray(t, dtype=float)
    if X.ndim != 2 or X.shape[1] != len(FEATURE_NAMES):
        raise ValueError("O14 requires the exact frozen 13-feature O0 matrix")
    if len(t) != len(X):
        raise ValueError("time vector length must equal feature-row count")
    signed = np.column_stack([X[:, a] - X[:, b] for a, b in DRIFT_PAIRS])
    return np.hstack((X, signed * t.reshape(-1, 1)))


def train_o14(
    X_train: np.ndarray,
    y_train: np.ndarray,
    *,
    first_train_index: int = 0,
    last_train_index: int | None = None,
) -> Tuple[O14Model, np.ndarray]:
    X_train = np.asarray(X_train, dtype=float)
    y_train = np.asarray(y_train, dtype=int)
    if last_train_index is None:
        last_train_index = len(X_train) - 1
    t = training_anchored_time(len(X_train), first_train_index, last_train_index)
    scaler = StandardScaler()
    model = LogisticRegression(max_iter=MAX_ITER)
    model.fit(scaler.fit_transform(augment_o14(X_train, t)), y_train)
    return O14Model(scaler, model, first_train_index, last_train_index), t


def predict_proba(bundle: O14Model, X: np.ndarray, absolute_indices: np.ndarray) -> np.ndarray:
    X = np.asarray(X, dtype=float)
    absolute_indices = np.asarray(absolute_indices, dtype=float)
    if len(absolute_indices) != len(X):
        raise ValueError("absolute_indices length must equal feature rows")
    t = (absolute_indices - bundle.first_train_index) / float(bundle.last_train_index - bundle.first_train_index)
    return bundle.model.predict_proba(bundle.scaler.transform(augment_o14(X, t)))[:, 1]

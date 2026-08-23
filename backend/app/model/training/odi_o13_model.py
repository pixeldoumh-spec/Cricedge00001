"""Men's ODI O13 temporal non-stationarity experiment.

O13 is a controlled extension of frozen O0: each O0 feature receives one
training-anchored linear time interaction. No decay or new raw match feature
is introduced.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from .odi_o0_features import FEATURE_NAMES

MAX_ITER = 2000
BASE_FEATURE_COUNT = len(FEATURE_NAMES)


@dataclass
class O13Model:
    scaler: StandardScaler
    model: LogisticRegression
    first_train_index: int
    last_train_index: int


def training_anchored_time(n_rows: int, first_train_index: int, last_train_index: int) -> np.ndarray:
    """Return chronological t anchored only to the training interval.

    Future rows may extrapolate above 1.0; this is intentional so the model can
    represent continued temporal movement instead of flattening all future
    rows to the final training era.
    """
    if n_rows <= 0:
        raise ValueError("n_rows must be positive")
    if not (0 <= first_train_index < last_train_index < n_rows):
        raise ValueError("invalid training chronology bounds")
    return (np.arange(n_rows, dtype=float) - first_train_index) / float(last_train_index - first_train_index)


def augment_o13(X: np.ndarray, t: np.ndarray) -> np.ndarray:
    """Append one x_j*t interaction for every frozen O0 feature."""
    X = np.asarray(X, dtype=float)
    t = np.asarray(t, dtype=float)
    if X.ndim != 2 or X.shape[1] != BASE_FEATURE_COUNT:
        raise ValueError("O13 requires the exact frozen 13-feature O0 matrix")
    if len(t) != len(X):
        raise ValueError("time vector length must equal feature-row count")
    return np.hstack((X, X * t.reshape(-1, 1)))


def train_o13(X_train: np.ndarray, y_train: np.ndarray, *, first_train_index: int = 0, last_train_index: int | None = None) -> Tuple[O13Model, np.ndarray]:
    """Fit O13 using only the supplied chronological training rows."""
    X_train = np.asarray(X_train, dtype=float)
    y_train = np.asarray(y_train, dtype=int)
    if last_train_index is None:
        last_train_index = len(X_train) - 1
    if last_train_index <= first_train_index:
        raise ValueError("training interval must contain at least two rows")
    t = training_anchored_time(len(X_train), first_train_index, last_train_index)
    X_aug = augment_o13(X_train, t)
    scaler = StandardScaler()
    model = LogisticRegression(max_iter=MAX_ITER)
    model.fit(scaler.fit_transform(X_aug), y_train)
    return O13Model(scaler, model, first_train_index, last_train_index), t


def predict_proba(bundle: O13Model, X: np.ndarray, absolute_indices: np.ndarray) -> np.ndarray:
    """Predict using absolute chronological indices and the frozen train anchor."""
    X = np.asarray(X, dtype=float)
    absolute_indices = np.asarray(absolute_indices, dtype=float)
    if len(absolute_indices) != len(X):
        raise ValueError("absolute_indices length must equal feature rows")
    t = (absolute_indices - bundle.first_train_index) / float(bundle.last_train_index - bundle.first_train_index)
    X_aug = augment_o13(X, t)
    return bundle.model.predict_proba(bundle.scaler.transform(X_aug))[:, 1]

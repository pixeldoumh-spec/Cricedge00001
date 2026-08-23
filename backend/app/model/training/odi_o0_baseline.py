"""Men's ODI O0 baseline training and validation-only calibration."""
from __future__

from dataclasses import dataclass
from typing import Sequence, Tuple

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from .odi_o0_features import FEATURE_NAMES

TRAIN_FRACTION = 0.70
VALIDATION_FRACTION = 0.15
TEST_FRACTION = 0.15
MAX_ITER = 2000

@dataclass
class O0Baseline:
    scaler: StandardScaler
    model: LogisticRegression

@dataclass
class CalibrationCandidates:
    platt: LogisticRegression
    isotonic: IsotonicRegression


def chronological_split(X: np.ndarray, y: np.ndarray) -> Tuple[np.ndarray, ...]:
    if len(X) != 2440 or len(y) != 2440:
        raise ValueError("ODI O0 baseline requires the locked 2,440-row population")
    n_train = 1708
    n_validation = 366
    return (
        X[:n_train], y[:n_train],
        X[n_train:n_train + n_validation], y[n_train:n_train + n_validation],
        X[n_train + n_validation:], y[n_train + n_validation:],
    )


def train_model_o0(X_train: np.ndarray, y_train: np.ndarray) -> O0Baseline:
    if X_train.shape[1] != len(FEATURE_NAMES):
        raise ValueError("ODI O0 requires the exact 13-feature contract")
    scaler = StandardScaler()
    model = LogisticRegression(max_iter=MAX_ITER)
    model.fit(scaler.fit_transform(X_train), y_train)
    return O0Baseline(scaler=scaler, model=model)


def fit_validation_calibrators(raw_validation: Sequence[float], y_validation: Sequence[int]) -> CalibrationCandidates:
    p = np.asarray(raw_validation, dtype=float)
    y = np.asarray(y_validation, dtype=int)
    platt = LogisticRegression(max_iter=MAX_ITER)
    platt.fit(p.reshape(-1, 1), y)
    isotonic = IsotonicRegression(out_of_bounds="clip")
    isotonic.fit(p, y)
    return CalibrationCandidates(platt=platt, isotonic=isotonic)


def predict_raw(bundle: O0Baseline, X: np.ndarray) -> np.ndarray:
    return bundle.model.predict_proba(bundle.scaler.transform(X))[:, 1]


def predict_platt(calibrator: LogisticRegression, probabilities: Sequence[float]) -> np.ndarray:
    return calibrator.predict_proba(np.asarray(probabilities).reshape(-1, 1))[:, 1]


def predict_isotonic(calibrator: IsotonicRegression, probabilities: Sequence[float]) -> np.ndarray:
    return calibrator.predict(np.asarray(probabilities, dtype=float))

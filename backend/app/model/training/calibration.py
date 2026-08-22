"""Validation-only Platt calibration for the current model."""

from __future__ import annotations

import numpy as np
from scipy.special import expit, logit
from sklearn.linear_model import LogisticRegression


class ValidationPlattCalibrator:
    """Calibrate a fitted classifier using validation predictions only."""

    def __init__(self) -> None:
        self._model = LogisticRegression(max_iter=2000)

    def fit(self, validation_probabilities: np.ndarray, targets: np.ndarray) -> "ValidationPlattCalibrator":
        probabilities = np.clip(np.asarray(validation_probabilities, dtype=float), 1e-6, 1 - 1e-6)
        self._model.fit(logit(probabilities).reshape(-1, 1), np.asarray(targets, dtype=int))
        return self

    def predict_proba(self, probabilities: np.ndarray) -> np.ndarray:
        values = np.clip(np.asarray(probabilities, dtype=float), 1e-6, 1 - 1e-6)
        return self._model.predict_proba(logit(values).reshape(-1, 1))[:, 1]

    def transform_one(self, probability: float) -> float:
        value = float(np.clip(probability, 1e-6, 1 - 1e-6))
        return float(expit(self._model.intercept_[0] + self._model.coef_[0, 0] * logit(value)))

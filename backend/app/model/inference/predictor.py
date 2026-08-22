"""Runtime prediction boundary for frozen Model v0.

The predictor accepts a fitted estimator and calibrated probability mapper;
it never trains or mutates either object during inference.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np

from .feature_builder import build_v0_features

MODEL_VERSION = "v0"


@dataclass(frozen=True)
class Prediction:
    home_win_probability: float
    away_win_probability: float
    model_version: str = MODEL_VERSION
    feature_timestamp: str | None = None


class ModelV0Predictor:
    """Thin, side-effect-free inference wrapper for the frozen v0 model."""

    def __init__(self, estimator: Any, calibrator: Any):
        self._estimator = estimator
        self._calibrator = calibrator

    def predict(
        self,
        features: Mapping[str, float],
        *,
        feature_timestamp: str | None = None,
    ) -> Prediction:
        vector = build_v0_features(features)
        matrix = np.asarray([[*vector.values()]], dtype=float)
        raw_probability = float(self._estimator.predict_proba(matrix)[0, 1])
        calibrated_probability = float(
            self._calibrator.predict_proba(np.asarray([[raw_probability]], dtype=float))[0, 1]
        )
        home = min(max(calibrated_probability, 0.0), 1.0)
        return Prediction(
            home_win_probability=home,
            away_win_probability=1.0 - home,
            feature_timestamp=feature_timestamp,
        )

"""Production prediction service for the frozen model artifacts."""

from __future__ import annotations

from typing import Mapping

import numpy as np

from app.model.training.model_v0 import FEATURES
from .artifact_registry import registry


def _probability(artifact, values: Mapping[str, float]) -> float:
    missing = [name for name in FEATURES if name not in values]
    if missing:
        raise ValueError(f"missing model features: {', '.join(missing)}")
    vector = np.asarray([[float(values[name]) for name in FEATURES]], dtype=float)
    raw = float(artifact.model.predict_proba(vector)[0, 1])
    if artifact.calibrator is not None:
        raw = float(artifact.calibrator.predict_proba(np.asarray([raw], dtype=float))[0])
    return min(max(raw, 0.0), 1.0)


def predict(version: str, features: Mapping[str, float]) -> dict[str, object]:
    artifact = registry.load(version)
    probability = _probability(artifact, features)
    return {
        "model_version": artifact.version,
        "calibrated": artifact.calibrated,
        "home_win_probability": probability,
        "away_win_probability": 1.0 - probability,
    }

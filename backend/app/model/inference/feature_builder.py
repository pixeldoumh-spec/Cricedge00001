"""Build the frozen Model v0 inference feature vector."""

from __future__ import annotations

from typing import Mapping

from app.model.training.model_v0 import FEATURES


def build_v0_features(values: Mapping[str, float]) -> dict[str, float]:
    """Return the exact frozen v0 feature contract in stable training order."""
    missing = [name for name in FEATURES if name not in values]
    if missing:
        raise ValueError(f"missing Model v0 features: {', '.join(missing)}")
    return {name: float(values[name]) for name in FEATURES}

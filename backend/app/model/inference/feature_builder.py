"""Build the frozen Model v0 inference feature vector.

This module is deliberately narrow: it consumes already-computed historical
state and current match context. It does not train, update Elo, or inspect
future results.
"""

from __future__ import annotations

from typing import Mapping

from app.model.training.model_v1 import FEATURE_NAMES


def build_v0_features(values: Mapping[str, float]) -> dict[str, float]:
    """Return the exact v0 feature contract in a stable order."""
    return {name: float(values.get(name, 0.0)) for name in FEATURE_NAMES}

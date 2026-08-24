"""Bounded recency-movement diagnostic for T20 strength.

This is a predeclared research representation, not a production model.
It replaces the unrestricted fast-minus-slow state with bounded measures of
recent strength movement.  The goal is to test whether recent movement has a
stable relationship with future outcomes without allowing extreme Elo gaps to
dominate.

All states are pre-match. No current outcome is used in construction.
Selection must be validation-only; frozen test and future holdout are never
used to choose bounds or windows.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class BoundedMovementConfig:
    horizon_matches: int
    cap_elo: float
    use_sign: bool
    use_magnitude: bool


# Predeclared, deliberately small grid. These are diagnostics, not a search
# over arbitrary hyperparameters.
CONFIGS: tuple[BoundedMovementConfig, ...] = (
    BoundedMovementConfig(5, 100.0, True, False),
    BoundedMovementConfig(10, 100.0, True, False),
    BoundedMovementConfig(20, 100.0, True, False),
    BoundedMovementConfig(10, 150.0, True, False),
    BoundedMovementConfig(20, 150.0, True, False),
    BoundedMovementConfig(10, 100.0, True, True),
    BoundedMovementConfig(20, 100.0, True, True),
)


def bounded_tanh(delta: float, cap_elo: float) -> float:
    """Map unrestricted Elo movement to a bounded (-1, 1) state."""
    if cap_elo <= 0:
        raise ValueError("cap_elo must be positive")
    # delta/cap is dimensionless; tanh prevents extreme movement from growing
    # linearly without clipping the sign.
    import math
    return math.tanh(delta / cap_elo)


def signed_magnitude(delta: float, cap_elo: float) -> tuple[float, float]:
    """Return bounded signed movement and bounded magnitude."""
    value = bounded_tanh(delta, cap_elo)
    return value, abs(value)


def protocol() -> dict:
    return {
        "reference": "raw Challenger B",
        "selection": "validation only",
        "test_selection": False,
        "future_holdout_selection": False,
        "calibration": False,
        "state": "bounded recent movement from pre-match strength states",
        "transformation": "tanh(delta / cap_elo)",
        "configs": [
            {
                "horizon_matches": c.horizon_matches,
                "cap_elo": c.cap_elo,
                "use_sign": c.use_sign,
                "use_magnitude": c.use_magnitude,
            }
            for c in CONFIGS
        ],
    }

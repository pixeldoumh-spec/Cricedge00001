"""ODI O12: frozen O0 strength with pre-match history-depth interaction."""
from __future__ import annotations

import math
from typing import Any, Dict

FEATURE_NAME = "team_a_minus_team_b_strength_x_history_context"


def history_context(team_a_history: int, team_b_history: int) -> float:
    """Return leakage-safe context from pre-match decisive-history counts."""
    minimum_history = min(int(team_a_history), int(team_b_history))
    if minimum_history < 0:
        raise ValueError("pre-match history counts must be non-negative")
    return math.log1p(minimum_history)


def add_o12_feature(o0_features: Dict[str, float], team_a_history: int, team_b_history: int) -> Dict[str, float]:
    """Add exactly one O12 feature to an existing frozen O0 feature dictionary."""
    if "team_a_minus_team_b_strength" not in o0_features:
        raise KeyError("missing frozen O0 strength feature")
    if FEATURE_NAME in o0_features:
        raise ValueError("O12 feature already present")
    out = dict(o0_features)
    out[FEATURE_NAME] = float(
        o0_features["team_a_minus_team_b_strength"]
        * history_context(team_a_history, team_b_history)
    )
    return out

"""Bounded recency-movement diagnostic for T20 strength.

This is a predeclared research representation, not a production model.
For horizon H, recent movement is the change in the pre-match fast Elo state
between the current match and the state after H completed matches for that
team, divided by H (movement per completed match). The movement is then
bounded with tanh(rate / cap_elo).

All states are pre-match. No current outcome is used in construction.
Selection must be validation-only; frozen test and future holdout are never
used to choose bounds or windows.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping, Sequence, Any


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
    """Map an unrestricted per-match Elo movement to (-1, 1)."""
    if cap_elo <= 0:
        raise ValueError("cap_elo must be positive")
    import math
    return math.tanh(delta / cap_elo)


def signed_magnitude(delta: float, cap_elo: float) -> tuple[float, float]:
    """Return bounded signed movement and bounded magnitude."""
    value = bounded_tanh(delta, cap_elo)
    return value, abs(value)


def recent_rate(
    history: Sequence[Mapping[str, Any]],
    team: str,
    horizon_matches: int,
    current_fast_elo: float,
) -> float:
    """Return fast-Elo movement per completed match over the prior H matches.

    ``history`` must contain only completed matches before the current match and
    must be ordered chronologically. Each row must provide ``team``, ``fast_elo``
    as the post-match state, and a match identifier/date sufficient for the
    caller's chronological ordering. The baseline is the team's fast Elo state
    immediately after the H-th most recent completed match.

    The function intentionally does not read outcomes; outcomes belong only in
    the upstream Elo state construction.
    """
    if horizon_matches <= 0:
        raise ValueError("horizon_matches must be positive")

    team_rows = [r for r in history if r.get("team") == team]
    if len(team_rows) < horizon_matches:
        raise ValueError("insufficient prior matches for requested horizon")

    baseline = float(team_rows[-horizon_matches]["fast_elo"])
    return (float(current_fast_elo) - baseline) / horizon_matches


def bounded_recent_rate(
    history: Sequence[Mapping[str, Any]],
    team: str,
    current_fast_elo: float,
    horizon_matches: int,
    cap_elo: float,
) -> float:
    """Compute the explicit bounded recent fast-Elo movement state."""
    rate = recent_rate(history, team, horizon_matches, current_fast_elo)
    return bounded_tanh(rate, cap_elo)


def protocol() -> dict:
    return {
        "reference": "raw Challenger B",
        "selection": "validation only",
        "test_selection": False,
        "future_holdout_selection": False,
        "calibration": False,
        "state": "bounded recent movement from pre-match fast-strength states",
        "definition": "rate_H=(fast_elo_t-fast_elo_t_minus_H)/H; bounded=tanh(rate_H/cap_elo)",
        "baseline": "post-match fast Elo state after the H-th most recent completed team match",
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

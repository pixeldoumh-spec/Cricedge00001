"""Predeclared diagnostic for T20 fast-vs-slow strength movement.

Purpose: distinguish symmetric relative movement from asymmetric team/opponent
movement. This is diagnostic only; it does not select a production model.

For each match, the inputs are leakage-safe pre-match states:
  team_delta = fast_team_elo - slow_team_elo
  opponent_delta = fast_opponent_elo - slow_opponent_elo
  relative_delta = team_delta - opponent_delta

Sign and magnitude decompositions are included without using the outcome.
All model/evaluation choices remain fixed outside this module.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Any, Sequence


@dataclass(frozen=True)
class MovementRow:
    team_delta: float
    opponent_delta: float
    relative_delta: float
    team_delta_abs: float
    opponent_delta_abs: float
    relative_delta_abs: float
    team_delta_sign: int
    opponent_delta_sign: int
    relative_delta_sign: int


def movement_features(row: Mapping[str, Any]) -> MovementRow:
    td = float(row["fast_team_elo"]) - float(row["slow_team_elo"])
    od = float(row["fast_opponent_elo"]) - float(row["slow_opponent_elo"])
    rd = td - od
    return MovementRow(
        team_delta=td,
        opponent_delta=od,
        relative_delta=rd,
        team_delta_abs=abs(td),
        opponent_delta_abs=abs(od),
        relative_delta_abs=abs(rd),
        team_delta_sign=(td > 0) - (td < 0),
        opponent_delta_sign=(od > 0) - (od < 0),
        relative_delta_sign=(rd > 0) - (rd < 0),
    )


def build_movement_rows(rows: Sequence[Mapping[str, Any]]) -> list[MovementRow]:
    """Derive movement variables from pre-match strength states only."""
    return [movement_features(row) for row in rows]


VARIANTS = {
    "team_delta_only": ("team_delta",),
    "opponent_delta_only": ("opponent_delta",),
    "relative_delta_only": ("relative_delta",),
    "team_opponent_deltas": ("team_delta", "opponent_delta"),
    "relative_delta_magnitude": ("relative_delta", "relative_delta_abs"),
    "signed_movement": (
        "team_delta_sign",
        "opponent_delta_sign",
        "relative_delta_sign",
    ),
    "movement_magnitude": (
        "team_delta_abs",
        "opponent_delta_abs",
        "relative_delta_abs",
    ),
}


PROTOCOL = {
    "reference": "raw Challenger B",
    "selection": "validation only",
    "test_selection": False,
    "future_holdout_selection": False,
    "outcome_leakage": False,
    "fast_k": {"men": 80, "women": 160},
    "slow_k": 20,
    "purpose": "distinguish symmetric relative movement from asymmetric team/opponent drift",
    "variants": VARIANTS,
}

"""Diagnostic decomposition protocol for the T20 dual-timescale strength result.

This module defines the predeclared decomposition, not a promotion model.  The
purpose is to isolate which structural component of the six-feature dual state
is carrying the useful signal:

A) fast state only
B) slow state only
C) fast-minus-slow state only
D) persistent + delta state
E) separate team/opponent fast-vs-slow deltas

All variants must preserve the same non-strength features, estimator, corpus,
chronological splits, and evaluation protocol.  No test-set selection is
permitted.  The decomposition should be run against Challenger B as the
reference, with the frozen test and future holdout used only for final
comparison after validation-side selection.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


Variant = Literal[
    "fast_only",
    "slow_only",
    "delta_only",
    "slow_plus_delta",
    "team_opponent_delta",
]


@dataclass(frozen=True)
class DecompositionVariant:
    name: Variant
    description: str
    feature_columns: tuple[str, ...]


VARIANTS: tuple[DecompositionVariant, ...] = (
    DecompositionVariant(
        "fast_only",
        "Use only the fast team/opponent Elo and fast difference.",
        ("fast_team_elo", "fast_opponent_elo", "fast_difference"),
    ),
    DecompositionVariant(
        "slow_only",
        "Use only the slow team/opponent Elo and slow difference.",
        ("slow_team_elo", "slow_opponent_elo", "slow_difference"),
    ),
    DecompositionVariant(
        "delta_only",
        "Use only fast-minus-slow team, opponent, and difference states.",
        ("team_delta", "opponent_delta", "difference_delta"),
    ),
    DecompositionVariant(
        "slow_plus_delta",
        "Use slow team/opponent/difference plus fast-minus-slow deltas.",
        (
            "slow_team_elo",
            "slow_opponent_elo",
            "slow_difference",
            "team_delta",
            "opponent_delta",
            "difference_delta",
        ),
    ),
    DecompositionVariant(
        "team_opponent_delta",
        "Use the fast-minus-slow team and opponent deltas without the derived difference delta.",
        (
            "team_delta",
            "opponent_delta",
        ),
    ),
)


def add_delta_columns(rows):
    """Return rows with explicit fast-minus-slow state deltas.

    The caller supplies rows containing the six dual-timescale fields.  This
    function does not inspect outcomes and therefore cannot introduce outcome
    leakage.
    """
    enriched = []
    for row in rows:
        item = dict(row)
        item["team_delta"] = item["fast_team_elo"] - item["slow_team_elo"]
        item["opponent_delta"] = item["fast_opponent_elo"] - item["slow_opponent_elo"]
        item["difference_delta"] = item["fast_difference"] - item["slow_difference"]
        enriched.append(item)
    return enriched


def protocol() -> dict:
    return {
        "reference": "raw Challenger B",
        "selection": "validation only",
        "test_selection": False,
        "future_holdout_selection": False,
        "strength_state": "dual K=20 slow plus K=80 male/K=160 female fast",
        "non_strength_features_changed": False,
        "calibration": False,
        "variants": [
            {"name": v.name, "description": v.description, "features": list(v.feature_columns)}
            for v in VARIANTS
        ],
    }

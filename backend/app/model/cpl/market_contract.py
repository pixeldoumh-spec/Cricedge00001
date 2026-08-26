"""Authoritative recurring CPL bookmaker-market contract.

This file defines WHAT the CPL outcome engine must predict. It does not
contain bookmaker prices and it does not use bookmaker prices as training
labels. Match 16 of CPL 2026 supplied the concrete example of these markets;
the market families are intended to recur across CPL matches.

Coin-toss markets are intentionally excluded: the toss is not treated as a
learnable cricket-performance outcome from historical league matches.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PredictionTiming(str, Enum):
    PRE_MATCH = "pre_match"
    CONFIRMED_XI = "confirmed_xi"
    LIVE = "live"


@dataclass(frozen=True)
class MarketSpec:
    key: str
    family: str
    target: str
    timing: PredictionTiming
    source_of_truth: str
    derived_from_distribution: bool


MARKETS: tuple[MarketSpec, ...] = (
    MarketSpec("match_winner", "match", "winner_including_super_over", PredictionTiming.PRE_MATCH, "match_result", False),
    MarketSpec("player_of_match", "player", "player_of_match", PredictionTiming.CONFIRMED_XI, "match_award", False),
    MarketSpec("team_innings_total", "team_batting", "innings_runs_distribution", PredictionTiming.CONFIRMED_XI, "innings_score", True),
    MarketSpec("player_innings_total", "player_batting", "player_runs_distribution", PredictionTiming.CONFIRMED_XI, "player_batting", True),
    MarketSpec("over_1_to_6_total", "team_batting", "over_runs_distribution", PredictionTiming.CONFIRMED_XI, "delivery_runs", True),
    MarketSpec("total_fours", "match_aggregate", "fours_distribution", PredictionTiming.CONFIRMED_XI, "delivery_boundaries", True),
    MarketSpec("total_sixes", "match_aggregate", "sixes_distribution", PredictionTiming.CONFIRMED_XI, "delivery_boundaries", True),
    MarketSpec("most_fours", "comparative", "team_with_most_fours_or_draw", PredictionTiming.CONFIRMED_XI, "team_boundary_counts", True),
    MarketSpec("most_sixes", "comparative", "team_with_most_sixes_or_draw", PredictionTiming.CONFIRMED_XI, "team_boundary_counts", True),
    MarketSpec("team_top_batter", "comparative", "team_with_top_batter", PredictionTiming.CONFIRMED_XI, "player_batting_distribution", True),
    MarketSpec("team_top_bowler", "comparative", "team_with_top_bowler", PredictionTiming.CONFIRMED_XI, "player_bowling_distribution", True),
)

# The bookmaker's numerical line is a query against an underlying model
# distribution. It is never a training target.
DERIVED_MARKETS = {
    "team_total_over_under": "P(team_innings_runs > line)",
    "player_total_over_under": "P(player_runs > line)",
    "over_total_over_under": "P(over_runs > line)",
    "total_fours_over_under": "P(total_fours > line)",
    "total_sixes_over_under": "P(total_sixes > line)",
}

EXCLUDED_MARKETS = {
    "coin_toss_winner": "excluded: not a learnable cricket-performance target",
    "coin_toss_and_match_winner": "excluded: contains the non-predictive toss component",
}

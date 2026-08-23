"""Men's ODI O11: pre-match opponent-relative dynamic team rating."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, Iterable, List

from .odi_o0_features import FEATURE_NAMES as O0_FEATURE_NAMES, FeatureEngine as O0FeatureEngine

O11_FEATURE_NAMES = [*O0_FEATURE_NAMES, "team_a_minus_team_b_elo_rating"]
INITIAL_RATING = 1500.0
K_FACTOR = 20.0
RATING_SCALE = 400.0

@dataclass
class DynamicRatingEngine:
    ratings: Dict[str, float] = field(default_factory=dict)

    def rating(self, team: str) -> float:
        return float(self.ratings.get(team, INITIAL_RATING))

    @staticmethod
    def expected(rating_a: float, rating_b: float) -> float:
        return 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / RATING_SCALE))

    def feature(self, team_a: str, team_b: str) -> float:
        return self.rating(team_a) - self.rating(team_b)

    def update(self, team_a: str, team_b: str, winner: str) -> None:
        if winner not in {team_a, team_b}:
            return
        ra, rb = self.rating(team_a), self.rating(team_b)
        ea = self.expected(ra, rb)
        score_a = 1.0 if winner == team_a else 0.0
        self.ratings[team_a] = ra + K_FACTOR * (score_a - ea)
        self.ratings[team_b] = rb + K_FACTOR * ((1.0 - score_a) - (1.0 - ea))


def _date(match: Dict[str, Any]) -> date:
    return date.fromisoformat(str(match["info"]["dates"][0]))


def build_feature_rows(matches: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build leakage-safe O11 rows; the rating is always captured before updating."""
    ordered = sorted(matches, key=lambda m: (_date(m), str(m.get("_match_id", ""))))
    o0 = O0FeatureEngine()
    rating = DynamicRatingEngine()
    rows: List[Dict[str, Any]] = []
    for match in ordered:
        info = match["info"]
        if info.get("gender") != "male" or info.get("match_type") != "ODI":
            continue
        teams = list(info["teams"])
        if len(teams) != 2:
            raise ValueError("ODI O11 requires exactly two teams")
        winner = info.get("outcome", {}).get("winner")
        if winner in teams:
            team_a, team_b = teams
            base = o0.features_for(team_a, team_b)
            base["team_a_minus_team_b_elo_rating"] = rating.feature(team_a, team_b)
            rows.append({
                "match_id": str(match.get("_match_id", "")),
                "date": str(info["dates"][0]),
                "team_a": team_a,
                "team_b": team_b,
                "target": int(winner == team_a),
                "features": base,
            })
        o0.update(match)
        if winner in teams:
            rating.update(teams[0], teams[1], winner)
    return rows

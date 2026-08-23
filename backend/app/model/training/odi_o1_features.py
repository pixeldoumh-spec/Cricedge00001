"""Canonical men's ODI O1 feature generation: O0 plus fixed 20-match recency win rates."""
from __future__ import annotations

from collections import deque
from datetime import date
from typing import Any, Dict, Iterable, List, Tuple

from .odi_o0_features import FEATURE_NAMES, FeatureEngine as O0FeatureEngine, TeamState

RECENT_WINDOW = 20


class O1FeatureEngine(O0FeatureEngine):
    """O0 feature engine with exactly one controlled change: recent win rate."""

    def __init__(self) -> None:
        super().__init__()
        self.recent_results: Dict[str, deque[int]] = {}

    def _recent(self, team: str) -> deque[int]:
        return self.recent_results.setdefault(team, deque(maxlen=RECENT_WINDOW))

    def _metrics(self, team: str) -> List[float]:
        s = self._state(team)
        recent = self._recent(team)
        recent_win_rate = sum(recent) / len(recent) if recent else 0.0
        return [
            float(recent_win_rate),
            self._ratio(s.runs_scored, s.balls_batted),
            self._ratio(s.wickets_taken, s.balls_bowled),
            self._ratio(s.runs_conceded, s.balls_bowled),
            self._ratio(s.chase_wins, s.chase_decisive),
            self._ratio(s.defend_wins, s.defend_decisive),
        ]

    def update(self, match: Dict[str, Any]) -> None:
        info = match["info"]
        teams = list(info["teams"])
        if len(teams) != 2:
            raise ValueError("ODI O1 requires exactly two teams")
        winner = info.get("outcome", {}).get("winner")
        super().update(match)
        if winner in teams:
            for team in teams:
                self._recent(team).append(int(winner == team))


def _date(match: Dict[str, Any]) -> date:
    return date.fromisoformat(str(match["info"]["dates"][0]))


def build_feature_rows(matches: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Emit one leakage-safe supervised row per decisive men's ODI."""
    ordered = sorted(matches, key=lambda m: (_date(m), str(m.get("_match_id", ""))))
    engine = O1FeatureEngine()
    rows: List[Dict[str, Any]] = []
    for match in ordered:
        info = match["info"]
        if info.get("gender") != "male" or info.get("match_type") != "ODI":
            continue
        teams = list(info["teams"])
        winner = info.get("outcome", {}).get("winner")
        if winner not in teams:
            engine.update(match)
            continue
        team_a, team_b = teams
        rows.append({
            "match_id": str(match.get("_match_id", "")),
            "date": str(info["dates"][0]),
            "team_a": team_a,
            "team_b": team_b,
            "target": int(winner == team_a),
            "features": engine.features_for(team_a, team_b),
        })
        engine.update(match)
    return rows

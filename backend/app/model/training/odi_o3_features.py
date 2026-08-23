"""Canonical men's ODI O3: O0 plus one batting/bowling interaction term."""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, Iterable, List

from .odi_o0_features import FeatureEngine as O0FeatureEngine

O3_FEATURE_NAME = "team_a_minus_team_b_batting_bowling_interaction"


class O3FeatureEngine(O0FeatureEngine):
    """O0 feature engine with exactly one derived interaction feature."""

    def features_for(self, team_a: str, team_b: str) -> Dict[str, float]:
        values = super().features_for(team_a, team_b)
        batting_delta = (
            values["team_a_batting_runs_per_ball"]
            - values["team_b_batting_runs_per_ball"]
        )
        bowling_delta = (
            values["team_a_runs_conceded_per_ball"]
            - values["team_b_runs_conceded_per_ball"]
        )
        values[O3_FEATURE_NAME] = float(batting_delta * bowling_delta)
        return values


def _date(match: Dict[str, Any]) -> date:
    return date.fromisoformat(str(match["info"]["dates"][0]))


def build_feature_rows(matches: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    ordered = sorted(matches, key=lambda m: (_date(m), str(m.get("_match_id", ""))))
    engine = O3FeatureEngine()
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
        features = engine.features_for(team_a, team_b)
        rows.append({
            "match_id": str(match.get("_match_id", "")),
            "date": str(info["dates"][0]),
            "team_a": team_a,
            "team_b": team_b,
            "target": int(winner == team_a),
            "features": features,
        })
        engine.update(match)
    return rows

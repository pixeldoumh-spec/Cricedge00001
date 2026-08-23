"""ODI O8 level-plus-chronological-change feature generation.

O8 keeps every frozen O0 level feature and adds change signals only for
components identified by the committed O6 drift diagnosis. The change signal
uses each team's full pre-match history split into older/newer chronological
halves; there is no tunable recency window or decay parameter.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

import numpy as np

from .odi_o0_features import FEATURE_NAMES, FeatureEngine, TeamState

O8_FEATURE_NAMES = FEATURE_NAMES + [
    "team_a_win_rate_change", "team_b_win_rate_change",
    "team_a_batting_runs_per_ball_change", "team_b_batting_runs_per_ball_change",
    "team_a_chase_win_rate_change", "team_b_chase_win_rate_change",
    "team_a_defend_win_rate_change", "team_b_defend_win_rate_change",
    "team_a_minus_team_b_strength_change",
]


@dataclass
class MatchContribution:
    decisive: int = 0
    wins: int = 0
    runs_scored: int = 0
    balls_batted: int = 0
    wickets_taken: int = 0
    balls_bowled: int = 0
    runs_conceded: int = 0
    chase_decisive: int = 0
    chase_wins: int = 0
    defend_decisive: int = 0
    defend_wins: int = 0


def _ratio(num: float, den: float) -> float:
    return float(num / den) if den else 0.0


def _component_metrics(history: List[MatchContribution]) -> np.ndarray:
    s = MatchContribution()
    for h in history:
        s.decisive += h.decisive
        s.wins += h.wins
        s.runs_scored += h.runs_scored
        s.balls_batted += h.balls_batted
        s.wickets_taken += h.wickets_taken
        s.balls_bowled += h.balls_bowled
        s.runs_conceded += h.runs_conceded
        s.chase_decisive += h.chase_decisive
        s.chase_wins += h.chase_wins
        s.defend_decisive += h.defend_decisive
        s.defend_wins += h.defend_wins
    return np.array([
        _ratio(s.wins, s.decisive),
        _ratio(s.runs_scored, s.balls_batted),
        _ratio(s.wickets_taken, s.balls_bowled),
        _ratio(s.runs_conceded, s.balls_bowled),
        _ratio(s.chase_wins, s.chase_decisive),
        _ratio(s.defend_wins, s.defend_decisive),
    ], dtype=float)


def _change(history: List[MatchContribution]) -> np.ndarray:
    if len(history) < 2:
        return np.zeros(6, dtype=float)
    mid = len(history) // 2
    older = _component_metrics(history[:mid])
    newer = _component_metrics(history[mid:])
    return newer - older


@dataclass
class O8FeatureEngine:
    """Maintain match-level history and emit leakage-safe O8 rows."""

    base: FeatureEngine = field(default_factory=FeatureEngine)
    histories: Dict[str, List[MatchContribution]] = field(default_factory=dict)

    def _history(self, team: str) -> List[MatchContribution]:
        return self.histories.setdefault(team, [])

    def _level(self, team: str) -> np.ndarray:
        return np.asarray(self.base._metrics(team), dtype=float)

    def _strength_change(self, team_a: str, team_b: str) -> float:
        a = _change(self._history(team_a))
        b = _change(self._history(team_b))
        return float(np.mean(a - b))

    def features_for(self, team_a: str, team_b: str) -> Dict[str, float]:
        a = self._level(team_a)
        b = self._level(team_b)
        base_strength = float(np.mean(a - b))
        ca = _change(self._history(team_a))
        cb = _change(self._history(team_b))
        values = [
            a[0], b[0], a[1], b[1], a[2], b[2], a[3], b[3],
            a[4], b[4], a[5], b[5], base_strength,
            ca[0], cb[0], ca[1], cb[1], ca[4], cb[4], ca[5], cb[5],
            self._strength_change(team_a, team_b),
        ]
        return dict(zip(O8_FEATURE_NAMES, values))

    def update(self, match: Dict[str, Any]) -> None:
        info = match["info"]
        teams = list(info["teams"])
        if len(teams) != 2:
            raise ValueError("ODI O8 requires exactly two teams")
        winner = info.get("outcome", {}).get("winner")
        innings = match.get("innings", [])
        batting: Dict[str, Tuple[int, int]] = {t: (0, 0) for t in teams}
        bowling: Dict[str, Tuple[int, int, int]] = {t: (0, 0, 0) for t in teams}
        for inn in innings:
            batting_team = inn["team"]
            runs = balls = wickets = 0
            for over in inn.get("overs", []):
                for delivery in over.get("deliveries", []):
                    runs += int(delivery.get("runs", {}).get("total", 0))
                    extras = delivery.get("extras", {})
                    if "wides" not in extras and "noballs" not in extras:
                        balls += 1
                    for wicket in delivery.get("wickets", []):
                        if wicket.get("kind") not in {"retired hurt", "retired not out"}:
                            wickets += 1
            opponent = teams[1] if batting_team == teams[0] else teams[0]
            r, b = batting[batting_team]
            batting[batting_team] = (r + runs, b + balls)
            rc, bb, wt = bowling[opponent]
            bowling[opponent] = (rc + runs, bb + balls, wt + wickets)

        first_team = innings[0]["team"] if innings else None
        second_team = innings[1]["team"] if len(innings) > 1 else None
        for team in teams:
            r, b = batting[team]
            rc, bb, wt = bowling[team]
            contribution = MatchContribution(
                decisive=int(winner in teams),
                wins=int(winner == team),
                runs_scored=r,
                balls_batted=b,
                wickets_taken=wt,
                balls_bowled=bb,
                runs_conceded=rc,
                chase_decisive=int(winner in teams and team == second_team),
                chase_wins=int(winner in teams and team == second_team and winner == team),
                defend_decisive=int(winner in teams and team == first_team),
                defend_wins=int(winner in teams and team == first_team and winner == team),
            )
            self._history(team).append(contribution)
            self.base.update(match) if False else None

        # Update the canonical O0 cumulative state once per match.
        self.base.update(match)


def build_feature_rows(matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Emit one leakage-safe O8 supervised row per decisive men's ODI."""
    ordered = sorted(matches, key=lambda m: (str(m["info"]["dates"][0]), str(m.get("_match_id", ""))))
    engine = O8FeatureEngine()
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
        a, b = teams
        rows.append({
            "match_id": str(match.get("_match_id", "")),
            "date": str(info["dates"][0]),
            "team_a": a,
            "team_b": b,
            "target": int(winner == a),
            "features": engine.features_for(a, b),
        })
        engine.update(match)
    return rows

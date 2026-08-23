"""Canonical men's ODI O0 pre-match feature generation."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, Iterable, List, Tuple

FEATURE_NAMES = [
    "team_a_recent_win_rate", "team_b_recent_win_rate",
    "team_a_batting_runs_per_ball", "team_b_batting_runs_per_ball",
    "team_a_wickets_per_ball", "team_b_wickets_per_ball",
    "team_a_runs_conceded_per_ball", "team_b_runs_conceded_per_ball",
    "team_a_chase_win_rate", "team_b_chase_win_rate",
    "team_a_defend_win_rate", "team_b_defend_win_rate",
    "team_a_minus_team_b_strength",
]

@dataclass
class TeamState:
    decisive_matches: int = 0
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

@dataclass
class FeatureEngine:
    states: Dict[str, TeamState] = field(default_factory=dict)

    def _state(self, team: str) -> TeamState:
        return self.states.setdefault(team, TeamState())

    @staticmethod
    def _ratio(num: float, den: float) -> float:
        return float(num / den) if den else 0.0

    def _metrics(self, team: str) -> List[float]:
        s = self._state(team)
        return [self._ratio(s.wins, s.decisive_matches), self._ratio(s.runs_scored, s.balls_batted), self._ratio(s.wickets_taken, s.balls_bowled), self._ratio(s.runs_conceded, s.balls_bowled), self._ratio(s.chase_wins, s.chase_decisive), self._ratio(s.defend_wins, s.defend_decisive)]

    def features_for(self, team_a: str, team_b: str) -> Dict[str, float]:
        a, b = self._metrics(team_a), self._metrics(team_b)
        strength = sum(x - y for x, y in zip(a, b)) / 6.0
        return dict(zip(FEATURE_NAMES, [a[0], b[0], a[1], b[1], a[2], b[2], a[3], b[3], a[4], b[4], a[5], b[5], strength]))

    def update(self, match: Dict[str, Any]) -> None:
        info = match["info"]; teams = list(info["teams"])
        if len(teams) != 2: raise ValueError("ODI O0 requires exactly two teams")
        winner = info.get("outcome", {}).get("winner"); innings = match.get("innings", [])
        batting = {t: (0, 0) for t in teams}; bowling = {t: (0, 0, 0) for t in teams}
        for inn in innings:
            batting_team = inn["team"]; runs = balls = wickets = 0
            for over in inn.get("overs", []):
                for delivery in over.get("deliveries", []):
                    runs += int(delivery.get("runs", {}).get("total", 0)); extras = delivery.get("extras", {})
                    if "wides" not in extras and "noballs" not in extras: balls += 1
                    for wicket in delivery.get("wickets", []):
                        if wicket.get("kind") not in {"retired hurt", "retired not out"}: wickets += 1
            opponent = teams[1] if batting_team == teams[0] else teams[0]
            r0, b0 = batting[batting_team]; batting[batting_team] = (r0 + runs, b0 + balls)
            r0, b0, w0 = bowling[opponent]; bowling[opponent] = (r0 + runs, b0 + balls, w0 + wickets)
        first_team = innings[0]["team"] if innings else None; second_team = innings[1]["team"] if len(innings) > 1 else None
        for team in teams:
            s = self._state(team); r, b = batting[team]; rc, bb, wt = bowling[team]
            s.runs_scored += r; s.balls_batted += b; s.runs_conceded += rc; s.balls_bowled += bb; s.wickets_taken += wt
            if winner in teams:
                s.decisive_matches += 1; s.wins += int(winner == team)
                if team == second_team: s.chase_decisive += 1; s.chase_wins += int(winner == team)
                elif team == first_team: s.defend_decisive += 1; s.defend_wins += int(winner == team)

def _date(match: Dict[str, Any]) -> date: return date.fromisoformat(str(match["info"]["dates"][0]))

def build_feature_rows(matches: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    ordered = sorted(matches, key=lambda m: (_date(m), str(m.get("_match_id", "")))); engine = FeatureEngine(); rows = []
    for match in ordered:
        info = match["info"]
        if info.get("gender") != "male" or info.get("match_type") != "ODI": continue
        teams = list(info["teams"]); winner = info.get("outcome", {}).get("winner")
        if winner not in teams: engine.update(match); continue
        team_a, team_b = teams
        rows.append({"match_id": str(match.get("_match_id", "")), "date": str(info["dates"][0]), "team_a": team_a, "team_b": team_b, "target": int(winner == team_a), "features": engine.features_for(team_a, team_b)})
        engine.update(match)
    return rows

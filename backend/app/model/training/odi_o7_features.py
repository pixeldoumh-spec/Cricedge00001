"""Men's ODI O7 feature engine: targeted temporal decay on O6-supported components."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, Iterable, List

from .odi_o0_features import FEATURE_NAMES

HALF_LIFE_MATCHES = 20
DECAY = 2.0 ** (-1.0 / HALF_LIFE_MATCHES)

# State fields contributing to the O6-supported components. Bowling-rate
# components (wickets/ball and runs-conceded/ball) remain cumulative.
DECAYED = {
    "decisive_matches", "wins", "runs_scored", "balls_batted",
    "chase_decisive", "chase_wins", "defend_decisive", "defend_wins",
}

@dataclass
class DecayedTeamState:
    decisive_matches: float = 0.0
    wins: float = 0.0
    runs_scored: float = 0.0
    balls_batted: float = 0.0
    wickets_taken: float = 0.0
    balls_bowled: float = 0.0
    runs_conceded: float = 0.0
    chase_decisive: float = 0.0
    chase_wins: float = 0.0
    defend_decisive: float = 0.0
    defend_wins: float = 0.0

@dataclass
class FeatureEngine:
    states: Dict[str, DecayedTeamState] = field(default_factory=dict)

    def _state(self, team: str) -> DecayedTeamState:
        return self.states.setdefault(team, DecayedTeamState())

    @staticmethod
    def _ratio(num: float, den: float) -> float:
        return float(num / den) if den else 0.0

    def _metrics(self, team: str) -> List[float]:
        s = self._state(team)
        return [
            self._ratio(s.wins, s.decisive_matches),
            self._ratio(s.runs_scored, s.balls_batted),
            self._ratio(s.wickets_taken, s.balls_bowled),
            self._ratio(s.runs_conceded, s.balls_bowled),
            self._ratio(s.chase_wins, s.chase_decisive),
            self._ratio(s.defend_wins, s.defend_decisive),
        ]

    def features_for(self, team_a: str, team_b: str) -> Dict[str, float]:
        a, b = self._metrics(team_a), self._metrics(team_b)
        strength = sum(x - y for x, y in zip(a, b)) / 6.0
        values = [a[0], b[0], a[1], b[1], a[2], b[2], a[3], b[3],
                  a[4], b[4], a[5], b[5], strength]
        return dict(zip(FEATURE_NAMES, values))

    def _decay_targeted(self) -> None:
        for state in self.states.values():
            for name in DECAYED:
                setattr(state, name, getattr(state, name) * DECAY)

    def update(self, match: Dict[str, Any]) -> None:
        # Decay the completed historical state before adding this match.
        # Therefore the current match can never influence its own features.
        self._decay_targeted()
        info = match["info"]
        teams = list(info["teams"])
        if len(teams) != 2:
            raise ValueError("ODI O7 requires exactly two teams")
        winner = info.get("outcome", {}).get("winner")
        innings = match.get("innings", [])

        batting: Dict[str, tuple[int, int]] = {t: (0, 0) for t in teams}
        bowling: Dict[str, tuple[int, int, int]] = {t: (0, 0, 0) for t in teams}
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
            r, b, w = bowling[opponent]
            bowling[opponent] = (r + runs, b + balls, w + wickets)

        first_team = innings[0]["team"] if innings else None
        second_team = innings[1]["team"] if len(innings) > 1 else None
        for team in teams:
            s = self._state(team)
            r, b = batting[team]
            rc, bb, wt = bowling[team]
            s.runs_scored += r
            s.balls_batted += b
            s.runs_conceded += rc
            s.balls_bowled += bb
            s.wickets_taken += wt
            if winner in teams:
                s.decisive_matches += 1
                s.wins += float(winner == team)
                if team == second_team:
                    s.chase_decisive += 1
                    s.chase_wins += float(winner == team)
                elif team == first_team:
                    s.defend_decisive += 1
                    s.defend_wins += float(winner == team)


def _date(match: Dict[str, Any]) -> date:
    return date.fromisoformat(str(match["info"]["dates"][0]))


def build_feature_rows(matches: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Emit one leakage-safe supervised row for each decisive men's ODI."""
    ordered = sorted(matches, key=lambda m: (_date(m), str(m.get("_match_id", ""))))
    engine = FeatureEngine()
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

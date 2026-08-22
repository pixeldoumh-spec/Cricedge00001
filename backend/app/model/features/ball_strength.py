"""Leakage-safe team batting/bowling strength from prior deliveries."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from app.model.data.normalizer import CanonicalMatch


@dataclass(frozen=True)
class BallStrengthFeatures:
    batting_run_rate: float
    bowling_run_rate: float
    batting_wicket_rate: float
    bowling_wicket_rate: float


@dataclass
class TeamBallState:
    runs: int = 0
    balls: int = 0
    wickets_lost: int = 0
    runs_conceded: int = 0
    balls_bowled: int = 0
    wickets_taken: int = 0


class BallStrengthEngine:
    """Maintain team aggregates and expose only pre-match state."""

    def __init__(self) -> None:
        self._state: dict[str, TeamBallState] = defaultdict(TeamBallState)

    @staticmethod
    def _rate(value: int, denominator: int, default: float = 0.0) -> float:
        return value / denominator if denominator else default

    def features_before(self, team: str, opponent: str) -> BallStrengthFeatures:
        a = self._state[team]
        b = self._state[opponent]
        return BallStrengthFeatures(
            batting_run_rate=self._rate(a.runs * 6, a.balls),
            bowling_run_rate=self._rate(b.runs_conceded * 6, b.balls_bowled),
            batting_wicket_rate=self._rate(a.wickets_lost * 6, a.balls),
            bowling_wicket_rate=self._rate(b.wickets_taken * 6, b.balls_bowled),
        )

    def update_after_match(self, match: CanonicalMatch) -> None:
        """Update aggregates only after the complete match is known."""
        if len(match.teams) != 2 or not match.deliveries:
            return
        for delivery in match.deliveries:
            if delivery.batting_team not in match.teams or delivery.bowling_team not in match.teams:
                continue
            batting = self._state[delivery.batting_team]
            bowling = self._state[delivery.bowling_team]
            batting.runs += delivery.total_runs
            # Delivery records represent legal and illegal balls alike; this
            # conservative first version excludes wides/no-balls from the ball
            # denominator using the raw extras payload only when available is
            # not possible here, so count every delivery consistently.
            batting.balls += 1
            batting.wickets_lost += int(delivery.wicket)
            bowling.runs_conceded += delivery.total_runs
            bowling.balls_bowled += 1
            bowling.wickets_taken += int(delivery.wicket)


def build_ball_strength_features(
    matches: list[CanonicalMatch],
) -> list[tuple[CanonicalMatch, BallStrengthFeatures]]:
    """Build chronological, leakage-safe ball-strength features."""
    engine = BallStrengthEngine()
    rows: list[tuple[CanonicalMatch, BallStrengthFeatures]] = []
    for match in sorted(matches, key=lambda m: m.dates[0] if m.dates else ""):
        if len(match.teams) != 2:
            continue
        team, opponent = match.teams
        rows.append((match, engine.features_before(team, opponent)))
        engine.update_after_match(match)
    return rows

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
        """Update team aggregates only after the complete match."""
        if len(match.teams) != 2 or not match.deliveries:
            return
        team_a, team_b = match.teams
        # Canonical delivery records don't currently retain the batting team.
        # The first innings belongs to teams[0] and the second to teams[1] only
        # in the common case; without innings-team metadata we must not guess.
        # Keep this boundary conservative until the normalizer exposes it.
        return


def build_ball_strength_features(
    matches: list[CanonicalMatch],
) -> list[tuple[CanonicalMatch, BallStrengthFeatures]]:
    """Build chronological ball-strength rows when innings ownership is known."""
    engine = BallStrengthEngine()
    rows: list[tuple[CanonicalMatch, BallStrengthFeatures]] = []
    for match in sorted(matches, key=lambda m: m.dates[0] if m.dates else ""):
        if len(match.teams) != 2:
            continue
        team, opponent = match.teams
        rows.append((match, engine.features_before(team, opponent)))
        engine.update_after_match(match)
    return rows

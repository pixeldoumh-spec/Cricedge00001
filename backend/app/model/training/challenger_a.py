"""T20 Challenger A: correct ball-rate denominators without changing the model class.

The experiment changes only the denominator used by the four ball-strength
features. A delivery is counted as legal unless it contains a wide or no-ball.
All other V0 feature definitions, chronological state updates, population,
split, estimator, and evaluation rules are kept unchanged.

This is a challenger, not a modification of V0/W0.
"""

from __future__ import annotations

from typing import Sequence

from app.model.data.normalizer import CanonicalMatch
from app.model.training.model_v0 import (
    ELO_K_FACTOR,
    FEATURES,
    INITIAL_ELO,
)
from app.model.features.context import ContextFeatureEngine
from app.model.features.team_form import TeamFormEngine


class LegalBallStrengthEngine:
    """Maintain ball aggregates using legal deliveries as denominators only."""

    def __init__(self) -> None:
        from collections import defaultdict
        from app.model.features.ball_strength import TeamBallState

        self._state = defaultdict(TeamBallState)

    @staticmethod
    def _rate(value: int, denominator: int, default: float = 0.0) -> float:
        return value / denominator if denominator else default

    def features_before(self, team: str, opponent: str):
        a = self._state[team]
        b = self._state[opponent]
        from app.model.features.ball_strength import BallStrengthFeatures
        return BallStrengthFeatures(
            batting_run_rate=self._rate(a.runs * 6, a.balls),
            bowling_run_rate=self._rate(b.runs_conceded * 6, b.balls_bowled),
            batting_wicket_rate=self._rate(a.wickets_lost * 6, a.balls),
            bowling_wicket_rate=self._rate(b.wickets_taken * 6, b.balls_bowled),
        )

    def update_after_match(self, match: CanonicalMatch) -> None:
        if len(match.teams) != 2 or not match.deliveries:
            return
        for delivery in match.deliveries:
            if delivery.batting_team not in match.teams or delivery.bowling_team not in match.teams:
                continue
            batting = self._state[delivery.batting_team]
            bowling = self._state[delivery.bowling_team]
            batting.runs += delivery.total_runs
            bowling.runs_conceded += delivery.total_runs
            batting.wickets_lost += int(delivery.wicket)
            bowling.wickets_taken += int(delivery.wicket)
            if delivery.legal_ball:
                batting.balls += 1
                bowling.balls_bowled += 1


def build_challenger_a_feature_rows(
    matches: Sequence[CanonicalMatch],
) -> list[dict]:
    """Build the V0 feature contract with only legal-ball rate denominators changed."""
    ordered = sorted(matches, key=lambda m: m.dates[0] if m.dates else "")
    team_engine = TeamFormEngine(initial_elo=INITIAL_ELO, k_factor=ELO_K_FACTOR)
    context_engine = ContextFeatureEngine()
    ball_engine = LegalBallStrengthEngine()
    rows: list[dict] = []
    for match in ordered:
        if len(match.teams) != 2 or match.winner not in match.teams:
            continue
        team, opponent = match.teams
        team_features = team_engine.features_before(team, opponent)
        context_features = context_engine.features_before(match)
        ball_features = ball_engine.features_before(team, opponent)
        rows.append({
            **team_features.__dict__,
            **context_features.__dict__,
            **ball_features.__dict__,
            "match_id": match.match_id,
            "date": match.dates[0] if match.dates else "",
            "target": int(match.winner == team),
        })
        team_engine.update_after_match(match)
        context_engine.update_after_match(match)
        ball_engine.update_after_match(match)
    return rows


def changed_features(v0_rows: Sequence[dict], challenger_rows: Sequence[dict]) -> set[str]:
    """Return feature names whose values changed for any shared match row."""
    by_v0 = {r["match_id"]: r for r in v0_rows}
    by_challenger = {r["match_id"]: r for r in challenger_rows}
    changed: set[str] = set()
    for match_id in by_v0.keys() & by_challenger.keys():
        for name in FEATURES:
            if float(by_v0[match_id][name]) != float(by_challenger[match_id][name]):
                changed.add(name)
    return changed

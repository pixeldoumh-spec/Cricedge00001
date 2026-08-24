"""T20 Challenger B: faster-adapting Elo strength representation.

The only modeling change from the current V0/W0 reference is the Elo K-factor.
K is selected on the chronological validation partition by validation log loss
from a predeclared grid. All other feature engines, feature ordering, estimator,
population and split rules remain unchanged.

This module is an experiment only; it does not modify V0 or W0 artifacts.
"""

from __future__ import annotations

from typing import Sequence

import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.model.data.normalizer import CanonicalMatch
from app.model.features.ball_strength import BallStrengthEngine
from app.model.features.context import ContextFeatureEngine
from app.model.features.team_form import TeamFormEngine
from app.model.training.model_v0 import FEATURES, INITIAL_ELO

DEFAULT_K_GRID = (20.0, 40.0, 60.0, 80.0, 120.0, 160.0, 240.0, 320.0)


def build_challenger_b_feature_rows(
    matches: Sequence[CanonicalMatch],
    k_factor: float,
) -> list[dict]:
    """Build the frozen 13-feature contract with only Elo responsiveness changed."""
    ordered = sorted(matches, key=lambda m: m.dates[0] if m.dates else "")
    team_engine = TeamFormEngine(initial_elo=INITIAL_ELO, k_factor=k_factor)
    context_engine = ContextFeatureEngine()
    ball_engine = BallStrengthEngine()
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


def fit_logistic(train: pd.DataFrame) -> Pipeline:
    model = Pipeline([
        ("scale", StandardScaler()),
        ("logistic", LogisticRegression(max_iter=2000)),
    ])
    model.fit(train[FEATURES], train["target"])
    return model

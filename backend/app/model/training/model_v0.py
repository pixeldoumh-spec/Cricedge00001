"""Canonical Model v0: chronological 13-feature logistic-regression baseline.

The model consumes only pre-match state derived from CanonicalMatch. All stateful
feature engines are updated strictly after a match result is known, so no future
match outcome or delivery data enters a row's features.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss

from app.model.data.normalizer import CanonicalMatch
from app.model.features.ball_strength import BallStrengthEngine
from app.model.features.context import ContextFeatureEngine
from app.model.features.team_form import TeamFormEngine
from app.model.training.splits import chronological_split

MODEL_VERSION = "v0"

FEATURES = [
    "team_elo",
    "opponent_elo",
    "elo_difference",
    "team_form_3",
    "team_form_5",
    "team_form_10",
    "venue_team_win_rate",
    "venue_bat_first_win_rate",
    "head_to_head_win_rate",
    "batting_run_rate",
    "bowling_run_rate",
    "batting_wicket_rate",
    "bowling_wicket_rate",
]

INITIAL_ELO = 1500.0
ELO_K_FACTOR = 20.0


@dataclass(frozen=True)
class ModelV0Result:
    train_size: int
    validation_size: int
    test_size: int
    metrics: dict[str, float]


def build_v0_feature_rows(matches: Sequence[CanonicalMatch]) -> list[dict]:
    """Build the exact frozen 13-feature contract chronologically."""
    ordered = sorted(matches, key=lambda m: m.dates[0] if m.dates else "")
    team_engine = TeamFormEngine(initial_elo=INITIAL_ELO, k_factor=ELO_K_FACTOR)
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


def train_model_v0(matches: Sequence[CanonicalMatch]) -> tuple[Pipeline, ModelV0Result]:
    rows = build_v0_feature_rows(matches)
    by_id = {row["match_id"]: row for row in rows}
    match_by_id = {match.match_id: match for match in matches}
    eligible_matches = [match_by_id[row["match_id"]] for row in rows]
    train_matches, validation_matches, test_matches = chronological_split(eligible_matches)

    def frame(items: Sequence[CanonicalMatch]) -> pd.DataFrame:
        return pd.DataFrame([by_id[match.match_id] for match in items])

    train = frame(train_matches)
    validation = frame(validation_matches)
    test = frame(test_matches)
    _ = validation

    model = Pipeline([
        ("scale", StandardScaler()),
        ("logistic", LogisticRegression(max_iter=2000)),
    ])
    model.fit(train[FEATURES], train.target)

    probabilities = model.predict_proba(test[FEATURES])[:, 1]
    predictions = probabilities >= 0.5
    metrics = {
        "accuracy": float(accuracy_score(test.target, predictions)),
        "log_loss": float(log_loss(test.target, probabilities)),
        "brier_score": float(brier_score_loss(test.target, probabilities)),
    }
    return model, ModelV0Result(len(train), len(validation), len(test), metrics)

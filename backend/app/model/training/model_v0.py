"""Model v0: chronological logistic-regression baseline.

Consumes the leakage-safe Elo/form feature rows produced from CanonicalMatch.
The raw Cricsheet archive is intentionally not part of the repository.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss

from app.model.data.normalizer import CanonicalMatch
from app.model.features.team_form import build_team_features
from app.model.training.splits import chronological_split

FEATURES = [
    "team_elo",
    "opponent_elo",
    "elo_difference",
    "form_3",
    "form_5",
    "form_10",
]


@dataclass(frozen=True)
class ModelV0Result:
    train_size: int
    validation_size: int
    test_size: int
    metrics: dict[str, float]


def train_model_v0(matches: Sequence[CanonicalMatch]) -> tuple[Pipeline, ModelV0Result]:
    rows = build_team_features(list(matches))
    train_matches, validation_matches, test_matches = chronological_split(
        [row[0] for row in rows]
    )
    by_id = {match.match_id: features for match, features in rows}

    def frame(items):
        import pandas as pd
        records = []
        for match in items:
            f = by_id[match.match_id]
            records.append({**f.__dict__, "target": int(match.winner == match.teams[0])})
        return pd.DataFrame(records)

    train = frame(train_matches)
    validation = frame(validation_matches)
    test = frame(test_matches)

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

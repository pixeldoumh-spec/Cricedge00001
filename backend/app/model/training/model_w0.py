"""Women's T20 Model W0 experiment.

W0 is intentionally separate from the frozen men's Model v0. It uses the same
leakage-safe 13-feature architecture and validation-only Platt calibration, but
its training population and chronological evaluation are entirely women's T20.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

from app.model.data.normalizer import CanonicalMatch
from app.model.training.calibration import ValidationPlattCalibrator
from app.model.training.model_v0 import FEATURES, build_v0_feature_rows

MODEL_VERSION = "W0"


@dataclass(frozen=True)
class ModelW0Result:
    train_size: int
    validation_size: int
    test_size: int
    metrics: dict[str, float]


def _ece(targets: np.ndarray, probabilities: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0.0, 1.0, bins + 1)
    total = len(targets)
    value = 0.0
    for i in range(bins):
        mask = (probabilities >= edges[i]) & (
            probabilities <= edges[i + 1] if i == bins - 1 else probabilities < edges[i + 1]
        )
        if not np.any(mask):
            continue
        value += (mask.sum() / total) * abs(targets[mask].mean() - probabilities[mask].mean())
    return float(value)


def _split(items: list[CanonicalMatch]) -> tuple[list[CanonicalMatch], list[CanonicalMatch], list[CanonicalMatch]]:
    n = len(items)
    train_end = int(n * 0.70)
    validation_end = int(n * 0.85)
    return items[:train_end], items[train_end:validation_end], items[validation_end:]


def train_model_w0(matches: Sequence[CanonicalMatch]) -> tuple[Pipeline, ValidationPlattCalibrator, ModelW0Result]:
    """Train/evaluate W0 without touching men's v0 artifacts or state."""
    rows = build_v0_feature_rows(matches)
    by_id = {row["match_id"]: row for row in rows}
    match_by_id = {match.match_id: match for match in matches}
    eligible = [match_by_id[row["match_id"]] for row in rows]
    eligible.sort(key=lambda m: m.dates[0] if m.dates else "")
    train_matches, validation_matches, test_matches = _split(eligible)

    def frame(items: Sequence[CanonicalMatch]) -> pd.DataFrame:
        return pd.DataFrame([by_id[m.match_id] for m in items])

    train = frame(train_matches)
    validation = frame(validation_matches)
    test = frame(test_matches)

    model = Pipeline([
        ("scale", StandardScaler()),
        ("logistic", LogisticRegression(max_iter=2000)),
    ])
    model.fit(train[FEATURES], train.target)

    validation_raw = model.predict_proba(validation[FEATURES])[:, 1]
    calibrator = ValidationPlattCalibrator().fit(validation_raw, validation.target.to_numpy())
    test_raw = model.predict_proba(test[FEATURES])[:, 1]
    test_prob = calibrator.predict_proba(test_raw)
    test_target = test.target.to_numpy()

    metrics = {
        "accuracy": float(accuracy_score(test_target, test_prob >= 0.5)),
        "log_loss": float(log_loss(test_target, test_prob)),
        "brier_score": float(brier_score_loss(test_target, test_prob)),
        "auc": float(roc_auc_score(test_target, test_prob)),
        "ece": _ece(test_target, test_prob),
    }
    return model, calibrator, ModelW0Result(
        len(train_matches), len(validation_matches), len(test_matches), metrics
    )

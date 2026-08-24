"""Diagnostic decomposition of T20 strength responsiveness.

This module does not create a replacement model. It is intended to explain
whether Challenger B's larger Elo K is evidence of genuine temporal strength
adaptation or merely compensates for another weakness.

Diagnostics are computed strictly chronologically. No test or future-holdout
observation may be used to select K or representation parameters.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.model.training.challenger_b import build_challenger_b_feature_rows
from app.model.data.normalizer import CanonicalMatch
from app.model.training.model_v0 import FEATURES


@dataclass(frozen=True)
class RollingOrigin:
    train_end: int
    validation_end: int
    test_end: int


def make_model() -> Pipeline:
    return Pipeline([
        ("scale", StandardScaler()),
        ("logistic", LogisticRegression(max_iter=2000)),
    ])


def fit_score(train: pd.DataFrame, evaluate: pd.DataFrame) -> float:
    model = make_model()
    model.fit(train[FEATURES], train["target"])
    return float(log_loss(evaluate["target"], model.predict_proba(evaluate[FEATURES])[:, 1]))


def k_sensitivity(
    rows: Sequence[dict],
    origins: Sequence[RollingOrigin],
    k_values: Sequence[float],
) -> pd.DataFrame:
    """Score predeclared K values on validation only for each origin."""
    frame = pd.DataFrame(rows).sort_values(["date", "match_id"], kind="mergesort").reset_index(drop=True)
    records: list[dict] = []
    for origin_index, origin in enumerate(origins, start=1):
        train = frame.iloc[:origin.train_end]
        validation = frame.iloc[origin.train_end:origin.validation_end]
        for k in k_values:
            # Rows passed here must already have been generated for this K.
            k_frame = frame[frame["k_factor"] == float(k)]
            k_train = k_frame.iloc[:origin.train_end]
            k_validation = k_frame.iloc[origin.train_end:origin.validation_end]
            score = fit_score(k_train, k_validation)
            records.append({
                "origin": origin_index,
                "k": float(k),
                "validation_log_loss": score,
            })
    return pd.DataFrame(records)


def summarize_k_sensitivity(scores: pd.DataFrame) -> dict:
    """Return the per-origin winner and stability counts without touching test data."""
    winners = (
        scores.sort_values(["origin", "validation_log_loss", "k"])
        .groupby("origin", as_index=False)
        .first()
    )
    counts = winners["k"].value_counts().sort_index().to_dict()
    return {
        "origin_winners": winners.to_dict(orient="records"),
        "winner_counts": {str(k): int(v) for k, v in counts.items()},
        "number_of_origins": int(scores["origin"].nunique()),
    }


def elo_drift_summary(rows: Sequence[dict]) -> pd.DataFrame:
    """Summarize the distribution of strength state by chronological era."""
    frame = pd.DataFrame(rows).sort_values(["date", "match_id"], kind="mergesort").copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["year"] = frame["date"].dt.year
    return (
        frame.groupby("year", dropna=True)
        .agg(
            matches=("match_id", "count"),
            team_elo_mean=("team_elo", "mean"),
            team_elo_std=("team_elo", "std"),
            opponent_elo_mean=("opponent_elo", "mean"),
            opponent_elo_std=("opponent_elo", "std"),
            elo_difference_mean=("elo_difference", "mean"),
            elo_difference_std=("elo_difference", "std"),
        )
        .reset_index()
    )


def strength_feature_redundancy(rows: Sequence[dict]) -> dict:
    """Measure correlation among the three existing Elo-derived predictors."""
    frame = pd.DataFrame(rows)
    corr = frame[["team_elo", "opponent_elo", "elo_difference"]].corr()
    return corr.to_dict()

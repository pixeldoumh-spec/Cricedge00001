"""T20 Challenger B calibration/reconciliation helpers.

Keep Challenger B's selected Elo K fixed (male=80, female=160) and change only
the probability calibration applied after the frozen logistic model. Calibration
is fitted strictly on each chronological validation slice.
"""
from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd

from app.model.training.calibration import ValidationPlattCalibrator
from app.model.training.challenger_b import fit_logistic
from app.model.training.model_v0 import FEATURES

SELECTED_K = {"male": 80.0, "female": 160.0}


def fit_and_predict(train: pd.DataFrame, validation: pd.DataFrame, evaluation: pd.DataFrame):
    model = fit_logistic(train)
    validation_raw = model.predict_proba(validation[FEATURES])[:, 1]
    evaluation_raw = model.predict_proba(evaluation[FEATURES])[:, 1]
    calibrator = ValidationPlattCalibrator().fit(
        validation_raw, validation["target"].to_numpy(dtype=int)
    )
    evaluation_calibrated = calibrator.predict_proba(evaluation_raw)
    return model, calibrator, validation_raw, evaluation_raw, evaluation_calibrated


def ece(targets: np.ndarray, probabilities: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0.0, 1.0, bins + 1)
    total = len(targets)
    value = 0.0
    for i in range(bins):
        mask = (probabilities >= edges[i]) & (
            probabilities <= edges[i + 1]
            if i == bins - 1
            else probabilities < edges[i + 1]
        )
        if np.any(mask):
            value += (mask.sum() / total) * abs(
                targets[mask].mean() - probabilities[mask].mean()
            )
    return float(value)


def metrics(targets: np.ndarray, probabilities: np.ndarray) -> dict[str, float]:
    from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, roc_auc_score
    return {
        "accuracy": float(accuracy_score(targets, probabilities >= 0.5)),
        "log_loss": float(log_loss(targets, probabilities, labels=[0, 1])),
        "brier_score": float(brier_score_loss(targets, probabilities)),
        "auc": float(roc_auc_score(targets, probabilities)),
        "ece_10": ece(targets, probabilities),
    }


def rolling_origin(rows: Sequence[dict], windows=(0.50, 0.55, 0.60, 0.65, 0.70)) -> list[dict]:
    """Five chronological windows; each calibrator sees only its validation slice."""
    n = len(rows)
    out = []
    for fraction in windows:
        train_end = int(n * fraction)
        validation_size = max(1, int(n * 0.10))
        test_size = max(1, int(n * 0.10))
        val_end = train_end + validation_size
        test_end = min(n, val_end + test_size)
        if train_end < 100 or test_end <= val_end:
            continue
        train = pd.DataFrame(rows[:train_end])
        validation = pd.DataFrame(rows[train_end:val_end])
        evaluation = pd.DataFrame(rows[val_end:test_end])
        _, _, _, raw, calibrated = fit_and_predict(train, validation, evaluation)
        y = evaluation["target"].to_numpy(dtype=int)
        raw_m = metrics(y, raw)
        cal_m = metrics(y, calibrated)
        out.append({
            "train_fraction": fraction,
            "train": train_end,
            "validation": val_end - train_end,
            "evaluation": test_end - val_end,
            "raw": raw_m,
            "calibrated": cal_m,
            "calibrated_beats_raw": {
                key: cal_m[key] < raw_m[key]
                if key in {"log_loss", "brier_score", "ece_10"}
                else cal_m[key] > raw_m[key]
                for key in ("accuracy", "log_loss", "brier_score", "auc", "ece_10")
            },
        })
    return out

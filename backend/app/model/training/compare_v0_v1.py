"""Reproducible apples-to-apples evaluator for frozen Model v0 vs Model v1.

The evaluator intentionally owns the split protocol and calibration boundary:
2,387 train / 511 validation / 513 test, chronological and unchanged.
It never fits calibration on test predictions.

This module expects a prebuilt chronological feature table with one row per
eligible men's T20 match and the frozen feature columns used by v0/v1.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from app.model.training.model_v1 import FEATURE_NAMES, ModelV1

TRAIN_SIZE = 2387
VALIDATION_SIZE = 511
TEST_SIZE = 513
TOTAL_SIZE = TRAIN_SIZE + VALIDATION_SIZE + TEST_SIZE


@dataclass(frozen=True)
class Metrics:
    accuracy: float
    log_loss: float
    brier_score: float
    roc_auc: float
    ece_10: float


def _ece(probabilities: Sequence[float], targets: Sequence[int], bins: int = 10) -> float:
    p = np.asarray(probabilities, dtype=float)
    y = np.asarray(targets, dtype=int)
    edges = np.linspace(0.0, 1.0, bins + 1)
    total = len(y)
    value = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (p >= lo) & (p < hi)
        if hi == 1.0:
            mask |= p == hi
        if not mask.any():
            continue
        value += mask.mean() * abs(y[mask].mean() - p[mask].mean())
    return float(value)


def evaluate(y_true: Sequence[int], probabilities: Sequence[float]) -> Metrics:
    p = np.asarray(probabilities)
    y = np.asarray(y_true)
    return Metrics(
        accuracy=float(accuracy_score(y, p >= 0.5)),
        log_loss=float(log_loss(y, p, labels=[0, 1])),
        brier_score=float(brier_score_loss(y, p)),
        roc_auc=float(roc_auc_score(y, p)),
        ece_10=_ece(p, y),
    )


def chronological_split(rows: Sequence[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    if len(rows) != TOTAL_SIZE:
        raise ValueError(f"expected exactly {TOTAL_SIZE} rows, got {len(rows)}")
    ordered = list(rows)
    return (
        ordered[:TRAIN_SIZE],
        ordered[TRAIN_SIZE : TRAIN_SIZE + VALIDATION_SIZE],
        ordered[TRAIN_SIZE + VALIDATION_SIZE :],
    )


def _matrix(rows: Sequence[dict]) -> np.ndarray:
    return np.asarray(
        [[float(row.get(name, 0.0)) for name in FEATURE_NAMES] for row in rows],
        dtype=float,
    )


def _targets(rows: Sequence[dict]) -> np.ndarray:
    return np.asarray([int(row["target"]) for row in rows], dtype=int)


def _fit_v0(train: Sequence[dict]):
    model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, random_state=0))
    model.fit(_matrix(train), _targets(train))
    return model


def _fit_v1(train: Sequence[dict]):
    return ModelV1().fit(train, _targets(train))


def run_comparison(rows: Sequence[dict]) -> dict[str, Metrics]:
    train, validation, test = chronological_split(rows)
    y_test = _targets(test)

    results: dict[str, Metrics] = {}
    for name, fitter in (("v0", _fit_v0), ("v1", _fit_v1)):
        model = fitter(train)
        validation_prob = model.predict_proba(_matrix(validation) if name == "v0" else validation)
        test_prob = model.predict_proba(_matrix(test) if name == "v0" else test)

        # Fit a one-dimensional Platt calibrator on validation predictions only.
        calibrator = LogisticRegression(max_iter=1000, random_state=0)
        calibrator.fit(validation_prob.reshape(-1, 1), _targets(validation))
        calibrated_test = calibrator.predict_proba(test_prob.reshape(-1, 1))[:, 1]
        results[name] = evaluate(y_test, calibrated_test)

    return results


def format_report(results: dict[str, Metrics]) -> str:
    lines = [
        "# Model v0 vs Model v1 — frozen apples-to-apples evaluation",
        "",
        "Split: chronological 2,387 train / 511 validation / 513 test.",
        "Calibration: one-dimensional Platt scaling fitted on validation predictions only.",
        "Test set: untouched until final evaluation.",
        "",
        "| Metric | v0 | v1 |",
        "|---|---:|---:|",
    ]
    for metric in ("accuracy", "log_loss", "brier_score", "roc_auc", "ece_10"):
        a, b = results["v0"], results["v1"]
        label = {"accuracy":"Accuracy", "log_loss":"Log loss", "brier_score":"Brier score", "roc_auc":"ROC AUC", "ece_10":"10-bin ECE"}[metric]
        lines.append(f"| {label} | {getattr(a, metric):.5f} | {getattr(b, metric):.5f} |")
    return "\n".join(lines) + "\n"

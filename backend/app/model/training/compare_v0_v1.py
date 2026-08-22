"""Reproducible apples-to-apples evaluator for frozen Model v0 vs Model v1."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
from scipy.special import logit
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
    value = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (p >= lo) & ((p < hi) | (hi == 1.0))
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
    model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, random_state=0))
    model.fit(_matrix(train), _targets(train))
    return model


def _fit_v1(train: Sequence[dict]):
    return ModelV1().fit(train, _targets(train))


def _calibrate(validation_prob: np.ndarray, validation_targets: np.ndarray, test_prob: np.ndarray) -> np.ndarray:
    """Match ValidationPlattCalibrator: fit on logit(p), never on test targets."""
    validation_prob = np.clip(np.asarray(validation_prob, dtype=float), 1e-6, 1 - 1e-6)
    test_prob = np.clip(np.asarray(test_prob, dtype=float), 1e-6, 1 - 1e-6)
    calibrator = LogisticRegression(max_iter=2000)
    calibrator.fit(logit(validation_prob).reshape(-1, 1), validation_targets)
    return calibrator.predict_proba(logit(test_prob).reshape(-1, 1))[:, 1]


def run_comparison(rows: Sequence[dict]) -> dict[str, Metrics]:
    train, validation, test = chronological_split(rows)
    y_test = _targets(test)
    results: dict[str, Metrics] = {}
    for name, fitter in (("v0", _fit_v0), ("v1", _fit_v1)):
        model = fitter(train)
        if name == "v0":
            validation_prob = model.predict_proba(_matrix(validation))[:, 1]
            test_prob = model.predict_proba(_matrix(test))[:, 1]
        else:
            validation_prob = model.predict_proba(validation)
            test_prob = model.predict_proba(test)
        calibrated_test = _calibrate(validation_prob, _targets(validation), test_prob)
        results[name] = evaluate(y_test, calibrated_test)
    return results


def format_report(results: dict[str, Metrics]) -> str:
    lines = [
        "# Model v0 vs Model v1 — frozen apples-to-apples evaluation",
        "",
        "Split: chronological 2,387 train / 511 validation / 513 test.",
        "Features: the frozen v0 feature set for both models.",
        "Calibration: validation-only Platt scaling on logit probabilities.",
        "Test set: untouched until final evaluation.",
        "",
        "| Metric | v0 | v1 |",
        "|---|---:|---:|",
    ]
    labels = {"accuracy":"Accuracy", "log_loss":"Log loss", "brier_score":"Brier score", "roc_auc":"ROC AUC", "ece_10":"10-bin ECE"}
    for metric, label in labels.items():
        a, b = results["v0"], results["v1"]
        lines.append(f"| {label} | {getattr(a, metric):.5f} | {getattr(b, metric):.5f} |")
    return "\n".join(lines) + "\n"

"""Leakage-safe calibration candidate selection for production evaluation.

Candidates are selected from out-of-fold predictions inside validation only.
The untouched test set is never inspected during selection.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.special import logit
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss
from sklearn.model_selection import StratifiedKFold


@dataclass(frozen=True)
class CalibrationSelection:
    name: str
    validation_log_loss: float
    validation_brier: float
    validation_ece: float


class RawCalibrator:
    name = "raw"

    def fit(self, probabilities: np.ndarray, targets: np.ndarray) -> "RawCalibrator":
        return self

    def predict_proba(self, probabilities: np.ndarray) -> np.ndarray:
        return np.asarray(probabilities, dtype=float)


class PlattCalibrator:
    name = "platt"

    def __init__(self) -> None:
        self._model = LogisticRegression(max_iter=2000)

    def fit(self, probabilities: np.ndarray, targets: np.ndarray) -> "PlattCalibrator":
        p = np.clip(np.asarray(probabilities, dtype=float), 1e-6, 1 - 1e-6)
        self._model.fit(logit(p).reshape(-1, 1), np.asarray(targets, dtype=int))
        return self

    def predict_proba(self, probabilities: np.ndarray) -> np.ndarray:
        p = np.clip(np.asarray(probabilities, dtype=float), 1e-6, 1 - 1e-6)
        return self._model.predict_proba(logit(p).reshape(-1, 1))[:, 1]


class IsotonicCalibrator:
    name = "isotonic"

    def __init__(self) -> None:
        self._model = IsotonicRegression(out_of_bounds="clip")

    def fit(self, probabilities: np.ndarray, targets: np.ndarray) -> "IsotonicCalibrator":
        self._model.fit(np.asarray(probabilities, dtype=float), np.asarray(targets, dtype=int))
        return self

    def predict_proba(self, probabilities: np.ndarray) -> np.ndarray:
        return np.asarray(self._model.predict(np.asarray(probabilities, dtype=float)), dtype=float)


def _ece(y: np.ndarray, p: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0.0, 1.0, bins + 1)
    value = 0.0
    for i in range(bins):
        mask = (p >= edges[i]) & (p <= edges[i + 1] if i == bins - 1 else p < edges[i + 1])
        if mask.any():
            value += mask.mean() * abs(float(y[mask].mean()) - float(p[mask].mean()))
    return float(value)


def _metrics(y: np.ndarray, p: np.ndarray) -> tuple[float, float, float]:
    return (
        float(log_loss(y, np.clip(p, 1e-6, 1 - 1e-6), labels=[0, 1])),
        float(brier_score_loss(y, p)),
        _ece(y, p),
    )


def select_calibrator(
    validation_probabilities: np.ndarray,
    targets: np.ndarray,
    *,
    folds: int = 5,
    random_state: int = 20260822,
) -> tuple[Any, CalibrationSelection, list[CalibrationSelection]]:
    """Select and refit a calibrator using validation data only.

    Candidate ranking uses OOF validation predictions. The chosen candidate is
    then refit on the complete validation set and returned for the untouched
    test set. Raw probabilities are a first-class candidate, so calibration is
    never forced when it does not demonstrate validation benefit.
    """
    probabilities = np.asarray(validation_probabilities, dtype=float)
    y = np.asarray(targets, dtype=int)
    if len(probabilities) != len(y):
        raise ValueError("validation probabilities and targets must have equal length")
    if len(np.unique(y)) != 2:
        raise ValueError("calibration validation set must contain both classes")
    splitter = StratifiedKFold(n_splits=folds, shuffle=True, random_state=random_state)
    candidate_types = (RawCalibrator, PlattCalibrator, IsotonicCalibrator)
    selections: list[CalibrationSelection] = []

    for candidate_type in candidate_types:
        oof = np.empty(len(y), dtype=float)
        for fit_idx, predict_idx in splitter.split(probabilities, y):
            candidate = candidate_type().fit(probabilities[fit_idx], y[fit_idx])
            oof[predict_idx] = candidate.predict_proba(probabilities[predict_idx])
        ll, brier, ece = _metrics(y, oof)
        selections.append(CalibrationSelection(candidate_type.name, ll, brier, ece))

    selected = min(selections, key=lambda item: (item.validation_log_loss, item.validation_brier, item.validation_ece, item.name))
    selected_type = next(candidate for candidate in candidate_types if candidate.name == selected.name)
    fitted = selected_type().fit(probabilities, y)
    return fitted, selected, selections


def calibration_report(selection: CalibrationSelection, candidates: list[CalibrationSelection]) -> dict[str, object]:
    return {
        "selected": selection.name,
        "selection_basis": "5-fold OOF validation predictions; log loss, then Brier, then ECE",
        "candidates": [
            {"name": c.name, "oof_log_loss": c.validation_log_loss, "oof_brier": c.validation_brier, "oof_ece": c.validation_ece}
            for c in candidates
        ],
        "test_used_for_selection": False,
    }

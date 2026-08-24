"""Strictly chronological adaptive calibration for T20 Challenger B.

This is a diagnostic calibration layer, not a model replacement.  It never
fits a calibration mapping using the period being evaluated.  For each
validation/test/holdout prediction, calibration is fit only from predictions
whose match dates precede the prediction date, using a bounded trailing window
when configured.  The underlying Challenger B ranking/probabilities are left
unchanged before calibration.

The purpose is to test whether calibration drift is temporal rather than to
search a black-box calibrator.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
from sklearn.linear_model import LogisticRegression


@dataclass(frozen=True)
class AdaptiveCalibrationConfig:
    window: int = 250
    min_history: int = 100
    refit_every: int = 25


class ChronologicalPlattCalibrator:
    """Online Platt calibration with no look-ahead.

    Input rows must already be in chronological order.  For row i, only rows
    before i can be used.  The optional trailing window is applied after the
    chronological cutoff.  A prediction is left raw until min_history
    previous labeled predictions are available.
    """

    def __init__(self, config: AdaptiveCalibrationConfig = AdaptiveCalibrationConfig()):
        self.config = config

    @staticmethod
    def _fit(x: np.ndarray, y: np.ndarray) -> LogisticRegression:
        model = LogisticRegression(C=1.0, solver="lbfgs", max_iter=1000)
        model.fit(x.reshape(-1, 1), y)
        return model

    def transform(
        self,
        raw_probabilities: Sequence[float],
        targets: Sequence[int],
    ) -> np.ndarray:
        p = np.asarray(raw_probabilities, dtype=float)
        y = np.asarray(targets, dtype=int)
        if len(p) != len(y):
            raise ValueError("probabilities and targets must have equal length")
        out = p.copy()
        model: LogisticRegression | None = None
        last_fit = -1
        for i in range(len(p)):
            available_end = i
            start = max(0, available_end - self.config.window)
            history_x = p[start:available_end]
            history_y = y[start:available_end]
            if len(history_x) < self.config.min_history or np.unique(history_y).size < 2:
                continue
            if model is None or (i - last_fit) >= self.config.refit_every:
                model = self._fit(history_x, history_y)
                last_fit = i
            out[i] = float(model.predict_proba(np.array([[p[i]]]))[0, 1])
        return out

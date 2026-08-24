"""Run diagnostic temporal-adaptive calibration for T20 Challenger B.

Protocol:
1. Use the already selected B K (80 men's, 160 women's).
2. Preserve the exact frozen chronological population/splits.
3. Fit the underlying Challenger B model only on the training partition.
4. Generate validation/test/future predictions chronologically.
5. Fit calibration at each prediction only from earlier labeled predictions.
6. Never use the current row or any future row to calibrate that prediction.
7. Compare raw B against adaptive calibration; do not change ranking features.

This runner is intentionally diagnostic. It does not modify V0/W0 artifacts.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

import numpy as np
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, roc_auc_score

from app.model.training.temporal_adaptive_calibration import (
    AdaptiveCalibrationConfig,
    ChronologicalPlattCalibrator,
)


def ece(y: np.ndarray, p: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0, 1, bins + 1)
    value = 0.0
    for i in range(bins):
        mask = (p >= edges[i]) & (p <= edges[i + 1] if i == bins - 1 else p < edges[i + 1])
        if mask.any():
            value += mask.mean() * abs(y[mask].mean() - p[mask].mean())
    return float(value)


def metrics(y: np.ndarray, p: np.ndarray) -> dict[str, float]:
    return {
        "accuracy": float(accuracy_score(y, p >= 0.5)),
        "log_loss": float(log_loss(y, p)),
        "brier_score": float(brier_score_loss(y, p)),
        "roc_auc": float(roc_auc_score(y, p)),
        "ece_10": ece(y, p),
    }


def calibrate_chronologically(raw: Sequence[float], y: Sequence[int], config: AdaptiveCalibrationConfig) -> np.ndarray:
    """Apply online calibration where each output uses only earlier labels."""
    return ChronologicalPlattCalibrator(config).transform(raw, y)


def run_diagnostic(raw: Sequence[float], y: Sequence[int], windows: Sequence[int]) -> dict:
    y_arr = np.asarray(y, dtype=int)
    p_arr = np.asarray(raw, dtype=float)
    return {
        "raw": metrics(y_arr, p_arr),
        "adaptive": {
            str(window): metrics(
                y_arr,
                calibrate_chronologically(
                    p_arr,
                    y_arr,
                    AdaptiveCalibrationConfig(window=window, min_history=min(100, window // 2), refit_every=max(10, window // 10)),
                ),
            )
            for window in windows
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Diagnostic temporal adaptive calibration")
    parser.add_argument("--input", type=Path, required=True, help="JSON containing chronological raw B predictions and targets")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--windows", type=int, nargs="+", default=[100, 250, 500])
    args = parser.parse_args(argv)
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    result = run_diagnostic(payload["raw_probabilities"], payload["targets"], args.windows)
    result["protocol"] = {
        "calibration": "chronological online Platt",
        "future_information_used": False,
        "current_target_used_for_current_prediction": False,
        "underlying_model_changed": False,
        "v0_w0_modified": False,
        "windows": args.windows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

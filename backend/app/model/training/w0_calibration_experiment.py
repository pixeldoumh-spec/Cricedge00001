"""Evaluate W0 calibration candidates without changing the frozen W0 contract."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.model.training.calibration_selector import calibration_report, select_calibrator
from app.model.training.model_v0 import FEATURES, build_v0_feature_rows
from app.model.training.w0_robustness import EXPECTED_DECISIVE, EXPECTED_FEATURES, EXPECTED_SPLIT, load_womens_t20


def _ece(y: np.ndarray, p: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0.0, 1.0, bins + 1)
    value = 0.0
    for i in range(bins):
        mask = (p >= edges[i]) & (p <= edges[i + 1] if i == bins - 1 else p < edges[i + 1])
        if mask.any():
            value += mask.mean() * abs(float(y[mask].mean()) - float(p[mask].mean()))
    return float(value)


def _metrics(y: np.ndarray, p: np.ndarray) -> dict[str, float]:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return {
        "accuracy": float(accuracy_score(y, p >= 0.5)),
        "log_loss": float(log_loss(y, p, labels=[0, 1])),
        "brier": float(brier_score_loss(y, p)),
        "auc": float(roc_auc_score(y, p)),
        "ece": _ece(y, p),
    }


def run(archive: Path) -> dict[str, object]:
    matches = load_womens_t20(archive)
    if len(matches) != EXPECTED_DECISIVE:
        raise ValueError(f"expected {EXPECTED_DECISIVE} decisive matches, got {len(matches)}")
    if tuple(FEATURES) != EXPECTED_FEATURES:
        raise ValueError("W0 feature contract changed")

    rows = build_v0_feature_rows(matches)
    if len(rows) != EXPECTED_DECISIVE:
        raise ValueError("W0 feature row count changed")
    train_end, validation_end, test_end = np.cumsum(EXPECTED_SPLIT)
    x = np.asarray([[row[f] for f in FEATURES] for row in rows], dtype=float)
    y = np.asarray([row["target"] for row in rows], dtype=int)

    model = Pipeline([
        ("scale", StandardScaler()),
        ("logistic", LogisticRegression(max_iter=2000)),
    ])
    model.fit(x[:train_end], y[:train_end])
    validation_raw = model.predict_proba(x[train_end:validation_end])[:, 1]
    test_raw = model.predict_proba(x[validation_end:test_end])[:, 1]
    test_y = y[validation_end:test_end]

    calibrator, selected, candidates = select_calibrator(validation_raw, y[train_end:validation_end])
    selected_test = calibrator.predict_proba(test_raw)

    candidate_test_metrics: dict[str, dict[str, float]] = {
        "raw": _metrics(test_y, test_raw),
    }
    from app.model.training.calibration_selector import PlattCalibrator, IsotonicCalibrator
    for name, cls in (("platt", PlattCalibrator), ("isotonic", IsotonicCalibrator)):
        candidate_test_metrics[name] = _metrics(
            test_y,
            cls().fit(validation_raw, y[train_end:validation_end]).predict_proba(test_raw),
        )

    return {
        "contract": {
            "decisive_matches": EXPECTED_DECISIVE,
            "split": {"train": EXPECTED_SPLIT[0], "validation": EXPECTED_SPLIT[1], "test": EXPECTED_SPLIT[2]},
            "features": list(EXPECTED_FEATURES),
            "estimator": "StandardScaler + LogisticRegression(max_iter=2000)",
            "calibration_selection": "5-fold OOF within validation only",
            "test_used_for_selection": False,
        },
        "validation_selection": calibration_report(selected, candidates),
        "untouched_test_candidate_metrics": candidate_test_metrics,
        "selected_candidate_test_metrics": _metrics(test_y, selected_test),
        "production_recommendation": "use selected candidate only after this experiment is repeated on the final chronological holdout; otherwise retain raw probabilities",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate W0 calibration candidates")
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.archive)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

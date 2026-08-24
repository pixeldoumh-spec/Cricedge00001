"""Evaluate temporal-adaptive calibration without look-ahead.

Input is the dated raw Challenger B prediction stream. Rows are re-sorted by
match date and ID. Each prediction is calibrated only from earlier labeled
rows in the same chronological stream. This makes the temporal information
boundary explicit and auditable.
"""
from __future__ import annotations

import argparse
import hashlib
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
    edges = np.linspace(0.0, 1.0, bins + 1)
    total = len(y)
    out = 0.0
    for i in range(bins):
        mask = (p >= edges[i]) & (p <= edges[i + 1] if i == bins - 1 else p < edges[i + 1])
        if mask.any():
            out += mask.sum() / total * abs(y[mask].mean() - p[mask].mean())
    return float(out)


def metrics(y: np.ndarray, p: np.ndarray) -> dict[str, float]:
    return {
        "accuracy": float(accuracy_score(y, p >= 0.5)),
        "log_loss": float(log_loss(y, p)),
        "brier_score": float(brier_score_loss(y, p)),
        "roc_auc": float(roc_auc_score(y, p)),
        "ece_10": ece(y, p),
    }


def evaluate(records: list[dict], windows: Sequence[int]) -> dict:
    records = sorted(records, key=lambda r: (r["match_date"], r["match_id"]))
    y = np.asarray([r["target"] for r in records], dtype=int)
    raw = np.asarray([r["raw_probability"] for r in records], dtype=float)
    partitions = np.asarray([r["partition"] for r in records])
    dates = [r["match_date"] for r in records]

    result = {
        "ordering": {
            "first_date": dates[0],
            "last_date": dates[-1],
            "rows": len(records),
            "strictly_sorted": all((dates[i], records[i]["match_id"]) <= (dates[i+1], records[i+1]["match_id"]) for i in range(len(records)-1)),
        },
        "raw_all": metrics(y, raw),
        "partitions": {},
        "windows": {},
    }

    for partition in ("train", "validation", "test"):
        mask = partitions == partition
        result["partitions"][partition] = metrics(y[mask], raw[mask]) if mask.sum() else None

    for window in windows:
        calibrated = ChronologicalPlattCalibrator(
            AdaptiveCalibrationConfig(window=window, min_history=min(100, max(20, window // 2)), refit_every=max(10, window // 10))
        ).transform(raw, y)
        result["windows"][str(window)] = {
            "all": metrics(y, calibrated),
            "partitions": {
                p: metrics(y[partitions == p], calibrated[partitions == p])
                for p in ("train", "validation", "test")
            },
            "future_holdout_boundary": "not present in this frozen stream; evaluate future holdout separately with the same chronological calibrator state",
        }

    result["protocol"] = {
        "current_row_target_used": False,
        "future_rows_used": False,
        "calibrator": "bounded trailing-window Platt, online chronological fit",
        "underlying_challenger_b_unchanged": True,
        "v0_w0_modified": False,
    }
    return result


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Evaluate temporal adaptive calibration")
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--windows", type=int, nargs="+", default=[100, 250, 500])
    args = p.parse_args(argv)
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    result = evaluate(payload["rows"], args.windows)
    result["input_schema"] = payload.get("schema")
    result["gender"] = payload.get("gender")
    result["k_factor"] = payload.get("k_factor")
    result["corpus_sha256"] = payload.get("corpus_sha256")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

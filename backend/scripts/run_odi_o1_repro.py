"""Reproduce ODI O1 from the locked O0 corpus pipeline.

O1 changes only the two recent-win-rate features to a fixed 20-match
pre-match window. Main 1708/366/366 evaluation is fully specified by the
O1 contract. Historical rolling-origin/future protocols are preserved as
comparison targets but are not silently inferred when their exact procedure
is absent from the recovered source lineage.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Sequence

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, roc_auc_score

from backend.app.model.training.odi_o0_corpus import load_locked_matches
from backend.app.model.training.odi_o1_baseline import train_model_o1, predict_raw
from backend.app.model.training.odi_o1_features import build_feature_rows

EXPECTED_CORPUS_SHA256 = "f0798ef14e1f3f61720d41978289fe7318257263f59edba5dca0b35dbba64d6c"
N_ROWS = 2440
TRAIN_END, VALIDATION_END, TEST_END = 1708, 2074, 2440
FUTURE_ROWS = 122


def ece(y: np.ndarray, p: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0.0, 1.0, bins + 1)
    total = 0.0
    for i in range(bins):
        mask = (p >= edges[i]) & ((p < edges[i + 1]) if i < bins - 1 else (p <= edges[i + 1]))
        if mask.any():
            total += float(mask.mean()) * abs(float(y[mask].mean()) - float(p[mask].mean()))
    return total


def metrics(y: np.ndarray, p: np.ndarray) -> Dict[str, float]:
    return {
        "accuracy": float(accuracy_score(y, p >= 0.5)),
        "log_loss": float(log_loss(y, p)),
        "brier": float(brier_score_loss(y, p)),
        "auc": float(roc_auc_score(y, p)),
        "ece": ece(y, p),
    }


def matrix(rows: Sequence[Dict[str, Any]], feature_names: Sequence[str]):
    X = np.asarray([[r["features"][name] for name in feature_names] for r in rows], dtype=float)
    y = np.asarray([r["target"] for r in rows], dtype=int)
    return X, y


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("corpus", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    matches = load_locked_matches(args.corpus)
    rows = build_feature_rows(matches)
    if len(rows) != N_ROWS:
        raise ValueError(f"expected {N_ROWS} O1 rows, got {len(rows)}")

    # The O1 feature engine deliberately inherits the frozen O0 13-feature
    # schema: two values change, the other eleven remain unchanged.
    feature_names = list(rows[0]["features"].keys())
    X, y = matrix(rows, feature_names)
    if X.shape != (N_ROWS, 13):
        raise ValueError(f"expected O1 matrix shape {(N_ROWS, 13)}, got {X.shape}")

    bundle = train_model_o1(X[:TRAIN_END], y[:TRAIN_END])
    p_val = predict_raw(bundle, X[TRAIN_END:VALIDATION_END])
    p_test = predict_raw(bundle, X[VALIDATION_END:TEST_END])
    platt = LogisticRegression(max_iter=2000).fit(p_val.reshape(-1, 1), y[TRAIN_END:VALIDATION_END])
    isotonic = IsotonicRegression(out_of_bounds="clip").fit(p_val, y[TRAIN_END:VALIDATION_END])
    p_platt = platt.predict_proba(p_test.reshape(-1, 1))[:, 1]
    p_iso = isotonic.predict(p_test)

    # Future holdout is the final 122 locked rows. No future labels are used
    # to fit the model or calibrator here; this result is a raw-prediction
    # reconstruction and is explicitly compared to the preserved artifact.
    future_start = N_ROWS - FUTURE_ROWS
    future_bundle = train_model_o1(X[:future_start], y[:future_start])
    p_future = predict_raw(future_bundle, X[future_start:])

    result: Dict[str, Any] = {
        "model": "men_odi_o1",
        "parent": "men_odi_o0",
        "corpus_sha256": EXPECTED_CORPUS_SHA256,
        "population": {"archive_json": 2569, "decisive_rows": N_ROWS},
        "feature_names": feature_names,
        "main_split": {"train": TRAIN_END, "validation": VALIDATION_END - TRAIN_END, "test": TEST_END - VALIDATION_END},
        "main_test": {
            "raw": metrics(y[VALIDATION_END:TEST_END], p_test),
            "platt": metrics(y[VALIDATION_END:TEST_END], p_platt),
            "isotonic": metrics(y[VALIDATION_END:TEST_END], p_iso),
        },
        "future_holdout": {"rows": FUTURE_ROWS, "raw": metrics(y[future_start:], p_future)},
        "historical_rolling_origin": {
            "preserved_train_fractions": [0.50, 0.55, 0.60, 0.65, 0.70],
            "procedure_recovered": False,
            "status": "UNRECOVERED_PROTOCOL",
        },
        "historical_fingerprint": {
            "value": "a64c5b01d338b08e018c92bf34c30355e41a380ba0209f190fad457bccc60d42",
            "source_recovered": False,
            "reconstructed_candidate_only": True,
        },
        "runner_schema": "ODI O1 reconciliation 1",
    }
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    result["result_sha256"] = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"rows": len(rows), "corpus_sha256": EXPECTED_CORPUS_SHA256, "result": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()

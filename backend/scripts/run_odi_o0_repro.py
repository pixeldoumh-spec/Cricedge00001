"""Reproduce the frozen O0 baseline from the locked corpus."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, roc_auc_score

from app.model.training.odi_o0_corpus import LOCKED_CORPUS_SHA256, build_locked_o0_rows, sha256_file
from app.model.training.odi_o0_baseline import fit_validation_calibrators, train_model_o0, predict_raw, predict_isotonic, predict_platt
from app.model.training.odi_o0_features import FEATURE_NAMES

EXPECTED_FEATURE_FINGERPRINT = "a64c5b01d338b08e018c92bf34c30355e41a380ba0209f190fad457bccc60d42"
EXPECTED_TEST_ISOTONIC = {"log_loss": 0.6749556551, "brier": 0.2412253816, "auc": 0.6364371499}


def ece(y, p, bins=10):
    y = np.asarray(y); p = np.asarray(p)
    edges = np.linspace(0.0, 1.0, bins + 1); value = 0.0
    for i in range(bins):
        mask = (p >= edges[i]) & ((p < edges[i + 1]) if i < bins - 1 else (p <= edges[i + 1]))
        if np.any(mask):
            value += mask.mean() * abs(y[mask].mean() - p[mask].mean())
    return float(value)


def feature_fingerprint(rows):
    # Stable project fingerprint: canonical JSON of the complete supervised rows.
    payload = json.dumps(rows, separators=(",", ":"), sort_keys=True, allow_nan=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def metrics(y, p):
    return {
        "accuracy": float(accuracy_score(y, p >= 0.5)),
        "log_loss": float(log_loss(y, p)),
        "brier": float(brier_score_loss(y, p)),
        "auc": float(roc_auc_score(y, p)),
        "ece": ece(y, p),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("corpus")
    ap.add_argument("--output", default="docs/model/ODI_O0_REPRODUCED_REPORT.json")
    args = ap.parse_args()

    corpus = Path(args.corpus)
    actual_corpus_hash = sha256_file(corpus)
    if actual_corpus_hash != LOCKED_CORPUS_SHA256:
        raise SystemExit("FAIL: corpus SHA-256 does not match the locked O0 contract")

    rows = build_locked_o0_rows(corpus)
    X = np.asarray([[r["features"][n] for n in FEATURE_NAMES] for r in rows], dtype=float)
    y = np.asarray([r["target"] for r in rows], dtype=int)
    if len(rows) != 2440 or X.shape != (2440, 13):
        raise SystemExit("FAIL: canonical O0 population/shape mismatch")

    tr, va, te = slice(0, 1708), slice(1708, 2074), slice(2074, 2440)
    bundle = train_model_o0(X[tr], y[tr])
    pva = predict_raw(bundle, X[va]); pte = predict_raw(bundle, X[te])
    cands = fit_validation_calibrators(pva, y[va])
    ptest_iso = predict_isotonic(cands.isotonic, pte)
    result = {
        "status": "reproduced",
        "corpus_sha256": actual_corpus_hash,
        "population": len(rows),
        "feature_shape": list(X.shape),
        "feature_rows_fingerprint": feature_fingerprint(rows),
        "split": {"train": 1708, "validation": 366, "test": 366},
        "estimator": "StandardScaler + LogisticRegression(max_iter=2000)",
        "selected_calibration": "isotonic",
        "validation_raw": metrics(y[va], pva),
        "untouched_test_isotonic": metrics(y[te], ptest_iso),
        "expected_frozen_test_isotonic": EXPECTED_TEST_ISOTONIC,
        "exact_metric_match": all(abs(metrics(y[te], ptest_iso)[k] - v) < 5e-10 for k, v in EXPECTED_TEST_ISOTONIC.items()),
    }
    if not result["exact_metric_match"]:
        raise SystemExit("FAIL: reproduced O0 metrics do not match the frozen baseline")
    out = Path(args.output); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

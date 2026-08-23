"""Reproduce ODI O10 from the locked corpus.

O10 changes only LogisticRegression C on the frozen O0 13-feature matrix.
C is selected from the frozen candidate set using validation raw log loss.
The runner also evaluates validation-only calibration, untouched test,
rolling-origin windows, and the future holdout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from backend.app.model.training.odi_o0_corpus import load_locked_matches
from backend.app.model.training.odi_o0_features import FEATURE_NAMES, FeatureEngine
from backend.app.model.training.odi_o10_model import (
    CANDIDATE_C,
    fit_o10,
    predict_raw,
    select_C_by_validation_log_loss,
)

CORPUS_SHA256 = "f0798ef14e1f3f61720d41978289fe7318257263f59edba5dca0b35dbba64d6c"
TRAIN_END, VALIDATION_END, TEST_END = 1708, 2074, 2440
FUTURE_TRAIN_END, FUTURE_VALIDATION_END, FUTURE_END = 1586, 1952, 2074
ROLLING_TRAIN_ENDS = (1037, 1244, 1451, 1658, 1865)
ROLLING_WIDTH = 207


def ece(y: np.ndarray, p: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0, 1, bins + 1)
    return float(sum(
        np.mean(mask) * abs(np.mean(y[mask]) - np.mean(p[mask]))
        for i in range(bins)
        for mask in [((p >= edges[i]) & ((p < edges[i + 1]) if i < bins - 1 else (p <= edges[i + 1])))]
        if mask.any()
    ))


def metrics(y: np.ndarray, p: np.ndarray) -> Dict[str, float]:
    return {
        "accuracy": float(accuracy_score(y, p >= 0.5)),
        "log_loss": float(log_loss(y, p)),
        "brier": float(brier_score_loss(y, p)),
        "auc": float(roc_auc_score(y, p)),
        "ece": ece(y, p),
    }


def build_rows(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    engine = FeatureEngine()
    rows = []
    for match in matches:
        info = match["info"]
        if info.get("gender") != "male" or info.get("match_type") != "ODI":
            continue
        teams = list(info["teams"])
        winner = info.get("outcome", {}).get("winner")
        if winner in teams:
            a, b = teams
            rows.append({
                "match_id": str(match.get("_match_id", "")),
                "date": str(info["dates"][0]),
                "team_a": a,
                "team_b": b,
                "target": int(winner == a),
                "features": engine.features_for(a, b),
            })
        engine.update(match)
    if len(rows) != 2440:
        raise ValueError(f"expected 2440 decisive rows, got {len(rows)}")
    return rows


def matrix(rows):
    X = np.asarray([[r["features"][n] for n in FEATURE_NAMES] for r in rows], dtype=float)
    y = np.asarray([r["target"] for r in rows], dtype=int)
    return X, y


def calibrated_protocol(X: np.ndarray, y: np.ndarray, train_end: int, val_end: int, test_end: int) -> Dict[str, Any]:
    best_C, scores = select_C_by_validation_log_loss(X[:train_end], y[:train_end], X[train_end:val_end], y[train_end:val_end])
    bundle = fit_o10(X[:train_end], y[:train_end], best_C)
    pv = predict_raw(bundle, X[train_end:val_end])
    pt = predict_raw(bundle, X[val_end:test_end])
    platt = LogisticRegression(max_iter=2000).fit(pv.reshape(-1, 1), y[train_end:val_end])
    iso = IsotonicRegression(out_of_bounds="clip").fit(pv, y[train_end:val_end])
    pp, pi = platt.predict_proba(pv.reshape(-1, 1))[:, 1], iso.predict(pv)
    selected = "isotonic" if log_loss(y[train_end:val_end], pi) < log_loss(y[train_end:val_end], pp) else "platt"
    ptest = iso.predict(pt) if selected == "isotonic" else platt.predict_proba(pt.reshape(-1, 1))[:, 1]
    return {
        "selected_C": best_C,
        "candidate_validation_log_loss": [{"C": c, "log_loss": ll} for ll, c in scores],
        "validation_calibration": {
            "raw_log_loss": float(log_loss(y[train_end:val_end], pv)),
            "platt_log_loss": float(log_loss(y[train_end:val_end], pp)),
            "isotonic_log_loss": float(log_loss(y[train_end:val_end], pi)),
            "selected": selected,
        },
        "test_raw": metrics(y[val_end:test_end], pt),
        "test_selected_calibration": metrics(y[val_end:test_end], ptest),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("corpus", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    matches = load_locked_matches(args.corpus)
    rows = build_rows(matches)
    X, y = matrix(rows)
    if X.shape != (2440, 13):
        raise ValueError(f"expected (2440,13), got {X.shape}")

    result: Dict[str, Any] = {
        "model": "men_odi_o10",
        "control": "men_odi_o0",
        "corpus_sha256": CORPUS_SHA256,
        "population": {"archive_json": 2569, "decisive_rows": 2440},
        "feature_names": list(FEATURE_NAMES),
        "candidate_C": list(CANDIDATE_C),
        "protocol": calibrated_protocol(X, y, TRAIN_END, VALIDATION_END, TEST_END),
        "rolling_origin": [],
        "future_holdout": {},
    }

    for end in ROLLING_TRAIN_ENDS:
        stop = end + ROLLING_WIDTH
        row = {"train_end": end, "eval_end": stop}
        for name, C in (("o0", 1.0), ("o10", None)):
            if C is None:
                C, _ = select_C_by_validation_log_loss(X[:end], y[:end], X[end:stop], y[end:stop])
            bundle = fit_o10(X[:end], y[:end], C)
            p = predict_raw(bundle, X[end:stop])
            row[name] = {"C": C, "raw_log_loss": float(log_loss(y[end:stop], p))}
        result["rolling_origin"].append(row)

    for name, end in (("o0", 1.0), ("o10", None)):
        train_end, val_end, test_end = FUTURE_TRAIN_END, FUTURE_VALIDATION_END, FUTURE_END
        if end is None:
            C, _ = select_C_by_validation_log_loss(X[:train_end], y[:train_end], X[train_end:val_end], y[train_end:val_end])
        else:
            C = end
        bundle = fit_o10(X[:train_end], y[:train_end], C)
        pv = predict_raw(bundle, X[train_end:val_end])
        pf = predict_raw(bundle, X[val_end:test_end])
        iso = IsotonicRegression(out_of_bounds="clip").fit(pv, y[train_end:val_end])
        result["future_holdout"][name] = {"C": C, "raw": metrics(y[val_end:test_end], pf), "isotonic": metrics(y[val_end:test_end], iso.predict(pf))}

    result["source_feature_names_sha256"] = hashlib.sha256(json.dumps(list(FEATURE_NAMES), separators=(",", ":")).encode()).hexdigest()
    result["result_schema"] = "ODI O10 reproduction 1"
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "corpus_sha256": CORPUS_SHA256, "rows": len(rows)}, indent=2))


if __name__ == "__main__":
    main()

"""Reproduce the frozen ODI O12 experiment from the locked corpus.

Usage:
  python -m backend.scripts.run_odi_o12_repro /path/to/odis_male_json.zip

The runner uses the canonical O0 corpus loader/feature engine, adds exactly
one O12 interaction, selects isotonic calibration on validation log loss, and
reports untouched-test, rolling-origin, history-depth, and future-holdout
metrics. It fails closed on a corpus hash or population mismatch.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.preprocessing import StandardScaler

from backend.app.model.training.odi_o0_baseline import chronological_split
from backend.app.model.training.odi_o0_corpus import load_locked_matches
from backend.app.model.training.odi_o0_features import FEATURE_NAMES, FeatureEngine
from backend.app.model.training.odi_o12_features import add_o12_feature

TRAIN_END = 1708
VALIDATION_END = 2074
TEST_END = 2440
FUTURE_TRAIN_END = 1586
FUTURE_VALIDATION_END = 1952
FUTURE_END = 2074
ROLLING_TRAIN_ENDS = [1037, 1244, 1451, 1658, 1865]
ROLLING_WIDTH = 207


def _ece(y: np.ndarray, p: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0.0, 1.0, bins + 1)
    total = 0.0
    for i in range(bins):
        mask = (p >= edges[i]) & ((p < edges[i + 1]) if i < bins - 1 else (p <= edges[i + 1]))
        if mask.any():
            total += float(mask.mean()) * abs(float(y[mask].mean()) - float(p[mask].mean()))
    return total


def _metrics(y: np.ndarray, p: np.ndarray) -> Dict[str, float]:
    return {
        "accuracy": float(accuracy_score(y, p >= 0.5)),
        "log_loss": float(log_loss(y, p)),
        "brier": float(brier_score_loss(y, p)),
        "auc": float(roc_auc_score(y, p)),
        "ece": _ece(y, p),
    }


def build_o12_rows(matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build O0 + O12 rows while preserving the canonical pre-match state order."""
    engine = FeatureEngine()
    rows: List[Dict[str, Any]] = []
    for match in matches:
        info = match["info"]
        if info.get("gender") != "male" or info.get("match_type") != "ODI":
            continue
        teams = list(info["teams"])
        winner = info.get("outcome", {}).get("winner")
        a, b = teams
        sa = engine._state(a)
        sb = engine._state(b)
        if winner in teams:
            o0 = engine.features_for(a, b)
            o12 = add_o12_feature(o0, sa.decisive_matches, sb.decisive_matches)
            rows.append({
                "match_id": str(match.get("_match_id", "")),
                "date": str(info["dates"][0]),
                "team_a": a,
                "team_b": b,
                "target": int(winner == a),
                "min_pre_match_decisive_history": min(sa.decisive_matches, sb.decisive_matches),
                "features": o12,
            })
        engine.update(match)
    if len(rows) != 2440:
        raise ValueError(f"expected 2440 decisive rows, got {len(rows)}")
    return rows


def matrix(rows: List[Dict[str, Any]]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    names = FEATURE_NAMES + ["team_a_minus_team_b_strength_x_history_context"]
    X = np.asarray([[r["features"][n] for n in names] for r in rows], dtype=float)
    y = np.asarray([r["target"] for r in rows], dtype=int)
    h = np.asarray([r["min_pre_match_decisive_history"] for r in rows], dtype=int)
    return X, y, h


def fit(train_X: np.ndarray, train_y: np.ndarray):
    scaler = StandardScaler().fit(train_X)
    model = LogisticRegression(max_iter=2000).fit(scaler.transform(train_X), train_y)
    return scaler, model


def calibrated_test(X: np.ndarray, y: np.ndarray, train_end: int, validation_end: int, test_end: int) -> Dict[str, Any]:
    scaler, model = fit(X[:train_end], y[:train_end])
    pv = model.predict_proba(scaler.transform(X[train_end:validation_end]))[:, 1]
    pt = model.predict_proba(scaler.transform(X[validation_end:test_end]))[:, 1]
    platt = LogisticRegression(max_iter=2000).fit(pv.reshape(-1, 1), y[train_end:validation_end])
    pp = platt.predict_proba(pv.reshape(-1, 1))[:, 1]
    iso = IsotonicRegression(out_of_bounds="clip").fit(pv, y[train_end:validation_end])
    pi = iso.predict(pv)
    selected = "isotonic" if log_loss(y[train_end:validation_end], pi) < log_loss(y[train_end:validation_end], pp) else "platt"
    ptest = iso.predict(pt) if selected == "isotonic" else platt.predict_proba(pt.reshape(-1, 1))[:, 1]
    return {
        "validation_selection": {
            "raw_log_loss": float(log_loss(y[train_end:validation_end], pv)),
            "platt_log_loss": float(log_loss(y[train_end:validation_end], pp)),
            "isotonic_log_loss": float(log_loss(y[train_end:validation_end], pi)),
            "selected": selected,
        },
        "untouched_test_raw": _metrics(y[validation_end:test_end], pt),
        "untouched_test_selected_calibration": _metrics(y[validation_end:test_end], ptest),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("corpus", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    matches = load_locked_matches(args.corpus)
    rows = build_o12_rows(matches)
    X, y, history = matrix(rows)
    if X.shape != (2440, 14):
        raise ValueError(f"expected (2440, 14), got {X.shape}")

    result = {
        "model": "men_odi_o12",
        "control": "men_odi_o0",
        "corpus_sha256": "f0798ef14e1f3f61720d41978289fe7318257263f59edba5dca0b35dbba64d6c",
        "population": {"archive_json": 2569, "decisive_rows": 2440},
        "feature_count": 14,
        "o12_feature": "team_a_minus_team_b_strength_x_history_context",
        "fingerprint": "ODI canonical feature fingerprint; same bytes as reconstructed legacy O0 fingerprint for the O0 row subset",
        "baseline_protocol": calibrated_test(X[:, :13], y, TRAIN_END, VALIDATION_END, TEST_END),
        "o12_protocol": calibrated_test(X, y, TRAIN_END, VALIDATION_END, TEST_END),
    }

    rolling = []
    for train_end in ROLLING_TRAIN_ENDS:
        eval_end = train_end + ROLLING_WIDTH
        row = {"train_end": train_end, "eval_end": eval_end}
        for name, XX in (("o0", X[:, :13]), ("o12", X)):
            scaler, model = fit(XX[:train_end], y[:train_end])
            p = model.predict_proba(scaler.transform(XX[train_end:eval_end]))[:, 1]
            row[name] = {"raw_log_loss": float(log_loss(y[train_end:eval_end], p))}
        rolling.append(row)
    result["rolling_origin"] = rolling

    depth = {}
    for name, XX in (("o0", X[:, :13]), ("o12", X)):
        selected = calibrated_test(XX, y, TRAIN_END, VALIDATION_END, TEST_END)
        scaler, model = fit(XX[:TRAIN_END], y[:TRAIN_END])
        pv = model.predict_proba(scaler.transform(XX[TRAIN_END:VALIDATION_END]))[:, 1]
        pt = model.predict_proba(scaler.transform(XX[VALIDATION_END:TEST_END]))[:, 1]
        iso = IsotonicRegression(out_of_bounds="clip").fit(pv, y[TRAIN_END:VALIDATION_END])
        p = iso.predict(pt)
        depth[name] = {}
        for label, lo, hi in (("20-49", 20, 49), ("50+", 50, 10**9)):
            mask = (history[VALIDATION_END:TEST_END] >= lo) & (history[VALIDATION_END:TEST_END] <= hi)
            depth[name][label] = {"n": int(mask.sum()), "log_loss": float(log_loss(y[VALIDATION_END:TEST_END][mask], p[mask]))}
    result["history_depth_test"] = depth

    future = {}
    for name, XX in (("o0", X[:, :13]), ("o12", X)):
        scaler, model = fit(XX[:FUTURE_TRAIN_END], y[:FUTURE_TRAIN_END])
        pv = model.predict_proba(scaler.transform(XX[FUTURE_TRAIN_END:FUTURE_VALIDATION_END]))[:, 1]
        pf = model.predict_proba(scaler.transform(XX[FUTURE_VALIDATION_END:FUTURE_END]))[:, 1]
        iso = IsotonicRegression(out_of_bounds="clip").fit(pv, y[FUTURE_TRAIN_END:FUTURE_VALIDATION_END])
        future[name] = {
            "raw": _metrics(y[FUTURE_VALIDATION_END:FUTURE_END], pf),
            "isotonic": _metrics(y[FUTURE_VALIDATION_END:FUTURE_END], iso.predict(pf)),
        }
    result["future_holdout"] = future

    if args.output:
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    else:
        print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

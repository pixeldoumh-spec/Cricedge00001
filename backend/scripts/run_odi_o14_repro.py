"""Reproduce ODI O14 from the locked corpus.

This is a provenance runner, not a tuning script. It uses the verified O0
corpus/feature pipeline and the frozen O14 implementation. No test or future
holdout values are used for fitting, calibration selection, or hypothesis
selection.

Usage:
  python -m backend.scripts.run_odi_o14_repro /path/to/odis_male_json.zip

Optional:
  --output docs/model/artifacts/ODI_O14_REPRODUCED_RESULT.json
  --provenance docs/model/artifacts/ODI_O14_PROVENANCE_MANIFEST.json
  --legacy-artifact docs/model/ODI_O14_EVALUATION_REPORT.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, roc_auc_score

from backend.app.model.training.odi_feature_fingerprint import fingerprint_odi_canonical
from backend.app.model.training.odi_o0_corpus import load_locked_matches
from backend.app.model.training.odi_o0_features import FEATURE_NAMES, FeatureEngine
from backend.app.model.training.odi_o14_model import augment_o14, predict_proba, train_o14

CORPUS_SHA256 = "f0798ef14e1f3f61720d41978289fe7318257263f59edba5dca0b35dbba64d6c"
N_ROWS = 2440
TRAIN_END = 1708
VALIDATION_END = 2074
TEST_END = 2440
ROLLING_TRAIN_ENDS = [1037, 1244, 1451, 1658, 1865]
ROLLING_WIDTH = 207
FUTURE_TRAIN_END = 1586
FUTURE_VALIDATION_END = 1952
FUTURE_END = 2074


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_json_sha256(value: Any) -> str:
    payload = json.dumps(value, separators=(",", ":"), sort_keys=True, allow_nan=False)
    return sha256_bytes(payload.encode("utf-8"))


def git_revision() -> str:
    env_sha = os.environ.get("GITHUB_SHA")
    if env_sha:
        return env_sha
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "unknown"


def _ece(y: np.ndarray, p: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0.0, 1.0, bins + 1)
    total = 0.0
    for i in range(bins):
        mask = (p >= edges[i]) & ((p < edges[i + 1]) if i < bins - 1 else (p <= edges[i + 1]))
        if mask.any():
            total += float(mask.mean()) * abs(float(y[mask].mean()) - float(p[mask].mean()))
    return total


def metrics(y: np.ndarray, p: np.ndarray) -> Dict[str, float]:
    return {
        "log_loss": float(log_loss(y, p)),
        "brier": float(brier_score_loss(y, p)),
        "auc": float(roc_auc_score(y, p)),
        "ece": _ece(y, p),
        "accuracy": float(accuracy_score(y, p >= 0.5)),
    }


def build_o14_rows(matches: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """Build canonical O0 rows plus O14's three semantic signed differences."""
    engine = FeatureEngine()
    rows: List[Dict[str, Any]] = []
    for match in matches:
        info = match["info"]
        if info.get("gender") != "male" or info.get("match_type") != "ODI":
            continue
        teams = list(info["teams"])
        winner = info.get("outcome", {}).get("winner")
        if winner not in teams:
            engine.update(match)
            continue
        a, b = teams
        o0 = engine.features_for(a, b)
        rows.append(
            {
                "match_id": str(match.get("_match_id", "")),
                "date": str(info["dates"][0]),
                "team_a": a,
                "team_b": b,
                "target": int(winner == a),
                "features": o0,
            }
        )
        engine.update(match)
    if len(rows) != N_ROWS:
        raise ValueError(f"expected {N_ROWS} decisive rows, got {len(rows)}")
    return rows


def matrix(rows: Sequence[Mapping[str, Any]]) -> tuple[np.ndarray, np.ndarray]:
    X = np.asarray([[r["features"][n] for n in FEATURE_NAMES] for r in rows], dtype=float)
    y = np.asarray([r["target"] for r in rows], dtype=int)
    if X.shape != (N_ROWS, len(FEATURE_NAMES)):
        raise ValueError(f"expected {(N_ROWS, len(FEATURE_NAMES))}, got {X.shape}")
    return X, y


def fit_o0(X_train: np.ndarray, y_train: np.ndarray):
    from sklearn.preprocessing import StandardScaler
    scaler = StandardScaler().fit(X_train)
    model = LogisticRegression(max_iter=2000).fit(scaler.transform(X_train), y_train)
    return scaler, model


def o0_predict(scaler, model, X: np.ndarray) -> np.ndarray:
    return model.predict_proba(scaler.transform(X))[:, 1]


def calibration(p_val: np.ndarray, y_val: np.ndarray):
    platt = LogisticRegression(max_iter=2000).fit(p_val.reshape(-1, 1), y_val)
    iso = IsotonicRegression(out_of_bounds="clip").fit(p_val, y_val)
    p_platt = platt.predict_proba(p_val.reshape(-1, 1))[:, 1]
    p_iso = iso.predict(p_val)
    candidates = {
        "platt": (log_loss(y_val, p_platt), lambda p: platt.predict_proba(p.reshape(-1, 1))[:, 1]),
        "isotonic": (log_loss(y_val, p_iso), lambda p: iso.predict(p)),
    }
    selected = min(candidates, key=lambda k: candidates[k][0])
    return {
        "selected": selected,
        "validation": {
            "raw": metrics(y_val, p_val),
            "platt": metrics(y_val, p_platt),
            "isotonic": metrics(y_val, p_iso),
        },
        "transform": candidates[selected][1],
    }


def evaluate_main_split(X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
    o14, _ = train_o14(X[:TRAIN_END], y[:TRAIN_END], first_train_index=0, last_train_index=TRAIN_END - 1)
    p_train = predict_proba(o14, X[:TRAIN_END], np.arange(TRAIN_END))
    p_val = predict_proba(o14, X[TRAIN_END:VALIDATION_END], np.arange(TRAIN_END, VALIDATION_END))
    p_test = predict_proba(o14, X[VALIDATION_END:TEST_END], np.arange(VALIDATION_END, TEST_END))
    cal = calibration(p_val, y[TRAIN_END:VALIDATION_END])
    selected_transform = cal["transform"]
    p_val_selected = selected_transform(p_val)
    p_test_selected = selected_transform(p_test)
    return {
        "train": {"indices": [0, TRAIN_END], "raw_predictions": p_train.tolist(), "metrics": metrics(y[:TRAIN_END], p_train)},
        "validation": {
            "indices": [TRAIN_END, VALIDATION_END],
            "raw_predictions": p_val.tolist(),
            "selected_calibration_predictions": p_val_selected.tolist(),
            "metrics": metrics(y[TRAIN_END:VALIDATION_END], p_val),
            "selected_calibration_metrics": metrics(y[TRAIN_END:VALIDATION_END], p_val_selected),
            "calibration": {k: v for k, v in cal.items() if k != "transform"},
        },
        "test": {
            "indices": [VALIDATION_END, TEST_END],
            "raw_predictions": p_test.tolist(),
            "selected_calibration_predictions": p_test_selected.tolist(),
            "raw_metrics": metrics(y[VALIDATION_END:TEST_END], p_test),
            "selected_calibration_metrics": metrics(y[VALIDATION_END:TEST_END], p_test_selected),
        },
    }


def rolling_origin(X: np.ndarray, y: np.ndarray) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for train_end in ROLLING_TRAIN_ENDS:
        eval_end = train_end + ROLLING_WIDTH
        model, _ = train_o14(X[:train_end], y[:train_end], first_train_index=0, last_train_index=train_end - 1)
        p14 = predict_proba(model, X[train_end:eval_end], np.arange(train_end, eval_end))
        s0, m0 = fit_o0(X[:train_end], y[:train_end])
        p0 = o0_predict(s0, m0, X[train_end:eval_end])
        out.append({
            "train_end": train_end,
            "eval_end": eval_end,
            "o0_raw": metrics(y[train_end:eval_end], p0),
            "o14_raw": metrics(y[train_end:eval_end], p14),
            "delta_log_loss_o14_minus_o0": float(log_loss(y[train_end:eval_end], p14) - log_loss(y[train_end:eval_end], p0)),
        })
    return out


def future_holdout(X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for name in ("o0", "o14"):
        if name == "o0":
            scaler, model = fit_o0(X[:FUTURE_TRAIN_END], y[:FUTURE_TRAIN_END])
            p_val = o0_predict(scaler, model, X[FUTURE_TRAIN_END:FUTURE_VALIDATION_END])
            p_future = o0_predict(scaler, model, X[FUTURE_VALIDATION_END:FUTURE_END])
        else:
            bundle, _ = train_o14(X[:FUTURE_TRAIN_END], y[:FUTURE_TRAIN_END], first_train_index=0, last_train_index=FUTURE_TRAIN_END - 1)
            p_val = predict_proba(bundle, X[FUTURE_TRAIN_END:FUTURE_VALIDATION_END], np.arange(FUTURE_TRAIN_END, FUTURE_VALIDATION_END))
            p_future = predict_proba(bundle, X[FUTURE_VALIDATION_END:FUTURE_END], np.arange(FUTURE_VALIDATION_END, FUTURE_END))
        cal = calibration(p_val, y[FUTURE_TRAIN_END:FUTURE_VALIDATION_END])
        out[name] = {
            "validation_calibration": {k: v for k, v in cal.items() if k != "transform"},
            "future_raw": metrics(y[FUTURE_VALIDATION_END:FUTURE_END], p_future),
            "future_selected_calibration": metrics(y[FUTURE_VALIDATION_END:FUTURE_END], cal["transform"](p_future)),
        }
    return out


def compare_legacy(result: Mapping[str, Any], artifact: Path | None) -> Dict[str, Any]:
    if artifact is None or not artifact.exists():
        return {"status": "legacy_artifact_not_found", "path": str(artifact) if artifact else None}
    legacy = json.loads(artifact.read_text(encoding="utf-8"))
    comparisons: Dict[str, Any] = {"status": "loaded", "path": str(artifact), "checks": {}}
    # Compare common scalar paths when present without assuming an undocumented schema.
    pairs = [
        ("test.raw_metrics.log_loss", ["o14_protocol", "untouched_test_raw", "log_loss"]),
        ("test.selected_calibration_metrics.log_loss", ["o14_protocol", "untouched_test_selected_calibration", "log_loss"]),
    ]
    for label, path in pairs:
        cur: Any = result
        old: Any = legacy
        try:
            for key in path:
                cur = cur[key]
            # Best-effort lookup of the same terminal metric in legacy artifact.
            old_value = None
            if isinstance(legacy, dict):
                for container_key in ("o14_protocol", "untouched_test_raw", "untouched_test_selected_calibration", "test", "metrics"):
                    obj = legacy.get(container_key)
                    if isinstance(obj, dict) and "log_loss" in obj:
                        old_value = obj["log_loss"]
                        break
            comparisons["checks"][label] = {"current": cur, "legacy": old_value, "match": old_value is not None and abs(float(cur) - float(old_value)) <= 1e-10}
        except Exception:
            comparisons["checks"][label] = {"status": "schema_not_comparable"}
    return comparisons


def source_hashes(repo_root: Path) -> Dict[str, str]:
    paths = [
        "backend/app/model/training/odi_o0_features.py",
        "backend/app/model/training/odi_o0_corpus.py",
        "backend/app/model/training/odi_o14_model.py",
        "backend/app/model/training/odi_feature_fingerprint.py",
        "backend/scripts/run_odi_o14_repro.py",
        "docs/model/ODI_O14_HYPOTHESIS_CONTRACT.md",
    ]
    out = {}
    for rel in paths:
        p = repo_root / rel
        if p.exists():
            out[rel] = sha256_file(p)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("corpus", type=Path)
    ap.add_argument("--output", type=Path, default=Path("docs/model/artifacts/ODI_O14_REPRODUCED_RESULT.json"))
    ap.add_argument("--provenance", type=Path, default=Path("docs/model/artifacts/ODI_O14_PROVENANCE_MANIFEST.json"))
    ap.add_argument("--legacy-artifact", type=Path, default=Path("docs/model/ODI_O14_EVALUATION_REPORT.json"))
    args = ap.parse_args()

    if sha256_file(args.corpus) != CORPUS_SHA256:
        raise SystemExit("FAIL CLOSED: locked corpus SHA-256 mismatch")
    matches = load_locked_matches(args.corpus)
    rows = build_o14_rows(matches)
    X, y = matrix(rows)
    fingerprint = fingerprint_odi_canonical(rows)

    result: Dict[str, Any] = {
        "schema": "ODI-O14-reproduction-1",
        "model": "men_odi_o14",
        "control": "men_odi_o0",
        "corpus": {"sha256": CORPUS_SHA256, "archive_json": 2569, "decisive_rows": N_ROWS},
        "feature_row_fingerprint": fingerprint,
        "feature_row_fingerprint_contract": "ODI canonical feature fingerprint",
        "main_split": evaluate_main_split(X, y),
        "rolling_origin": rolling_origin(X, y),
        "future_holdout": future_holdout(X, y),
    }
    result["legacy_comparison"] = compare_legacy(result, args.legacy_artifact)
    result["result_sha256"] = canonical_json_sha256(result)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    repo_root = Path(__file__).resolve().parents[2]
    manifest = {
        "schema": "ODI-provenance-manifest-1",
        "experiment": "O14",
        "corpus_sha256": CORPUS_SHA256,
        "archive_population": {"json_matches": 2569, "decisive_rows": N_ROWS},
        "feature_row_fingerprint": fingerprint,
        "runner": {"path": "backend/scripts/run_odi_o14_repro.py", "sha256": sha256_file(Path(__file__))},
        "source_hashes": source_hashes(repo_root),
        "git_revision": git_revision(),
        "result_artifact": {"path": str(args.output), "sha256": sha256_file(args.output)},
        "legacy_artifact": {"path": str(args.legacy_artifact), "sha256": sha256_file(args.legacy_artifact) if args.legacy_artifact.exists() else None},
        "status": "reproduced_pending_legacy_reconciliation" if not args.legacy_artifact.exists() else "reproduced_with_legacy_comparison",
    }
    args.provenance.parent.mkdir(parents=True, exist_ok=True)
    args.provenance.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"result": str(args.output), "provenance": str(args.provenance), "fingerprint": fingerprint, "legacy_status": result["legacy_comparison"]["status"]}, indent=2))


if __name__ == "__main__":
    main()

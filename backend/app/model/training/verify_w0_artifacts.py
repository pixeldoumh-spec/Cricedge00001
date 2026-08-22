"""Verify the raw-probability W0 production artifact."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import joblib

from app.model.training.model_v0 import FEATURES

EXPECTED_MATCHES = 2066
EXPECTED_SPLIT = {"train": 1446, "validation": 310, "test": 310}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify(output_dir: Path) -> None:
    model_path = output_dir / "model.joblib"
    metadata_path = output_dir / "metadata.json"
    sums_path = output_dir / "SHA256SUMS.json"
    missing = [str(p) for p in (model_path, metadata_path, sums_path) if not p.exists()]
    if missing:
        raise SystemExit(f"FAIL: missing W0 artifact files: {', '.join(missing)}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    sums = json.loads(sums_path.read_text(encoding="utf-8"))
    if metadata.get("model_version") != "W0":
        raise SystemExit("FAIL: model version mismatch")
    dataset = metadata.get("dataset", {})
    if dataset.get("matches") != EXPECTED_MATCHES or dataset.get("split") != EXPECTED_SPLIT:
        raise SystemExit("FAIL: dataset contract mismatch")
    if tuple(metadata.get("features", ())) != tuple(FEATURES):
        raise SystemExit("FAIL: 13-feature contract mismatch")
    if metadata.get("production_calibration") != "raw_logistic_probabilities":
        raise SystemExit("FAIL: W0 production calibration strategy mismatch")
    if sha256(model_path) != sums.get("files", {}).get("model.joblib") or sha256(metadata_path) != sums.get("files", {}).get("metadata.json"):
        raise SystemExit("FAIL: SHA-256 mismatch")
    model = joblib.load(model_path)
    estimator = getattr(model, "named_steps", {}).get("logistic", model)
    if not hasattr(model, "predict_proba") or getattr(estimator, "max_iter", None) != 2000:
        raise SystemExit("FAIL: serialized estimator mismatch")
    print("PASS: W0 artifacts verified")
    print(f"model.joblib sha256: {sha256(model_path)}")
    print("matches: 2066")
    print("split: 1446/310/310")
    print("features: 13")
    print("production probabilities: raw LogisticRegression")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Verify W0 production artifacts")
    p.add_argument("--output-dir", required=True, type=Path)
    args = p.parse_args()
    verify(args.output_dir)

"""Verify generated Model v0 artifacts before they are used by inference."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import joblib

from app.model.training.model_v0 import FEATURES, MODEL_VERSION, LogisticRegression

EXPECTED_MATCHES = 3411
EXPECTED_SPLIT = {"train": 2387, "validation": 511, "test": 513}
EXPECTED_FEATURES = (
    "team_elo", "opponent_elo", "elo_difference", "team_form_3", "team_form_5", "team_form_10",
    "venue_team_win_rate", "venue_bat_first_win_rate", "head_to_head_win_rate",
    "batting_run_rate", "bowling_run_rate", "batting_wicket_rate", "bowling_wicket_rate",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(output_dir: Path) -> None:
    model_path = output_dir / "model.joblib"
    calibrator_path = output_dir / "calibrator.joblib"
    checksums_path = output_dir / "SHA256SUMS.json"
    metadata_path = output_dir / "metadata.json"
    required = (model_path, calibrator_path, checksums_path, metadata_path)
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise SystemExit(f"FAIL: missing artifact files: {', '.join(missing)}")

    manifest = json.loads(checksums_path.read_text(encoding="utf-8"))
    expected_files = manifest.get("files", {})
    actual_model_sha = sha256(model_path)
    actual_calibrator_sha = sha256(calibrator_path)
    if actual_model_sha != expected_files.get("model.joblib"):
        raise SystemExit("FAIL: model.joblib SHA-256 mismatch")
    if actual_calibrator_sha != expected_files.get("calibrator.joblib"):
        raise SystemExit("FAIL: calibrator.joblib SHA-256 mismatch")

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("model_version") != MODEL_VERSION:
        raise SystemExit("FAIL: model version mismatch")
    dataset = metadata.get("dataset", {})
    if dataset.get("matches") != EXPECTED_MATCHES:
        raise SystemExit("FAIL: match count mismatch")
    if dataset.get("split") != EXPECTED_SPLIT:
        raise SystemExit("FAIL: chronological split mismatch")
    if tuple(metadata.get("features", ())) != EXPECTED_FEATURES or tuple(FEATURES) != EXPECTED_FEATURES:
        raise SystemExit("FAIL: 13-feature contract mismatch")

    model = joblib.load(model_path)
    calibrator = joblib.load(calibrator_path)
    if not hasattr(model, "predict_proba") or not hasattr(calibrator, "predict_proba"):
        raise SystemExit("FAIL: serialized artifact missing predict_proba")
    estimator = getattr(model, "named_steps", {}).get("logistic", model)
    if not isinstance(estimator, LogisticRegression):
        raise SystemExit("FAIL: serialized estimator is not LogisticRegression")
    if estimator.max_iter != 2000:
        raise SystemExit("FAIL: LogisticRegression max_iter mismatch")

    print("PASS: Model v0 artifacts verified")
    print(f"model.joblib sha256:      {actual_model_sha}")
    print(f"calibrator.joblib sha256: {actual_calibrator_sha}")
    print(f"matches:                  {EXPECTED_MATCHES}")
    print(f"split:                    {EXPECTED_SPLIT}")
    print(f"features:                 {len(EXPECTED_FEATURES)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify generated Model v0 artifacts")
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    verify(args.output_dir)


if __name__ == "__main__":
    main()

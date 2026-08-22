"""Verify the frozen men's v0 and women's W0 production artifacts.

The model binaries intentionally stay outside GitHub. This command is the final
runtime gate: it verifies the binary checksums, metadata contracts, estimator
configuration, calibration policy, and optionally the retained corpus checksum.

Usage:
    python -m app.model.training.verify_production_artifacts \
        --v0-dir backend/models/v0 \
        --w0-dir backend/models/W0 \
        --archive /path/to/t20s_json.zip
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import joblib

EXPECTED_FEATURES = (
    "team_elo",
    "opponent_elo",
    "elo_difference",
    "team_form_3",
    "team_form_5",
    "team_form_10",
    "venue_team_win_rate",
    "venue_bat_first_win_rate",
    "head_to_head_win_rate",
    "batting_run_rate",
    "bowling_run_rate",
    "batting_wicket_rate",
    "bowling_wicket_rate",
)
EXPECTED_V0 = {
    "matches": 3411,
    "split": {"train": 2387, "validation": 511, "test": 513},
}
EXPECTED_W0 = {
    "matches": 2066,
    "split": {"train": 1446, "validation": 310, "test": 310},
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _check_pipeline(model, version: str) -> None:
    if not hasattr(model, "predict_proba"):
        raise RuntimeError(f"{version}: serialized model has no predict_proba")
    named_steps = getattr(model, "named_steps", {})
    estimator = named_steps.get("logistic", model)
    if estimator.__class__.__name__ != "LogisticRegression":
        raise RuntimeError(f"{version}: serialized estimator is not LogisticRegression")
    if getattr(estimator, "max_iter", None) != 2000:
        raise RuntimeError(f"{version}: LogisticRegression max_iter must be 2000")
    if "scale" not in named_steps:
        raise RuntimeError(f"{version}: StandardScaler step missing")


def _verify_version(output_dir: Path, version: str, expected: dict) -> dict:
    model_path = output_dir / "model.joblib"
    metadata_path = output_dir / "metadata.json"
    sums_path = output_dir / "SHA256SUMS.json"
    required = (model_path, metadata_path, sums_path)
    missing = [str(path) for path in required if not path.is_file()]
    if version == "v0":
        calibrator_path = output_dir / "calibrator.joblib"
        if not calibrator_path.is_file():
            missing.append(str(calibrator_path))
    if missing:
        raise RuntimeError(f"{version}: missing artifact files: {', '.join(missing)}")

    metadata = _load_json(metadata_path)
    sums = _load_json(sums_path)
    if metadata.get("model_version") != version or sums.get("model_version") != version:
        raise RuntimeError(f"{version}: model version mismatch")
    dataset = metadata.get("dataset", {})
    if dataset.get("matches") != expected["matches"]:
        raise RuntimeError(f"{version}: match count mismatch")
    if dataset.get("split") != expected["split"]:
        raise RuntimeError(f"{version}: chronological split mismatch")
    if metadata.get("features") and tuple(metadata["features"]) != EXPECTED_FEATURES:
        raise RuntimeError(f"{version}: 13-feature contract mismatch")
    if metadata.get("ordering") not in (None, "chronological") and dataset.get("ordering") != "chronological":
        raise RuntimeError(f"{version}: ordering contract mismatch")

    actual_model = sha256(model_path)
    if actual_model != sums.get("files", {}).get("model.joblib"):
        raise RuntimeError(f"{version}: model.joblib SHA-256 mismatch")
    actual_metadata = sha256(metadata_path)
    if actual_metadata != sums.get("files", {}).get("metadata.json"):
        raise RuntimeError(f"{version}: metadata.json SHA-256 mismatch")

    model = joblib.load(model_path)
    _check_pipeline(model, version)

    result = {
        "model_version": version,
        "status": "PASS",
        "model_sha256": actual_model,
        "metadata_sha256": actual_metadata,
        "matches": expected["matches"],
        "split": expected["split"],
        "feature_count": len(EXPECTED_FEATURES),
    }

    if version == "v0":
        calibrator_path = output_dir / "calibrator.joblib"
        actual_calibrator = sha256(calibrator_path)
        if actual_calibrator != sums.get("files", {}).get("calibrator.joblib"):
            raise RuntimeError("v0: calibrator.joblib SHA-256 mismatch")
        calibrator = joblib.load(calibrator_path)
        if not hasattr(calibrator, "predict_proba"):
            raise RuntimeError("v0: calibrator has no predict_proba")
        calibration = metadata.get("calibration", {})
        if calibration.get("fit_scope") != "validation_only" or calibration.get("test_used_for_calibration") is not False:
            raise RuntimeError("v0: calibration policy mismatch")
        result["calibrator_sha256"] = actual_calibrator
        result["calibration"] = "validation_only_platt"
    else:
        calibration = metadata.get("calibration", {})
        production = metadata.get("production_calibration") or calibration.get("production")
        if production not in ("raw", "raw_logistic_probabilities"):
            raise RuntimeError("W0: production calibration policy mismatch")
        if (output_dir / "calibrator.joblib").exists():
            raise RuntimeError("W0: calibrator.joblib must not be present for production")
        result["calibration"] = "raw_logistic_probabilities"

    return result


def verify(v0_dir: Path, w0_dir: Path, archive: Path | None = None) -> dict:
    report = {
        "verification_version": 1,
        "status": "PASS",
        "models": {
            "v0": _verify_version(v0_dir, "v0", EXPECTED_V0),
            "W0": _verify_version(w0_dir, "W0", EXPECTED_W0),
        },
    }
    if archive is not None:
        if not archive.is_file():
            raise RuntimeError(f"archive not found: {archive}")
        report["source_archive_sha256"] = sha256(archive)
        expected_archive = report["models"]["v0"].get("source_archive_sha256")
        if expected_archive is None:
            # Require the corpus checksum to be present in both artifact manifests.
            v0_sums = _load_json(v0_dir / "SHA256SUMS.json")
            w0_sums = _load_json(w0_dir / "SHA256SUMS.json")
            v0_archive = v0_sums.get("source_archive_sha256")
            w0_archive = w0_sums.get("source_archive_sha256")
            if v0_archive != report["source_archive_sha256"] or w0_archive != report["source_archive_sha256"]:
                raise RuntimeError("source archive SHA-256 does not match both artifact manifests")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify production v0 and W0 artifacts")
    parser.add_argument("--v0-dir", type=Path, required=True)
    parser.add_argument("--w0-dir", type=Path, required=True)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = verify(args.v0_dir, args.w0_dir, args.archive)
    text = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

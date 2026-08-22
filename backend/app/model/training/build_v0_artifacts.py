"""Reproducibly build the verified Model v0 artifacts from a Cricsheet ZIP."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Sequence

import joblib
import numpy as np

from app.model.data.dataset import is_trainable_t20
from app.model.data.normalizer import CanonicalMatch, normalize_match
from app.model.data.parser import iter_matches
from app.model.training.calibration import ValidationPlattCalibrator
from app.model.training.model_v0 import FEATURES, build_v0_feature_rows, train_model_v0
from app.model.training.splits import chronological_split

EXPECTED_TOTAL = 3411
EXPECTED_TRAIN = 2387
EXPECTED_VALIDATION = 511
EXPECTED_TEST = 513


def load_t20_matches(archive: Path) -> list[CanonicalMatch]:
    """Normalize and filter the archive to the canonical men's T20 population."""
    matches: list[CanonicalMatch] = []
    for index, raw in enumerate(iter_matches(archive)):
        raw_meta = raw.get("meta") or {}
        raw_id = raw_meta.get("match_id") or raw_meta.get("data_version") or "match"
        # The embedded metadata value is not unique across Cricsheet files.
        # Append the deterministic archive ordinal so every match remains distinct.
        match_id = f"{raw_id}-{index:06d}"
        match = normalize_match(match_id, raw)
        if is_trainable_t20(match):
            matches.append(match)
    return sorted(matches, key=lambda m: m.dates[0] if m.dates else "")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_v0_artifacts(archive: Path, output_dir: Path) -> dict[str, object]:
    """Train and serialize the verified v0 estimator and validation calibrator."""
    matches = load_t20_matches(archive)
    if len(matches) != EXPECTED_TOTAL:
        raise ValueError(
            f"expected exactly {EXPECTED_TOTAL} trainable men's T20 matches, got {len(matches)}"
        )

    model, result = train_model_v0(matches)
    train_matches, validation_matches, test_matches = chronological_split(matches)
    expected = (EXPECTED_TRAIN, EXPECTED_VALIDATION, EXPECTED_TEST)
    actual = tuple(map(len, (train_matches, validation_matches, test_matches)))
    if actual != expected:
        raise ValueError(f"expected split {expected}, got {actual}")
    if (result.train_size, result.validation_size, result.test_size) != expected:
        raise ValueError(
            "canonical train_model_v0 returned unexpected split sizes: "
            f"{result.train_size}/{result.validation_size}/{result.test_size}"
        )

    rows = build_v0_feature_rows(matches)
    by_id = {row["match_id"]: row for row in rows}
    validation_frame = np.asarray(
        [[float(by_id[m.match_id][name]) for name in FEATURES] for m in validation_matches],
        dtype=float,
    )
    validation_targets = np.asarray(
        [int(by_id[m.match_id]["target"]) for m in validation_matches], dtype=int
    )
    validation_probabilities = model.predict_proba(validation_frame)[:, 1]
    calibrator = ValidationPlattCalibrator().fit(validation_probabilities, validation_targets)

    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / "model.joblib"
    calibrator_path = output_dir / "calibrator.joblib"
    manifest_path = output_dir / "SHA256SUMS.json"
    metadata_path = output_dir / "metadata.json"

    joblib.dump(model, model_path)
    joblib.dump(calibrator, calibrator_path)

    manifest = {
        "model_version": "v0",
        "source_archive_sha256": _sha256(archive),
        "match_count": len(matches),
        "split": {"train": EXPECTED_TRAIN, "validation": EXPECTED_VALIDATION, "test": EXPECTED_TEST},
        "features": list(FEATURES),
        "estimator": "StandardScaler + LogisticRegression(max_iter=2000)",
        "calibration": "ValidationPlattCalibrator (logit-space LogisticRegression, validation-only)",
        "files": {"model.joblib": _sha256(model_path), "calibrator.joblib": _sha256(calibrator_path)},
        "reproduction_metrics": result.metrics,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    metadata = {
        "model_version": "v0",
        "status": "frozen_reference",
        "artifact_status": "buildable",
        "feature_count": len(FEATURES),
        "features": list(FEATURES),
        "estimator": {"pipeline": ["StandardScaler", "LogisticRegression"], "logistic_regression_max_iter": 2000},
        "calibration": {"method": "Platt scaling", "fit_scope": "validation_only", "test_used_for_calibration": False},
        "dataset": {"matches": EXPECTED_TOTAL, "split": {"train": EXPECTED_TRAIN, "validation": EXPECTED_VALIDATION, "test": EXPECTED_TEST}, "ordering": "chronological", "domain": "men's T20"},
        "source_archive_sha256": _sha256(archive),
        "artifact_files": ["model.joblib", "calibrator.joblib", "metadata.json"],
        "reproduction_metrics": result.metrics,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    manifest["files"]["metadata.json"] = _sha256(metadata_path)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build verified Model v0 artifacts")
    parser.add_argument("--archive", type=Path, required=True, help="Cricsheet T20 ZIP archive")
    parser.add_argument("--output-dir", type=Path, default=Path("backend/models/v0"))
    args = parser.parse_args(argv)
    print(json.dumps(build_v0_artifacts(args.archive, args.output_dir), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

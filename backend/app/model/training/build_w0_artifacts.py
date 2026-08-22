"""Build the frozen women's W0 production artifact from the retained corpus."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Sequence

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.model.data.normalizer import CanonicalMatch, normalize_match
from app.model.data.parser import iter_matches
from app.model.training.model_v0 import FEATURES, build_v0_feature_rows

EXPECTED_TOTAL = 2066
EXPECTED_SPLIT = (1446, 310, 310)
MODEL_VERSION = "W0"


def load_w0_matches(archive: Path) -> list[CanonicalMatch]:
    matches: list[CanonicalMatch] = []
    for index, raw in enumerate(iter_matches(archive)):
        info = raw.get("info") or {}
        outcome = info.get("outcome") or {}
        teams = info.get("teams") or []
        if str(info.get("gender", "")).lower() != "female" or info.get("match_type") != "T20":
            continue
        if len(teams) != 2 or outcome.get("winner") not in teams:
            continue
        meta = raw.get("meta") or {}
        raw_id = meta.get("match_id") or meta.get("data_version") or "match"
        matches.append(normalize_match(f"{raw_id}-{index:06d}", raw))
    return sorted(matches, key=lambda m: m.dates[0] if m.dates else "")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_w0_artifacts(archive: Path, output_dir: Path) -> dict:
    matches = load_w0_matches(archive)
    if len(matches) != EXPECTED_TOTAL:
        raise ValueError(f"expected {EXPECTED_TOTAL} decisive women's T20 matches, got {len(matches)}")
    rows = sorted(build_v0_feature_rows(matches), key=lambda r: r.get("date", ""))
    if len(rows) != EXPECTED_TOTAL:
        raise ValueError(f"expected {EXPECTED_TOTAL} feature rows, got {len(rows)}")
    train = pd.DataFrame(rows[:1446])
    validation = pd.DataFrame(rows[1446:1756])
    test = pd.DataFrame(rows[1756:])
    if (len(train), len(validation), len(test)) != EXPECTED_SPLIT:
        raise ValueError("W0 split contract mismatch")

    model = Pipeline([
        ("scale", StandardScaler()),
        ("logistic", LogisticRegression(max_iter=2000)),
    ])
    model.fit(train[FEATURES], train["target"])

    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / "model.joblib"
    metadata_path = output_dir / "metadata.json"
    sums_path = output_dir / "SHA256SUMS.json"
    joblib.dump(model, model_path)

    metadata = {
        "model_version": MODEL_VERSION,
        "status": "frozen_reference",
        "production_calibration": "raw_logistic_probabilities",
        "feature_count": len(FEATURES),
        "features": list(FEATURES),
        "estimator": {"pipeline": ["StandardScaler", "LogisticRegression"], "logistic_regression_max_iter": 2000},
        "dataset": {"matches": EXPECTED_TOTAL, "split": {"train": 1446, "validation": 310, "test": 310}, "ordering": "chronological", "domain": "women's T20"},
        "calibration": {"status": "not_promoted", "production": "raw", "reason": "raw probabilities beat Platt and isotonic on final holdout primary metrics"},
        "source_archive_sha256": sha256(archive),
        "artifact_files": ["model.joblib", "metadata.json"],
    }
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    sums = {"model_version": MODEL_VERSION, "source_archive_sha256": sha256(archive), "files": {"model.joblib": sha256(model_path), "metadata.json": sha256(metadata_path)}}
    sums_path.write_text(json.dumps(sums, indent=2) + "\n", encoding="utf-8")
    return sums


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--archive", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args(argv)
    print(json.dumps(build_w0_artifacts(args.archive, args.output_dir), indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

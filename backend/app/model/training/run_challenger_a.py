"""Run T20 Challenger A against the retained Cricsheet corpus.

Challenger A changes only the ball-rate denominator from all delivery records to
legal deliveries (excluding wides and no-balls). Population, chronological
ordering, feature set, estimator, and validation/test boundaries remain the
same as the selected T20 reference for the supplied gender.

No V0/W0 artifact is modified by this runner.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.model.data.normalizer import CanonicalMatch, normalize_match
from app.model.data.parser import iter_matches
from app.model.training.calibration import ValidationPlattCalibrator
from app.model.training.challenger_a import build_challenger_a_feature_rows, changed_features
from app.model.training.model_v0 import FEATURES, build_v0_feature_rows

EXPECTED = {
    "male": {"total": 3411, "split": (2387, 511, 513)},
    "female": {"total": 2066, "split": (1446, 310, 310)},
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_matches(archive: Path, gender: str) -> list[CanonicalMatch]:
    matches: list[CanonicalMatch] = []
    for index, raw in enumerate(iter_matches(archive)):
        info = raw.get("info") or {}
        outcome = info.get("outcome") or {}
        teams = info.get("teams") or []
        if str(info.get("gender", "")).lower() != gender:
            continue
        if info.get("match_type") != "T20":
            continue
        if len(teams) != 2 or outcome.get("winner") not in teams:
            continue
        meta = raw.get("meta") or {}
        raw_id = meta.get("match_id") or meta.get("data_version") or "match"
        matches.append(normalize_match(f"{raw_id}-{index:06d}", raw))
    return sorted(matches, key=lambda m: m.dates[0] if m.dates else "")


def split(items: list[CanonicalMatch], gender: str):
    train_n, validation_n, test_n = EXPECTED[gender]["split"]
    if len(items) != EXPECTED[gender]["total"]:
        raise ValueError(f"expected {EXPECTED[gender]['total']} decisive {gender} T20 matches, got {len(items)}")
    return items[:train_n], items[train_n:train_n + validation_n], items[train_n + validation_n:train_n + validation_n + test_n]


def metrics(target: np.ndarray, probability: np.ndarray) -> dict[str, float]:
    return {
        "accuracy": float(accuracy_score(target, probability >= 0.5)),
        "log_loss": float(log_loss(target, probability)),
        "brier_score": float(brier_score_loss(target, probability)),
        "auc": float(roc_auc_score(target, probability)),
    }


def frame(rows: dict[str, dict], items: Sequence[CanonicalMatch]) -> pd.DataFrame:
    return pd.DataFrame([rows[m.match_id] for m in items])


def run(archive: Path, output: Path, gender: str) -> dict:
    matches = load_matches(archive, gender)
    train_matches, validation_matches, test_matches = split(matches, gender)

    v0_rows = build_v0_feature_rows(matches)
    challenger_rows = build_challenger_a_feature_rows(matches)
    if len(v0_rows) != len(challenger_rows):
        raise ValueError("V0 and Challenger A row counts differ")
    changed = sorted(changed_features(v0_rows, challenger_rows))
    expected_changed = {"batting_run_rate", "bowling_run_rate", "batting_wicket_rate", "bowling_wicket_rate"}
    if set(changed) - expected_changed:
        raise ValueError(f"Challenger A changed non-rate features: {sorted(set(changed) - expected_changed)}")

    v0_by_id = {r["match_id"]: r for r in v0_rows}
    ch_by_id = {r["match_id"]: r for r in challenger_rows}
    train = frame(ch_by_id, train_matches)
    validation = frame(ch_by_id, validation_matches)
    test = frame(ch_by_id, test_matches)

    model = Pipeline([
        ("scale", StandardScaler()),
        ("logistic", LogisticRegression(max_iter=2000)),
    ])
    model.fit(train[FEATURES], train.target)

    validation_target = validation.target.to_numpy(dtype=int)
    validation_raw = model.predict_proba(validation[FEATURES])[:, 1]
    calibrator = ValidationPlattCalibrator().fit(validation_raw, validation_target)
    test_target = test.target.to_numpy(dtype=int)
    raw_probability = model.predict_proba(test[FEATURES])[:, 1]
    calibrated_probability = calibrator.predict_proba(raw_probability)

    result = {
        "experiment": "T20 Challenger A",
        "status": "challenger_only",
        "gender": gender,
        "hypothesis": "Correct all-delivery rate denominators to legal-delivery denominators, excluding wides and no-balls, without changing the model class or any other feature.",
        "corpus_sha256": sha256(archive),
        "population": len(matches),
        "split": {"train": len(train_matches), "validation": len(validation_matches), "test": len(test_matches)},
        "feature_contract": list(FEATURES),
        "changed_features": changed,
        "estimator": "StandardScaler + LogisticRegression(max_iter=2000)",
        "calibration": "ValidationPlattCalibrator fitted on validation only",
        "test_metrics_raw": metrics(test_target, raw_probability),
        "test_metrics_calibrated": metrics(test_target, calibrated_probability),
        "v0_feature_rows_compared": len(v0_rows),
        "notes": [
            "The existing V0/W0 code and artifacts are not modified by this runner.",
            "Wicket numerators remain unchanged; only legal-ball denominators are changed.",
            "The raw and calibrated results are both reported so the challenger can be judged under the same probability discipline as the current reference.",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run T20 Challenger A")
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--gender", choices=("male", "female"), required=True)
    args = parser.parse_args(argv)
    print(json.dumps(run(args.archive, args.output, args.gender), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

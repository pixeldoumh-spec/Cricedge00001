"""Run T20 Challenger B with a validation-selected Elo K-factor.

The runner deliberately uses the exact frozen V0/W0 population counts and
chronological split boundaries rather than recomputing 70/15 percentages.
This is required because the men's frozen contract is 2387/511/513 while
70/15 percentage flooring would produce 2387/512/512.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, roc_auc_score

from app.model.data.normalizer import CanonicalMatch, normalize_match
from app.model.data.parser import iter_matches
from app.model.training.calibration import ValidationPlattCalibrator
from app.model.training.challenger_b import (
    DEFAULT_K_GRID,
    build_challenger_b_feature_rows,
    fit_logistic,
)
from app.model.training.model_v0 import FEATURES, build_v0_feature_rows

EXPECTED = {
    "male": {"total": 3411, "split": (2387, 511, 513)},
    "female": {"total": 2066, "split": (1446, 310, 310)},
}


def _ece(targets: np.ndarray, probabilities: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0.0, 1.0, bins + 1)
    total = len(targets)
    value = 0.0
    for i in range(bins):
        mask = (probabilities >= edges[i]) & (
            probabilities <= edges[i + 1] if i == bins - 1 else probabilities < edges[i + 1]
        )
        if np.any(mask):
            value += (mask.sum() / total) * abs(targets[mask].mean() - probabilities[mask].mean())
    return float(value)


def _metrics(targets: np.ndarray, probabilities: np.ndarray) -> dict[str, float]:
    return {
        "accuracy": float(accuracy_score(targets, probabilities >= 0.5)),
        "log_loss": float(log_loss(targets, probabilities)),
        "brier_score": float(brier_score_loss(targets, probabilities)),
        "roc_auc": float(roc_auc_score(targets, probabilities)),
        "ece_10": _ece(targets, probabilities),
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_matches(archive: Path) -> list[CanonicalMatch]:
    matches: list[CanonicalMatch] = []
    for index, raw in enumerate(iter_matches(archive)):
        meta = raw.get("meta") or {}
        raw_id = meta.get("match_id") or meta.get("data_version") or "match"
        matches.append(normalize_match(f"{raw_id}-{index:06d}", raw))
    return matches


def eligible(matches: Sequence[CanonicalMatch], gender: str) -> list[CanonicalMatch]:
    return sorted(
        [
            m for m in matches
            if m.gender == gender
            and m.match_type == "T20"
            and m.team_type == "international"
            and len(m.teams) == 2
            and m.winner in m.teams
        ],
        key=lambda m: m.dates[0] if m.dates else "",
    )


def split(matches: Sequence[CanonicalMatch], gender: str):
    expected = EXPECTED[gender]
    if len(matches) != expected["total"]:
        raise ValueError(
            f"expected {expected['total']} decisive {gender} T20 matches, got {len(matches)}"
        )
    train_n, validation_n, test_n = expected["split"]
    return (
        list(matches[:train_n]),
        list(matches[train_n:train_n + validation_n]),
        list(matches[train_n + validation_n:train_n + validation_n + test_n]),
    )


def select_k(
    train: Sequence[CanonicalMatch],
    validation: Sequence[CanonicalMatch],
    rows_by_k: dict[float, dict[str, dict]],
) -> tuple[float, list[dict[str, float]]]:
    results: list[dict[str, float]] = []
    for k, rows in rows_by_k.items():
        train_df = pd.DataFrame([rows[m.match_id] for m in train])
        validation_df = pd.DataFrame([rows[m.match_id] for m in validation])
        model = fit_logistic(train_df)
        p = model.predict_proba(validation_df[FEATURES])[:, 1]
        results.append({
            "k_factor": k,
            "validation_log_loss": float(log_loss(validation_df.target, p)),
            "validation_brier": float(brier_score_loss(validation_df.target, p)),
            "validation_auc": float(roc_auc_score(validation_df.target, p)),
            "validation_ece_10": _ece(validation_df.target.to_numpy(), p),
        })
    best = min(results, key=lambda item: (item["validation_log_loss"], item["validation_brier"]))["k_factor"]
    return best, results


def run(archive: Path, gender: str, output: Path, k_grid: Sequence[float] = DEFAULT_K_GRID) -> dict:
    all_matches = load_matches(archive)
    matches = eligible(all_matches, gender)
    train, validation, test = split(matches, gender)

    rows_by_k = {
        float(k): {row["match_id"]: row for row in build_challenger_b_feature_rows(matches, float(k))}
        for k in k_grid
    }
    selected_k, selection = select_k(train, validation, rows_by_k)
    rows = rows_by_k[selected_k]

    # Verify Challenger B changes only the Elo representation versus K=20.
    reference_rows = {row["match_id"]: row for row in build_v0_feature_rows(matches)}
    changed: set[str] = set()
    for row in rows.values():
        reference = reference_rows[row["match_id"]]
        for feature in FEATURES:
            if row[feature] != reference[feature]:
                changed.add(feature)
    allowed_changes = {"team_elo", "opponent_elo", "elo_difference"}
    unexpected = changed - allowed_changes
    if unexpected:
        raise ValueError(f"Challenger B changed non-Elo features: {sorted(unexpected)}")

    train_df = pd.DataFrame([rows[m.match_id] for m in train])
    validation_df = pd.DataFrame([rows[m.match_id] for m in validation])
    test_df = pd.DataFrame([rows[m.match_id] for m in test])
    model = fit_logistic(train_df)
    validation_raw = model.predict_proba(validation_df[FEATURES])[:, 1]
    test_raw = model.predict_proba(test_df[FEATURES])[:, 1]
    calibrated = ValidationPlattCalibrator().fit(validation_raw, validation_df.target.to_numpy())
    test_calibrated = calibrated.predict_proba(test_raw)

    result = {
        "experiment": "T20 Challenger B",
        "status": "challenger_only",
        "gender": gender,
        "hypothesis": "Increase Elo responsiveness by selecting K from a predeclared validation-only grid while changing no other feature or estimator component.",
        "corpus": {"sha256": _sha256(archive), "source": "Cricsheet T20 JSON archive", "matches": len(matches)},
        "split": {"train": len(train), "validation": len(validation), "test": len(test)},
        "k_grid": list(map(float, k_grid)),
        "selection_rule": "minimum validation log loss; tie-break validation Brier",
        "selected_k": selected_k,
        "validation_selection": selection,
        "changed_features_vs_v0": sorted(changed),
        "test_raw": _metrics(test_df.target.to_numpy(), test_raw),
        "test_calibrated": _metrics(test_df.target.to_numpy(), test_calibrated),
        "feature_contract": list(FEATURES),
        "estimator": "StandardScaler + LogisticRegression(max_iter=2000)",
        "calibration": "validation-only Platt; production comparison follows gender-specific V0/W0 policy",
        "reference_policy": "male compares calibrated challenger against calibrated V0; female compares raw challenger against raw W0",
        "v0_w0_modified": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run T20 Challenger B")
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--gender", choices=("male", "female"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(run(args.archive, args.gender, args.output), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

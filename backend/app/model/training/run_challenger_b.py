"""Run T20 Challenger B with a validation-selected Elo K-factor."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Sequence

import numpy as np
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, roc_auc_score

from app.model.data.normalizer import CanonicalMatch, normalize_match
from app.model.data.parser import iter_matches
from app.model.features.team_form import TeamFormEngine
from app.model.training.calibration import ValidationPlattCalibrator
from app.model.training.challenger_b import (
    DEFAULT_K_GRID,
    build_challenger_b_feature_rows,
    fit_logistic,
)
from app.model.training.model_v0 import FEATURES


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


def split(matches: Sequence[CanonicalMatch]) -> tuple[list[CanonicalMatch], list[CanonicalMatch], list[CanonicalMatch]]:
    n = len(matches)
    a = int(n * 0.70)
    b = int(n * 0.85)
    return list(matches[:a]), list(matches[a:b]), list(matches[b:])


def select_k(train: Sequence[CanonicalMatch], validation: Sequence[CanonicalMatch], rows_by_k: dict[float, dict[str, dict]]) -> tuple[float, list[dict[str, float]]]:
    results: list[dict[str, float]] = []
    for k, rows in rows_by_k.items():
        train_df = __import__("pandas").DataFrame([rows[m.match_id] for m in train])
        validation_df = __import__("pandas").DataFrame([rows[m.match_id] for m in validation])
        model = fit_logistic(train_df)
        p = model.predict_proba(validation_df[FEATURES])[:, 1]
        results.append({
            "k_factor": k,
            "validation_log_loss": float(log_loss(validation_df.target, p)),
            "validation_brier": float(brier_score_loss(validation_df.target, p)),
            "validation_auc": float(roc_auc_score(validation_df.target, p)),
        })
    best = min(results, key=lambda item: item["validation_log_loss"])["k_factor"]
    return best, results


def run(archive: Path, gender: str, output: Path, k_grid: Sequence[float] = DEFAULT_K_GRID) -> dict:
    all_matches = load_matches(archive)
    matches = eligible(all_matches, gender)
    train, validation, test = split(matches)

    rows_by_k = {
        float(k): {row["match_id"]: row for row in build_challenger_b_feature_rows(matches, float(k))}
        for k in k_grid
    }
    selected_k, selection = select_k(train, validation, rows_by_k)
    rows = rows_by_k[selected_k]

    import pandas as pd
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
        "gender": gender,
        "hypothesis": "Increase Elo responsiveness by selecting K from a predeclared validation-only grid while changing no other feature or estimator component.",
        "corpus_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "matches": len(matches),
        "split": {"train": len(train), "validation": len(validation), "test": len(test)},
        "k_grid": list(map(float, k_grid)),
        "selected_k": selected_k,
        "validation_selection": selection,
        "test_raw": _metrics(test_df.target.to_numpy(), test_raw),
        "test_calibrated": _metrics(test_df.target.to_numpy(), test_calibrated),
        "feature_contract": list(FEATURES),
        "estimator": "StandardScaler + LogisticRegression(max_iter=2000)",
        "calibration": "validation-only Platt; production policy remains gender-specific reference policy",
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

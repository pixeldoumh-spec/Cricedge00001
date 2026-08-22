"""Pinned robustness/backtesting harness for Women's Model W0.

The harness is intentionally separate from the W0 baseline evaluator. It never
changes the baseline 1,446/310/310 split or writes W0 artifacts. Every rolling
window fits the same StandardScaler + LogisticRegression(max_iter=2000)
architecture and calibrates only on that window's validation slice.

Usage:
    python -m app.model.training.w0_robustness \
        --archive /path/to/t20s_json.zip \
        --output docs/model/w0_robustness.json
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.model.data.normalizer import CanonicalMatch, normalize_match
from app.model.data.parser import iter_matches
from app.model.training.calibration import ValidationPlattCalibrator
from app.model.training.model_v0 import FEATURES, build_v0_feature_rows

EXPECTED_TOTAL_WOMENS_T20 = 2114
EXPECTED_DECISIVE = 2066
EXPECTED_SPLIT = (1446, 310, 310)
EXPECTED_FEATURES = (
    "team_elo", "opponent_elo", "elo_difference",
    "team_form_3", "team_form_5", "team_form_10",
    "venue_team_win_rate", "venue_bat_first_win_rate",
    "head_to_head_win_rate", "batting_run_rate", "bowling_run_rate",
    "batting_wicket_rate", "bowling_wicket_rate",
)
WINDOWS = (0.50, 0.55, 0.60, 0.65, 0.70)


def load_womens_t20(archive: Path) -> list[CanonicalMatch]:
    matches: list[CanonicalMatch] = []
    for index, raw in enumerate(iter_matches(archive)):
        match_id = f"w20-{index:06d}"
        match = normalize_match(match_id, raw)
        if (
            match.match_type == "T20"
            and match.gender == "female"
            and len(match.teams) == 2
            and match.winner in match.teams
        ):
            matches.append(match)
    matches.sort(key=lambda m: (m.dates[0] if m.dates else "", m.match_id))
    return matches


def _ece(y: np.ndarray, p: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0.0, 1.0, bins + 1)
    value = 0.0
    for i in range(bins):
        mask = (p >= edges[i]) & (p <= edges[i + 1] if i == bins - 1 else p < edges[i + 1])
        if mask.any():
            value += mask.mean() * abs(float(y[mask].mean()) - float(p[mask].mean()))
    return float(value)


def _metrics(y: np.ndarray, p: np.ndarray) -> dict[str, float]:
    return {
        "accuracy": float(accuracy_score(y, p >= 0.5)),
        "log_loss": float(log_loss(y, p)),
        "brier": float(brier_score_loss(y, p)),
        "auc": float(roc_auc_score(y, p)) if len(np.unique(y)) == 2 else float("nan"),
        "ece": _ece(y, p),
    }


def _fit_eval(rows: list[dict], train_idx: np.ndarray, val_idx: np.ndarray, test_idx: np.ndarray) -> dict:
    x_train = np.asarray([[r[f] for f in FEATURES] for r in (rows[i] for i in train_idx)], dtype=float)
    y_train = np.asarray([rows[i]["target"] for i in train_idx], dtype=int)
    x_val = np.asarray([[r[f] for f in FEATURES] for r in (rows[i] for i in val_idx)], dtype=float)
    y_val = np.asarray([rows[i]["target"] for i in val_idx], dtype=int)
    x_test = np.asarray([[r[f] for f in FEATURES] for r in (rows[i] for i in test_idx)], dtype=float)
    y_test = np.asarray([rows[i]["target"] for i in test_idx], dtype=int)

    model = Pipeline([
        ("scale", StandardScaler()),
        ("logistic", LogisticRegression(max_iter=2000)),
    ])
    model.fit(x_train, y_train)
    val_raw = model.predict_proba(x_val)[:, 1]
    calibrator = ValidationPlattCalibrator().fit(val_raw, y_val)
    test_raw = model.predict_proba(x_test)[:, 1]
    test_prob = calibrator.predict_proba(test_raw)
    return {
        "train": int(len(train_idx)),
        "validation": int(len(val_idx)),
        "test": int(len(test_idx)),
        "metrics": _metrics(y_test, test_prob),
    }


def run(archive: Path) -> dict:
    matches = load_womens_t20(archive)
    if len(matches) != EXPECTED_DECISIVE:
        raise ValueError(f"expected {EXPECTED_DECISIVE} decisive women's T20 matches, got {len(matches)}")
    rows = build_v0_feature_rows(matches)
    if len(rows) != EXPECTED_DECISIVE:
        raise ValueError(f"expected {EXPECTED_DECISIVE} feature rows, got {len(rows)}")
    if tuple(FEATURES) != EXPECTED_FEATURES:
        raise ValueError("W0 robustness feature contract differs from the pinned 13-feature contract")

    n = len(rows)
    baseline_split = (1446, 310, 310)
    if sum(baseline_split) != n:
        raise ValueError(f"baseline split changed: expected {EXPECTED_SPLIT}, got {baseline_split}")

    results: dict[str, object] = {
        "contract": {
            "population": EXPECTED_TOTAL_WOMENS_T20,
            "decisive": EXPECTED_DECISIVE,
            "baseline_split": {"train": 1446, "validation": 310, "test": 310},
            "features": list(EXPECTED_FEATURES),
            "estimator": "StandardScaler + LogisticRegression(max_iter=2000)",
            "calibration": "ValidationPlattCalibrator fitted only on each validation window",
            "baseline_test_modified": False,
        },
        "rolling_origin": [],
    }

    for fraction in WINDOWS:
        train_end = int(n * fraction)
        validation_size = max(1, int(n * 0.10))
        test_size = max(1, int(n * 0.10))
        val_end = train_end + validation_size
        test_end = min(n, val_end + test_size)
        if test_end <= val_end or train_end < 100:
            continue
        results["rolling_origin"].append({
            "train_fraction": fraction,
            **_fit_eval(rows, np.arange(0, train_end), np.arange(train_end, val_end), np.arange(val_end, test_end)),
        })

    third = n // 3
    regime_specs = {
        "middle": (third, 2 * third),
        "newer": (2 * third, n),
    }
    regimes = []
    for name, (start, end) in regime_specs.items():
        train_end = start
        val_start = max(0, start - max(1, int(n * 0.10)))
        regimes.append({
            "period": name,
            "start_index": start,
            "end_index": end,
            **_fit_eval(rows, np.arange(0, val_start), np.arange(val_start, train_end), np.arange(start, end)),
        })
    results["time_regimes"] = regimes

    match_by_id = {m.match_id: m for m in matches}
    competition_counts = Counter((match_by_id[r["match_id"]].competition or "unknown") for r in rows)
    results["competition_counts"] = dict(sorted(competition_counts.items(), key=lambda kv: (-kv[1], kv[0])))

    team_counts: defaultdict[str, int] = defaultdict(int)
    depth_rows = []
    for r in rows:
        match = match_by_id[r["match_id"]]
        depth = max((team_counts[t] for t in match.teams), default=0)
        depth_rows.append(depth)
        for team in match.teams:
            team_counts[team] += 1
    buckets = {"0-4": 0, "5-19": 0, "20+": 0}
    for depth in depth_rows:
        buckets["0-4" if depth < 5 else "5-19" if depth < 20 else "20+"] += 1
    results["team_history_depth_counts"] = buckets
    results["home_away_neutral"] = {
        "status": "not_available",
        "reason": "CanonicalMatch does not encode a reliable home-team field; do not infer home advantage from venue."
    }
    results["notes"] = [
        "W0 baseline 1,446/310/310 split is asserted and left unchanged.",
        "Every rolling evaluation calibrates only on its own validation slice.",
        "The 310-match baseline test set is never used to fit a model or calibrator.",
        "Competition counts and team-history depth are descriptive corpus diagnostics; predictive subgroup metrics require a dedicated prediction ledger.",
    ]
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the pinned W0 robustness/backtesting harness")
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.archive)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Pinned robustness/backtesting harness for Women's Model W0."""
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
        match = normalize_match(f"w20-{index:06d}", raw)
        if match.match_type == "T20" and match.gender == "female" and len(match.teams) == 2 and match.winner in match.teams:
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
        "log_loss": float(log_loss(y, p, labels=[0, 1])),
        "brier": float(brier_score_loss(y, p)),
        "auc": float(roc_auc_score(y, p)) if len(np.unique(y)) == 2 else float("nan"),
        "ece": _ece(y, p),
    }


def _arrays(rows: list[dict], indices: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return (
        np.asarray([[r[f] for f in FEATURES] for r in (rows[i] for i in indices)], dtype=float),
        np.asarray([rows[i]["target"] for i in indices], dtype=int),
    )


def _fit_predict(rows: list[dict], train_idx: np.ndarray, val_idx: np.ndarray, test_idx: np.ndarray):
    x_train, y_train = _arrays(rows, train_idx)
    x_val, y_val = _arrays(rows, val_idx)
    x_test, y_test = _arrays(rows, test_idx)
    model = Pipeline([("scale", StandardScaler()), ("logistic", LogisticRegression(max_iter=2000))])
    model.fit(x_train, y_train)
    calibrator = ValidationPlattCalibrator().fit(model.predict_proba(x_val)[:, 1], y_val)
    raw = model.predict_proba(x_test)[:, 1]
    return model, calibrator, y_test, calibrator.predict_proba(raw), raw


def _fit_eval(rows: list[dict], train_idx: np.ndarray, val_idx: np.ndarray, test_idx: np.ndarray) -> dict:
    _, _, y_test, p, _ = _fit_predict(rows, train_idx, val_idx, test_idx)
    return {"train": int(len(train_idx)), "validation": int(len(val_idx)), "test": int(len(test_idx)), "metrics": _metrics(y_test, p)}


def _confidence_buckets(y: np.ndarray, p: np.ndarray) -> list[dict]:
    confidence = np.maximum(p, 1.0 - p)
    specs = [("50-60%", 0.50, 0.60), ("60-70%", 0.60, 0.70), ("70-80%", 0.70, 0.80), ("80-90%", 0.80, 0.90), ("90-100%", 0.90, 1.01)]
    out = []
    for name, lo, hi in specs:
        mask = (confidence >= lo) & (confidence < hi)
        if mask.any():
            out.append({"bucket": name, "count": int(mask.sum()), "accuracy": float(np.mean((p[mask] >= 0.5) == y[mask])), "mean_confidence": float(confidence[mask].mean())})
        else:
            out.append({"bucket": name, "count": 0})
    return out


def _outcome_subgroups(y: np.ndarray, p: np.ndarray) -> dict:
    predicted = (p >= 0.5).astype(int)
    correct = predicted == y
    return {
        "actual_team_win": {"count": int((y == 1).sum()), "accuracy": float(correct[y == 1].mean()) if (y == 1).any() else None, "mean_probability": float(p[y == 1].mean()) if (y == 1).any() else None},
        "actual_opponent_win": {"count": int((y == 0).sum()), "accuracy": float(correct[y == 0].mean()) if (y == 0).any() else None, "mean_probability": float(p[y == 0].mean()) if (y == 0).any() else None},
        "predicted_team_win": {"count": int((predicted == 1).sum()), "precision": float(y[predicted == 1].mean()) if (predicted == 1).any() else None, "mean_probability": float(p[predicted == 1].mean()) if (predicted == 1).any() else None},
        "predicted_opponent_win": {"count": int((predicted == 0).sum()), "precision": float((1 - y[predicted == 0]).mean()) if (predicted == 0).any() else None, "mean_probability": float((1 - p[predicted == 0]).mean()) if (predicted == 0).any() else None},
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
    baseline_split = EXPECTED_SPLIT
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
        results["rolling_origin"].append({"train_fraction": fraction, **_fit_eval(rows, np.arange(0, train_end), np.arange(train_end, val_end), np.arange(val_end, test_end))})

    third = n // 3
    regimes = []
    for name, (start, end) in {"middle": (third, 2 * third), "newer": (2 * third, n)}.items():
        validation_size = max(1, int(n * 0.10))
        val_start = max(0, start - validation_size)
        regimes.append({"period": name, "start_index": start, "end_index": end, **_fit_eval(rows, np.arange(0, val_start), np.arange(val_start, start), np.arange(start, end))})
    results["time_regimes"] = regimes

    match_by_id = {m.match_id: m for m in matches}
    competition_counts = Counter((match_by_id[r["match_id"]].competition or "unknown") for r in rows)
    results["competition_counts"] = dict(sorted(competition_counts.items(), key=lambda kv: (-kv[1], kv[0])))

    team_counts: defaultdict[str, int] = defaultdict(int)
    depth_rows = []
    for r in rows:
        match = match_by_id[r["match_id"]]
        depth_rows.append(max((team_counts[t] for t in match.teams), default=0))
        for team in match.teams:
            team_counts[team] += 1
    buckets = {"0-4": 0, "5-19": 0, "20+": 0}
    for depth in depth_rows:
        buckets["0-4" if depth < 5 else "5-19" if depth < 20 else "20+"] += 1
    results["team_history_depth_counts"] = buckets
    results["home_away_neutral"] = {"status": "not_available", "reason": "CanonicalMatch does not encode a reliable home-team field; do not infer home advantage from venue."}

    base_train = np.arange(0, 1446)
    base_val = np.arange(1446, 1756)
    base_test = np.arange(1756, 2066)
    _, _, base_y, base_p, _ = _fit_predict(rows, base_train, base_val, base_test)
    results["baseline_test_subgroups"] = {
        "test_count": 310,
        "confidence_buckets": _confidence_buckets(base_y, base_p),
        "outcome_subgroups": _outcome_subgroups(base_y, base_p),
        "metrics": _metrics(base_y, base_p),
    }

    holdout_size = 171
    holdout_start = n - holdout_size
    holdout_val_size = 310
    holdout_val_start = holdout_start - holdout_val_size
    holdout_train = np.arange(0, holdout_val_start)
    holdout_val = np.arange(holdout_val_start, holdout_start)
    holdout_test = np.arange(holdout_start, n)
    _, _, hold_y, hold_p, _ = _fit_predict(rows, holdout_train, holdout_val, holdout_test)
    results["future_holdout"] = {
        "train": int(len(holdout_train)),
        "validation": int(len(holdout_val)),
        "holdout": int(len(holdout_test)),
        "start_index": int(holdout_start),
        "end_index": int(n),
        "date_start": matches[holdout_start].dates[0] if matches[holdout_start].dates else None,
        "date_end": matches[-1].dates[0] if matches[-1].dates else None,
        "metrics": _metrics(hold_y, hold_p),
        "confidence_buckets": _confidence_buckets(hold_y, hold_p),
        "outcome_subgroups": _outcome_subgroups(hold_y, hold_p),
        "baseline_test_310_used_for_fit_or_calibration": False,
        "relationship_to_baseline_test": "nested final 171-match slice of the frozen 310-match test period; predictions are generated without fitting/calibration on the baseline test period",
    }

    results["notes"] = [
        "W0 baseline 1,446/310/310 split is asserted and left unchanged.",
        "Every rolling evaluation calibrates only on its own validation slice.",
        "The frozen 310-match baseline test set is never used to fit or calibrate any model.",
        "Competition counts and team-history depth are corpus diagnostics.",
        "Confidence/outcome subgroup metrics are evaluated on predictions generated by the frozen baseline contract.",
        "The future holdout is a nested final 171-match slice of the baseline test period; it is a temporal holdout, not an additional disjoint corpus period.",
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

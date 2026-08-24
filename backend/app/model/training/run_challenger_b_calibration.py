"""Execute the Challenger B calibration/reconciliation experiment.

Fixed Challenger B K: male=80, female=160.
Only validation-only Platt calibration is added after the B logistic model.
The frozen V0/W0 test partition is never used to fit or choose calibration.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd

from app.model.data.normalizer import CanonicalMatch, normalize_match
from app.model.data.parser import iter_matches
from app.model.training.challenger_b import build_challenger_b_feature_rows
from app.model.training.challenger_b_calibration import (
    SELECTED_K,
    fit_and_predict,
    metrics,
    rolling_origin,
)
from app.model.training.model_v0 import FEATURES

EXPECTED = {
    "male": {"total": 3411, "split": (2387, 511, 513)},
    "female": {"total": 2066, "split": (1446, 310, 310)},
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_matches(archive: Path) -> list[CanonicalMatch]:
    matches = []
    for index, raw in enumerate(iter_matches(archive)):
        meta = raw.get("meta") or {}
        raw_id = meta.get("match_id") or meta.get("data_version") or "match"
        matches.append(normalize_match(f"{raw_id}-{index:06d}", raw))
    return matches


def eligible(matches: Sequence[CanonicalMatch], gender: str) -> list[CanonicalMatch]:
    return sorted(
        [m for m in matches if m.gender == gender and m.match_type == "T20"
         and m.team_type == "international" and len(m.teams) == 2
         and m.winner in m.teams],
        key=lambda m: (m.dates[0] if m.dates else "", m.match_id),
    )


def split(matches: Sequence[CanonicalMatch], gender: str):
    expected = EXPECTED[gender]
    if len(matches) != expected["total"]:
        raise ValueError(f"expected {expected['total']} decisive {gender} T20 matches, got {len(matches)}")
    a, b, c = expected["split"]
    return list(matches[:a]), list(matches[a:a+b]), list(matches[a+b:a+b+c])


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Challenger B calibration reconciliation")
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--gender", choices=("male", "female"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    matches = eligible(load_matches(args.archive), args.gender)
    train_matches, validation_matches, test_matches = split(matches, args.gender)
    rows = {r["match_id"]: r for r in build_challenger_b_feature_rows(matches, SELECTED_K[args.gender])}
    ordered_rows = [rows[m.match_id] for m in matches]
    train = pd.DataFrame([rows[m.match_id] for m in train_matches])
    validation = pd.DataFrame([rows[m.match_id] for m in validation_matches])
    test = pd.DataFrame([rows[m.match_id] for m in test_matches])

    _, calibrator, val_raw, test_raw, test_cal = fit_and_predict(train, validation, test)
    y_test = test["target"].to_numpy(dtype=int)

    # The final 171-match future holdout is the last 171 rows. Its calibration
    # validation slice is the immediately preceding 310 matches, matching the
    # existing robustness convention and never fitting on the holdout itself.
    holdout_n = 171
    holdout_start = len(ordered_rows) - holdout_n
    holdout_val_n = 310
    holdout_val_start = holdout_start - holdout_val_n
    holdout_train = pd.DataFrame(ordered_rows[:holdout_val_start])
    holdout_val = pd.DataFrame(ordered_rows[holdout_val_start:holdout_start])
    holdout = pd.DataFrame(ordered_rows[holdout_start:])
    _, _, _, hold_raw, hold_cal = fit_and_predict(holdout_train, holdout_val, holdout)
    y_hold = holdout["target"].to_numpy(dtype=int)

    ro = rolling_origin(ordered_rows)
    result = {
        "experiment": "T20 Challenger B calibration/reconciliation",
        "status": "completed_diagnostic_only",
        "gender": args.gender,
        "hypothesis": "Validation-only Platt calibration can recover probability calibration of the fixed-K Challenger B without materially destroying its predictive gains.",
        "selected_k": SELECTED_K[args.gender],
        "calibration": "ValidationPlattCalibrator fitted only on chronological validation predictions",
        "corpus": {"sha256": sha256(args.archive), "source": "Cricsheet T20 JSON archive", "matches": len(matches)},
        "split": {"train": len(train), "validation": len(validation), "test": len(test)},
        "feature_contract": list(FEATURES),
        "model_change": "none beyond Challenger B K; no feature or estimator changes",
        "frozen_test": {
            "raw": metrics(y_test, test_raw),
            "calibrated": metrics(y_test, test_cal),
            "delta_calibrated_minus_raw": {
                k: metrics(y_test, test_cal)[k] - metrics(y_test, test_raw)[k]
                for k in metrics(y_test, test_raw)
            },
        },
        "rolling_origin": ro,
        "future_holdout_171": {
            "train": len(holdout_train), "validation": len(holdout_val), "holdout": len(holdout),
            "raw": metrics(y_hold, hold_raw),
            "calibrated": metrics(y_hold, hold_cal),
            "delta_calibrated_minus_raw": {
                k: metrics(y_hold, hold_cal)[k] - metrics(y_hold, hold_raw)[k]
                for k in metrics(y_hold, hold_raw)
            },
        },
        "calibrator_parameters": {
            "intercept": float(calibrator._model.intercept_[0]),
            "slope": float(calibrator._model.coef_[0, 0]),
        },
        "decision_rule": {
            "calibration_success": "calibrated ECE must improve on frozen test and future holdout, while log loss and Brier must not materially worsen; AUC should remain unchanged within numerical tolerance and accuracy should not materially deteriorate.",
            "promotion": "diagnostic only; this experiment does not modify V0/W0 or promote Challenger B.",
        },
        "v0_w0_modified": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

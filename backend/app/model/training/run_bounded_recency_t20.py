"""Run the predeclared bounded-recency T20 extension.

This runner appends bounded recent fast-Elo movement to raw Challenger B.
Selection is validation-only. Frozen test and the final 171-match future holdout
never choose a configuration. V0/W0 are not modified.

For the rolling-origin evaluation, the configuration selected on the main
chronological validation split is held fixed and evaluated at each origin.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
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
from app.model.training.challenger_b import build_challenger_b_feature_rows
from app.model.training.model_v0 import FEATURES

EXPECTED = {"male": (3411, (2387, 511, 513), 80), "female": (2066, (1446, 310, 310), 160)}
CONFIGS = ((5, 100.0, False), (10, 100.0, False), (20, 100.0, False),
           (10, 150.0, False), (20, 150.0, False), (10, 100.0, True),
           (20, 100.0, True))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_matches(path: Path) -> list[CanonicalMatch]:
    out = []
    for i, raw in enumerate(iter_matches(path)):
        meta = raw.get("meta") or {}
        raw_id = meta.get("match_id") or meta.get("data_version") or "match"
        out.append(normalize_match(f"{raw_id}-{i:06d}", raw))
    return out


def eligible(matches: Sequence[CanonicalMatch], gender: str) -> list[CanonicalMatch]:
    return sorted(
        [m for m in matches if m.gender == gender and m.match_type == "T20"
         and m.team_type == "international" and len(m.teams) == 2
         and m.winner in m.teams],
        key=lambda m: m.dates[0] if m.dates else "",
    )


def bounded_rows(matches: Sequence[CanonicalMatch], k: float, horizon: int,
                  cap: float, magnitude: bool) -> dict[str, dict]:
    """Return bounded movement keyed by the canonical match id."""
    elo: dict[str, float] = {}
    history: dict[str, list[float]] = {}
    out: dict[str, dict] = {}
    for match in sorted(matches, key=lambda m: m.dates[0] if m.dates else ""):
        team, opponent = match.teams

        def rate(name: str) -> float:
            previous = history.get(name, [])
            if len(previous) < horizon:
                return 0.0
            return (elo.get(name, 1500.0) - previous[-horizon]) / horizon

        team_rate = rate(team)
        opponent_rate = rate(opponent)
        relative_rate = team_rate - opponent_rate
        bt = math.tanh(team_rate / cap)
        bo = math.tanh(opponent_rate / cap)
        br = math.tanh(relative_rate / cap)
        row = {
            "bounded_team_rate": bt,
            "bounded_opponent_rate": bo,
            "bounded_relative_rate": br,
        }
        if magnitude:
            row.update({
                "bounded_team_magnitude": abs(bt),
                "bounded_opponent_magnitude": abs(bo),
                "bounded_relative_magnitude": abs(br),
            })
        out[match.match_id] = row

        a = elo.get(team, 1500.0)
        b = elo.get(opponent, 1500.0)
        expected = 1.0 / (1.0 + 10 ** ((b - a) / 400.0))
        score = 1.0 if match.winner == team else 0.0
        elo[team] = a + k * (score - expected)
        elo[opponent] = b + k * ((1.0 - score) - (1.0 - expected))
        history.setdefault(team, []).append(elo[team])
        history.setdefault(opponent, []).append(elo[opponent])
    return out


def fit(train: pd.DataFrame, features: list[str]) -> Pipeline:
    model = Pipeline([("scale", StandardScaler()), ("logistic", LogisticRegression(max_iter=2000))])
    model.fit(train[features], train.target)
    return model


def ece(y: np.ndarray, p: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0.0, 1.0, bins + 1)
    value = 0.0
    for i in range(bins):
        mask = (p >= edges[i]) & (p <= edges[i + 1] if i == bins - 1 else p < edges[i + 1])
        if mask.any():
            value += mask.mean() * abs(y[mask].mean() - p[mask].mean())
    return float(value)


def metrics(model: Pipeline, frame: pd.DataFrame, features: list[str]) -> dict[str, float]:
    y = frame.target.to_numpy(dtype=int)
    p = model.predict_proba(frame[features])[:, 1]
    return {"accuracy": float(accuracy_score(y, p >= .5)),
            "log_loss": float(log_loss(y, p)),
            "brier": float(brier_score_loss(y, p)),
            "auc": float(roc_auc_score(y, p)), "ece": ece(y, p)}


def run_gender(matches: list[CanonicalMatch], gender: str) -> dict:
    total, split_counts, k = EXPECTED[gender]
    if len(matches) != total:
        raise ValueError(f"expected {total} {gender} matches, got {len(matches)}")
    train_n, validation_n, test_n = split_counts
    base = {r["match_id"]: r for r in build_challenger_b_feature_rows(matches, k)}
    ordered_base = pd.DataFrame([base[m.match_id] for m in matches])
    tr0 = ordered_base.iloc[:train_n]
    te0 = ordered_base.iloc[train_n + validation_n:train_n + validation_n + test_n]
    base_model = fit(tr0, FEATURES)
    base_test = metrics(base_model, te0, FEATURES)

    ranking = []
    built: dict[tuple[int, float, bool], pd.DataFrame] = {}
    for horizon, cap, magnitude in CONFIGS:
        movement = bounded_rows(matches, k, horizon, cap, magnitude)
        frame = ordered_base.copy()
        extra = pd.DataFrame([movement[m.match_id] for m in matches])
        frame = pd.concat([frame.reset_index(drop=True), extra], axis=1)
        built[(horizon, cap, magnitude)] = frame
        features = FEATURES + list(extra.columns)
        model = fit(frame.iloc[:train_n], features)
        p = model.predict_proba(frame.iloc[train_n:train_n + validation_n][features])[:, 1]
        ranking.append((float(log_loss(frame.target.iloc[train_n:train_n + validation_n], p)), horizon, cap, magnitude))
    ranking.sort()
    selected = ranking[0][1:]
    selected_frame = built[selected]
    selected_features = FEATURES + [c for c in selected_frame.columns if c.startswith("bounded_")]
    selected_model = fit(selected_frame.iloc[:train_n], selected_features)
    selected_test = metrics(selected_model, selected_frame.iloc[train_n + validation_n:train_n + validation_n + test_n], selected_features)

    rolling = []
    n = len(matches)
    for fraction in (0.50, 0.55, 0.60, 0.65, 0.70):
        a = int(n * fraction); v = int(n * 0.10); t = int(n * 0.10)
        frame = built[selected]
        feats = FEATURES + [c for c in frame.columns if c.startswith("bounded_")]
        local_model = fit(frame.iloc[:a], feats)
        bounded_test = metrics(local_model, frame.iloc[a + v:a + v + t], feats)
        b_model = fit(ordered_base.iloc[:a], FEATURES)
        b_test = metrics(b_model, ordered_base.iloc[a + v:a + v + t], FEATURES)
        rolling.append({"train_fraction": fraction, "selected": selected,
                        "selection_source": "main_validation",
                        "challenger_b": b_test, "bounded": bounded_test})

    holdout_n = 171; holdout_val_n = 310
    holdout_start = len(matches) - holdout_n
    holdout_val_start = holdout_start - holdout_val_n
    hold = selected_frame.iloc[holdout_start:]
    hold_train = selected_frame.iloc[:holdout_val_start]
    hold_model = fit(hold_train, selected_features)
    future_b_model = fit(ordered_base.iloc[:holdout_val_start], FEATURES)
    future_b = metrics(future_b_model, ordered_base.iloc[holdout_start:], FEATURES)
    future_bounded = metrics(hold_model, hold, selected_features)

    return {"selected": selected, "validation_ranking": ranking,
            "frozen_test": {"challenger_b_raw": base_test, "bounded_selected": selected_test},
            "rolling_origin": rolling,
            "future_holdout_171": {"challenger_b_raw": future_b, "bounded_selected": future_bounded}}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    matches = load_matches(args.archive)
    result = {"experiment": "T20 bounded recency movement extension",
              "corpus_sha256": sha256(args.archive),
              "male": run_gender(eligible(matches, "male"), "male"),
              "female": run_gender(eligible(matches, "female"), "female")}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Export the chronological raw-probability stream required by adaptive calibration.

This exporter deliberately separates model generation from calibration. It emits
one row per eligible T20 match with the match date, partition, target and raw
Challenger B probability. No calibration is fitted here.

The prediction stream is generated with the exact frozen population and split
counts used by Challenger B. The model is trained only on the frozen training
partition. Validation/test/future probabilities are therefore out-of-sample
relative to that fitted model, and the adaptive calibration layer can later
consume the rows strictly in date order without reconstructing model state.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Sequence

import pandas as pd

from app.model.data.normalizer import CanonicalMatch, normalize_match
from app.model.data.parser import iter_matches
from app.model.training.challenger_b import build_challenger_b_feature_rows, fit_logistic
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
    out: list[CanonicalMatch] = []
    for i, raw in enumerate(iter_matches(archive)):
        meta = raw.get("meta") or {}
        raw_id = meta.get("match_id") or meta.get("data_version") or "match"
        out.append(normalize_match(f"{raw_id}-{i:06d}", raw))
    return out


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
        raise ValueError(f"expected {expected['total']} eligible {gender} matches, got {len(matches)}")
    a, b, c = expected["split"]
    return list(matches[:a]), list(matches[a:a+b]), list(matches[a+b:a+b+c])


def run(archive: Path, gender: str, output: Path, k: float) -> dict:
    matches = eligible(load_matches(archive), gender)
    train, validation, test = split(matches, gender)
    rows = {r["match_id"]: r for r in build_challenger_b_feature_rows(matches, k)}
    train_df = pd.DataFrame([rows[m.match_id] for m in train])
    model = fit_logistic(train_df)

    records = []
    for partition, subset in (("train", train), ("validation", validation), ("test", test)):
        df = pd.DataFrame([rows[m.match_id] for m in subset])
        p = model.predict_proba(df[FEATURES])[:, 1]
        for match, probability, target in zip(subset, p, df.target.to_numpy()):
            records.append({
                "match_id": match.match_id,
                "match_date": match.dates[0] if match.dates else "",
                "partition": partition,
                "target": int(target),
                "raw_probability": float(probability),
            })

    records.sort(key=lambda r: (r["match_date"], r["match_id"]))
    payload = {
        "schema": "t20_challenger_b_prediction_stream_v1",
        "gender": gender,
        "k_factor": k,
        "corpus_sha256": sha256(archive),
        "population_count": len(matches),
        "split": {"train": len(train), "validation": len(validation), "test": len(test)},
        "estimator": "StandardScaler + LogisticRegression(max_iter=2000)",
        "features": list(FEATURES),
        "calibration": "none; raw Challenger B probabilities",
        "rows": records,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Export dated Challenger B raw prediction stream")
    p.add_argument("--archive", type=Path, required=True)
    p.add_argument("--gender", choices=("male", "female"), required=True)
    p.add_argument("--k", type=float, required=True, help="Validation-selected K: 80 male, 160 female")
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args(argv)
    payload = run(args.archive, args.gender, args.output, args.k)
    print(json.dumps({k: payload[k] for k in ("schema", "gender", "k_factor", "corpus_sha256", "population_count", "split")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Run the frozen Challenger B against the 2026 CPL prospective stream.

This is deliberately a diagnostic transfer runner. Challenger B was trained on
male international T20 matches, while the CPL is franchise T20. No franchise
team is mapped to an international team or legacy franchise name.

The historical model is fixed at K=80 and the frozen 2387/511/513 contract.
Completed CPL results are then applied sequentially to a separate franchise
state. Because the current locked corpus does not contain CPL delivery JSON,
the live ball-strength state is reconstructed from published scorecard summary
runs, wickets and overs. This is not a canonical Cricsheet reproduction.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.model.data.normalizer import normalize_match
from app.model.data.parser import iter_matches
from app.model.training.challenger_b import build_challenger_b_feature_rows
from app.model.training.model_v0 import FEATURES

EXPECTED_MALE = (2387, 511, 513)


@dataclass
class SummaryMatch:
    match_id: str
    date: str
    teams: tuple[str, str]
    venue: str
    winner: str
    innings: tuple[tuple[int, int, int], tuple[int, int, int]]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_historical_matches(archive: Path):
    matches = []
    for index, raw in enumerate(iter_matches(archive)):
        meta = raw.get("meta") or {}
        raw_id = meta.get("match_id") or meta.get("data_version") or "match"
        matches.append(normalize_match(f"{raw_id}-{index:06d}", raw))
    return matches


def eligible_male(matches):
    return sorted(
        [
            m for m in matches
            if m.gender == "male"
            and m.match_type == "T20"
            and m.team_type == "international"
            and len(m.teams) == 2
            and m.winner in m.teams
        ],
        key=lambda m: m.dates[0] if m.dates else "",
    )


def fit_frozen_challenger_b(matches):
    if len(matches) != 3411:
        raise ValueError(f"expected 3411 eligible men's international T20 matches, got {len(matches)}")
    train_n, validation_n, test_n = EXPECTED_MALE
    if train_n + validation_n + test_n != len(matches):
        raise ValueError("frozen split contract does not sum to eligible population")

    rows = {row["match_id"]: row for row in build_challenger_b_feature_rows(matches, 80.0)}
    train = pd.DataFrame([rows[m.match_id] for m in matches[:train_n]])
    model = Pipeline([
        ("scale", StandardScaler()),
        ("logistic", LogisticRegression(max_iter=2000)),
    ])
    model.fit(train[FEATURES], train["target"])
    return model


class FranchiseState:
    def __init__(self, k: float = 80.0) -> None:
        self.k = k
        self.elo: dict[str, float] = {}
        self.results: dict[str, list[int]] = {}
        self.venue: dict[tuple[str, str], list[int]] = {}
        self.h2h: dict[tuple[str, str], list[int]] = {}
        self.ball: dict[str, list[float]] = {}

    def _elo(self, team: str) -> float:
        return self.elo.get(team, 1500.0)

    def _results(self, team: str) -> list[int]:
        return self.results.setdefault(team, [])

    def _ball(self, team: str) -> list[float]:
        return self.ball.setdefault(team, [0.0, 0.0, 0.0, 0.0, 0.0, 0.0])

    def before(self, team: str, opponent: str, venue: str) -> dict[str, float]:
        a = self._elo(team)
        b = self._elo(opponent)
        r = self._results(team)
        v = self.venue.get((venue, team), [0, 0, 0, 0])
        h = self.h2h.get((team, opponent), [])
        ba = self._ball(team)
        bb = self._ball(opponent)
        return {
            "team_elo": a,
            "opponent_elo": b,
            "elo_difference": a - b,
            "team_form_3": sum(r[-3:]) / len(r[-3:]) if r else 0.5,
            "team_form_5": sum(r[-5:]) / len(r[-5:]) if r else 0.5,
            "team_form_10": sum(r[-10:]) / len(r[-10:]) if r else 0.5,
            "venue_team_win_rate": v[0] / v[1] if v[1] else 0.5,
            "venue_bat_first_win_rate": v[2] / v[3] if v[3] else 0.5,
            "head_to_head_win_rate": sum(h) / len(h) if h else 0.5,
            "batting_run_rate": ba[0] * 6 / ba[1] if ba[1] else 0.0,
            "bowling_run_rate": bb[3] * 6 / bb[4] if bb[4] else 0.0,
            "batting_wicket_rate": ba[2] * 6 / ba[1] if ba[1] else 0.0,
            "bowling_wicket_rate": bb[5] * 6 / bb[4] if bb[4] else 0.0,
        }

    def after(self, match: SummaryMatch) -> None:
        team, opponent = match.teams
        a = self._elo(team)
        b = self._elo(opponent)
        expected = 1.0 / (1.0 + 10 ** ((b - a) / 400.0))
        score = 1.0 if match.winner == team else 0.0
        self.elo[team] = a + self.k * (score - expected)
        self.elo[opponent] = b + self.k * ((1.0 - score) - (1.0 - expected))
        self._results(team).append(int(score))
        self._results(opponent).append(int(1.0 - score))
        venue = self.venue.setdefault((match.venue, team), [0, 0, 0, 0])
        venue[0] += int(score)
        venue[1] += 1
        self.h2h.setdefault((team, opponent), []).append(int(score))

        for index, (runs, balls, wickets) in enumerate(match.innings):
            batting = match.teams[index]
            bowling = match.teams[1 - index]
            # Scorecard-summary adapter: legal-ball count is used because
            # canonical 2026 CPL delivery JSON is not in the locked corpus.
            bat = self._ball(batting)
            bowl = self._ball(bowling)
            bat[0] += runs
            bat[1] += balls
            bat[2] += wickets
            bowl[3] += runs
            bowl[4] += balls
            bowl[5] += wickets


CPL_RESULTS = (
    SummaryMatch("cpl-1", "2026-08-07", ("Jamaica Kingsmen", "Antigua and Barbuda Falcons"), "Arnos Vale Ground", "Antigua and Barbuda Falcons", ((167, 120, 7), (168, 120, 8))),
    SummaryMatch("cpl-2", "2026-08-08", ("St Kitts & Nevis Patriots", "Trinbago Knight Riders"), "Arnos Vale Ground", "Trinbago Knight Riders", ((109, 120, 9), (94, 90, 2))),
    SummaryMatch("cpl-3", "2026-08-09", ("Antigua and Barbuda Falcons", "Saint Lucia Kings"), "Arnos Vale Ground", "Saint Lucia Kings", ((183, 120, 7), (187, 120, 8))),
    SummaryMatch("cpl-4", "2026-08-11", ("Jamaica Kingsmen", "Barbados Tridents"), "Sabina Park", "Barbados Tridents", ((201, 120, 9), (206, 120, 3))),
    SummaryMatch("cpl-5", "2026-08-12", ("Saint Lucia Kings", "St Kitts & Nevis Patriots"), "Daren Sammy National Cricket Stadium", "St Kitts & Nevis Patriots", ((155, 120, 8), (156, 106, 5))),
    SummaryMatch("cpl-6", "2026-08-13", ("Jamaica Kingsmen", "Guyana Amazon Warriors"), "Sabina Park", "Guyana Amazon Warriors", ((117, 118, 10), (118, 85, 4))),
    SummaryMatch("cpl-7", "2026-08-14", ("Saint Lucia Kings", "Antigua and Barbuda Falcons"), "Daren Sammy National Cricket Stadium", "Saint Lucia Kings", ((54, 46, 7), (98, 114, 9))),
    SummaryMatch("cpl-8", "2026-08-15", ("Jamaica Kingsmen", "Trinbago Knight Riders"), "Sabina Park", "Jamaica Kingsmen", ((183, 112, 5), (182, 120, 6))),
    SummaryMatch("cpl-9", "2026-08-16", ("Saint Lucia Kings", "Barbados Tridents"), "Daren Sammy National Cricket Stadium", "Barbados Tridents", ((168, 108, 7), (177, 108, 5))),
    SummaryMatch("cpl-10", "2026-08-18", ("Jamaica Kingsmen", "St Kitts & Nevis Patriots"), "Sabina Park", "Jamaica Kingsmen", ((181, 120, 6), (130, 108, 10))),
    SummaryMatch("cpl-11", "2026-08-19", ("Saint Lucia Kings", "Guyana Amazon Warriors"), "Daren Sammy National Cricket Stadium", "Guyana Amazon Warriors", ((151, 120, 7), (157, 109, 3))),
    SummaryMatch("cpl-12", "2026-08-20", ("Antigua and Barbuda Falcons", "St Kitts & Nevis Patriots"), "Sir Vivian Richards Stadium", "Antigua and Barbuda Falcons", ((191, 117, 7), (187, 120, 6))),
    SummaryMatch("cpl-13", "2026-08-21", ("Saint Lucia Kings", "Jamaica Kingsmen"), "Daren Sammy National Cricket Stadium", "Saint Lucia Kings", ((171, 110, 4), (169, 120, 9))),
    SummaryMatch("cpl-14", "2026-08-22", ("Antigua and Barbuda Falcons", "Trinbago Knight Riders"), "Sir Vivian Richards Stadium", "Antigua and Barbuda Falcons", ((168, 111, 5), (165, 120, 6))),
    SummaryMatch("cpl-15", "2026-08-23", ("Antigua and Barbuda Falcons", "Guyana Amazon Warriors"), "Sir Vivian Richards Stadium", "Guyana Amazon Warriors", ((116, 102, 10), (121, 59, 3))),
)


def run(archive: Path, output: Path) -> dict:
    historical = eligible_male(load_historical_matches(archive))
    model = fit_frozen_challenger_b(historical)
    state = FranchiseState(k=80.0)
    for match in CPL_RESULTS:
        state.after(match)

    fixture = ("Antigua and Barbuda Falcons", "Barbados Tridents")
    features = state.before(fixture[0], fixture[1], "Sir Vivian Richards Stadium")
    frame = pd.DataFrame([features])
    probability = float(model.predict_proba(frame[FEATURES])[:, 1][0])

    result = {
        "experiment": "CPL 2026 prospective validation",
        "snapshot_date": "2026-08-25",
        "corpus_sha256": sha256(archive),
        "model": {"selected_k": 80, "training_rows": EXPECTED_MALE[0], "validation_rows": EXPECTED_MALE[1], "test_rows": EXPECTED_MALE[2]},
        "completed_cpl_matches_used": len(CPL_RESULTS),
        "fixture": {"match_number": 16, "date": "2026-08-25", "home": fixture[0], "away": fixture[1], "venue": "Sir Vivian Richards Stadium"},
        "prediction": {"home_probability": probability, "away_probability": 1.0 - probability, "predicted_winner": fixture[0] if probability >= 0.5 else fixture[1]},
        "pre_match_features": features,
        "input_quality": "scorecard_summary_adapter",
        "warning": "CPL is outside the locked international-T20 training population; this is a transfer diagnostic, not a production validation. 2026 CPL ball-strength state uses legal-ball scorecard summaries rather than canonical delivery JSON.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.archive, args.output), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Feature pipeline + logistic-regression match model trained on ingested Cricsheet matches."""
from __future__ import annotations

import math
import os
from collections import defaultdict
from datetime import datetime, timezone

import numpy as np
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

ARTIFACT_VERSION = "cricedge-match-v1"
MIN_TEAM_MATCHES = 8            # below this a team is flagged LOW DATA
ELO_K = {"T20": 24.0, "ODI": 20.0, "Test": 16.0}
BUCKET_BY_MATCH_TYPE = {
    "T20": "T20", "IT20": "T20", "T20I": "T20", "Hundred": "T20",
    "ODI": "ODI", "ODM": "ODI", "List A": "ODI",
    "Test": "Test", "MDM": "Test", "First-class": "Test",
}
BUCKET_BY_FORMAT = {"T20": "T20", "Hundred": "T20", "ODI": "ODI", "Test": "Test"}


def norm_sf(line: float, mean: float, sd: float) -> float:
    """P(X > line) for a normal approximation."""
    if sd <= 0:
        return 0.5
    z = (line - mean) / (sd * math.sqrt(2))
    return max(0.02, min(0.98, 0.5 * (1 - math.erf(z))))


class _Rolling:
    __slots__ = ("elo", "played", "wins", "recent", "runs", "wkts", "conceded")

    def __init__(self):
        self.elo = 1500.0
        self.played = 0
        self.wins = 0
        self.recent = []
        self.runs = []
        self.wkts = []
        self.conceded = []

    def form(self) -> float:
        window = self.recent[-10:]
        return sum(window) / len(window) if window else 0.5

    def runs_rate(self) -> float:
        window = self.runs[-20:]
        return sum(window) / len(window) if window else 0.0


def _mean_std(values: list[float], fallback_mean: float, fallback_sd: float) -> tuple[float, float]:
    if len(values) < 3:
        return fallback_mean, fallback_sd
    arr = np.asarray(values[-40:], dtype=float)
    sd = float(arr.std(ddof=1)) if arr.size > 1 else fallback_sd
    return float(arr.mean()), max(sd, fallback_sd * 0.4)


def _fit_logistic(x: np.ndarray, y: np.ndarray, epochs: int = 4000, lr: float = 0.08):
    n, d = x.shape
    w = np.zeros(d)
    b = 0.0
    for _ in range(epochs):
        z = x @ w + b
        p = 1.0 / (1.0 + np.exp(-z))
        err = p - y
        w -= lr * (x.T @ err) / n
        b -= lr * err.mean()
    return w, b


def _metrics(p: np.ndarray, y: np.ndarray) -> dict:
    if p.size == 0:
        return {"samples": 0, "accuracy": None, "log_loss": None, "brier": None}
    clipped = np.clip(p, 1e-6, 1 - 1e-6)
    return {
        "samples": int(p.size),
        "accuracy": round(float(((p > 0.5) == (y > 0.5)).mean()) * 100, 1),
        "log_loss": round(float(-(y * np.log(clipped) + (1 - y) * np.log(1 - clipped)).mean()), 4),
        "brier": round(float(((p - y) ** 2).mean()), 4),
    }


def build_and_train(db) -> dict:
    """Chronological feature build + per-format logistic model. Returns the persisted artifact."""
    cursor = db["cricsheet_matches"].find(
        {}, {"_id": 0, "teams": 1, "match_date": 1, "match_type": 1, "outcome": 1, "innings": 1, "venue": 1, "competition": 1}
    )
    matches = sorted(cursor, key=lambda m: m.get("match_date") or "")
    state: dict[str, dict[str, _Rolling]] = defaultdict(lambda: defaultdict(_Rolling))
    venue_runs: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    samples: dict[str, list[tuple[list[float], int]]] = defaultdict(list)
    draws: dict[str, list[int]] = defaultdict(list)
    used = 0

    for match in matches:
        bucket = BUCKET_BY_MATCH_TYPE.get(match.get("match_type") or "", None)
        if bucket is None or len(match.get("teams") or []) != 2:
            continue
        home, away = match["teams"]
        teams = state[bucket]
        h, a = teams[home], teams[away]
        outcome = match.get("outcome") or {}
        winner = outcome.get("winner")
        is_draw = winner is None
        draws[bucket].append(1 if is_draw else 0)

        if not is_draw and winner in (home, away) and h.played >= 3 and a.played >= 3:
            features = [
                (h.elo - a.elo) / 100.0,
                h.form() - a.form(),
                (h.runs_rate() - a.runs_rate()) / 50.0,
            ]
            samples[bucket].append((features, 1 if winner == home else 0))
            used += 1

        # update rolling state after using pre-match features
        for innings in match.get("innings") or []:
            team = innings.get("team")
            runs = innings.get("runs")
            wkts = innings.get("wickets")
            if team in (home, away) and runs:
                teams[team].runs.append(float(runs))
                teams[team].wkts.append(float(wkts or 0))
                other = away if team == home else home
                teams[other].conceded.append(float(runs))
        first = (match.get("innings") or [{}])[0].get("runs")
        if first:
            venue_runs[match.get("venue") or "Unknown venue"][bucket].append(float(first))
        if not is_draw and winner in (home, away):
            loser = away if winner == home else home
            exp_home = 1 / (1 + 10 ** ((a.elo - h.elo) / 400))
            k = ELO_K.get(bucket, 20.0)
            delta = k * ((1 if winner == home else 0) - exp_home)
            h.elo += delta
            a.elo -= delta
            teams[winner].wins += 1
            teams[winner].recent.append(1)
            teams[loser].recent.append(0)
        else:
            h.recent.append(0.5)
            a.recent.append(0.5)
        h.played += 1
        a.played += 1

    formats: dict[str, dict] = {}
    for bucket, rows in samples.items():
        x = np.asarray([r[0] for r in rows], dtype=float)
        y = np.asarray([r[1] for r in rows], dtype=float)
        if x.shape[0] < 60:
            continue
        split = int(x.shape[0] * 0.8)
        mu, sigma = x[:split].mean(axis=0), np.maximum(x[:split].std(axis=0), 1e-6)
        w, b = _fit_logistic((x[:split] - mu) / sigma, y[:split])
        holdout = 1 / (1 + np.exp(-(((x[split:] - mu) / sigma) @ w + b)))
        all_runs = [v for team in state[bucket].values() for v in team.runs]
        arr = np.asarray(all_runs or [0.0], dtype=float)
        all_wkts = np.asarray([v for team in state[bucket].values() for v in team.wkts] or [0.0], dtype=float)
        formats[bucket] = {
            "coef": w.tolist(),
            "intercept": float(b),
            "mu": mu.tolist(),
            "sigma": sigma.tolist(),
            "train_samples": split,
            "metrics": _metrics(holdout, y[split:]),
            "draw_rate": round(float(np.mean(draws[bucket])) if draws[bucket] else 0.0, 4),
            "baseline_runs": round(float(arr.mean()), 1),
            "baseline_runs_sd": round(float(arr.std(ddof=1)) if arr.size > 1 else 25.0, 1),
            "baseline_wkts": round(float(all_wkts.mean()), 2),
            "baseline_wkts_sd": round(float(all_wkts.std(ddof=1)) if all_wkts.size > 1 else 2.0, 2),
        }

    teams_out: dict[str, dict] = defaultdict(dict)
    for bucket, teams in state.items():
        base = formats.get(bucket, {})
        fb_mean = base.get("baseline_runs", 160.0)
        fb_sd = base.get("baseline_runs_sd", 25.0)
        fb_wm = base.get("baseline_wkts", 6.0)
        fb_wsd = base.get("baseline_wkts_sd", 2.0)
        for name, roll in teams.items():
            runs_mean, runs_sd = _mean_std(roll.runs, fb_mean, fb_sd)
            wkts_mean, wkts_sd = _mean_std(roll.wkts, fb_wm, fb_wsd)
            conc_mean, _ = _mean_std(roll.conceded, fb_mean, fb_sd)
            teams_out[name][bucket] = {
                "elo": round(roll.elo, 1),
                "matches": roll.played,
                "win_rate": round(roll.wins / roll.played, 3) if roll.played else 0.5,
                "form": round(roll.form(), 3),
                "runs_mean": round(runs_mean, 1),
                "runs_sd": round(runs_sd, 1),
                "wkts_mean": round(wkts_mean, 2),
                "wkts_sd": round(wkts_sd, 2),
                "conceded_mean": round(conc_mean, 1),
            }

    venues_out = {
        venue: {bucket: {"mean_runs": round(float(np.mean(vals)), 1), "n": len(vals)}
                for bucket, vals in buckets.items() if len(vals) >= 5}
        for venue, buckets in venue_runs.items()
    }
    venues_out = {k: v for k, v in venues_out.items() if v}

    artifact = {
        "version": ARTIFACT_VERSION,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "matches_ingested": len(matches),
        "training_samples": used,
        "formats": formats,
        "teams": dict(teams_out),
        "venues": venues_out,
        "competitions": sorted({m.get("competition") for m in matches if m.get("competition")}),
    }
    db["model_artifacts"].replace_one({"version": ARTIFACT_VERSION}, artifact, upsert=True)
    return artifact


_CACHE: dict = {}


def load_artifact(db, force: bool = False) -> dict | None:
    if force or "artifact" not in _CACHE:
        doc = db["model_artifacts"].find_one({"version": ARTIFACT_VERSION}, {"_id": 0})
        _CACHE["artifact"] = doc
    return _CACHE.get("artifact")


def _team_stats(artifact: dict, team: str, bucket: str) -> dict | None:
    entry = (artifact.get("teams") or {}).get(team)
    return entry.get(bucket) if entry else None


def predict_fixture(artifact: dict | None, fmt: str, home: str, away: str, venue: str | None = None) -> dict:
    """Model-driven fixture priors. `data_quality` is HIGH/MEDIUM/LOW based on match coverage."""
    bucket = BUCKET_BY_FORMAT.get(fmt, "T20")
    result = {
        "bucket": bucket,
        "data_quality": "LOW",
        "matches": {"home": 0, "away": 0},
        "win": None,
        "draw_rate": None,
        "teams": {},
        "metrics": None,
        "trained_at": None,
        "reason": "No trained model artifact available",
    }
    if not artifact:
        return result
    fmt_model = (artifact.get("formats") or {}).get(bucket)
    home_stats = _team_stats(artifact, home, bucket)
    away_stats = _team_stats(artifact, away, bucket)
    result["trained_at"] = artifact.get("trained_at")
    result["metrics"] = (fmt_model or {}).get("metrics")
    result["draw_rate"] = (fmt_model or {}).get("draw_rate")
    hm = home_stats["matches"] if home_stats else 0
    am = away_stats["matches"] if away_stats else 0
    result["matches"] = {"home": hm, "away": am}

    if fmt_model:
        base_mean = fmt_model["baseline_runs"]
        base_sd = fmt_model["baseline_runs_sd"]
        base_wm = fmt_model["baseline_wkts"]
        base_wsd = fmt_model["baseline_wkts_sd"]
    else:
        base_mean, base_sd, base_wm, base_wsd = 160.0, 25.0, 6.0, 2.0

    venue_entry = ((artifact.get("venues") or {}).get(venue or "") or {}).get(bucket)
    venue_factor = 1.0
    if venue_entry and base_mean:
        venue_factor = max(0.85, min(1.15, venue_entry["mean_runs"] / base_mean))

    for side, stats in (("home", home_stats), ("away", away_stats)):
        mean = (stats["runs_mean"] if stats else base_mean) * venue_factor
        sd = stats["runs_sd"] if stats else base_sd
        result["teams"][side] = {
            "runs_mean": round(mean, 1),
            "runs_sd": round(sd, 1),
            "wkts_mean": stats["wkts_mean"] if stats else base_wm,
            "wkts_sd": stats["wkts_sd"] if stats else base_wsd,
            "elo": stats["elo"] if stats else 1500.0,
            "matches": stats["matches"] if stats else 0,
        }

    if fmt_model and home_stats and away_stats and min(hm, am) >= MIN_TEAM_MATCHES:
        features = np.asarray([
            (home_stats["elo"] - away_stats["elo"]) / 100.0,
            home_stats["form"] - away_stats["form"],
            (home_stats["runs_mean"] - away_stats["runs_mean"]) / 50.0,
        ])
        mu = np.asarray(fmt_model["mu"])
        sigma = np.asarray(fmt_model["sigma"])
        z = float(((features - mu) / sigma) @ np.asarray(fmt_model["coef"]) + fmt_model["intercept"])
        p_home = 1 / (1 + math.exp(-z))
        draw = fmt_model["draw_rate"] if bucket == "Test" else 0.0
        remaining = 1 - draw
        result["win"] = {"home": round(p_home * remaining, 4), "away": round((1 - p_home) * remaining, 4), "draw": round(draw, 4)}
        result["data_quality"] = "HIGH" if min(hm, am) >= 25 else "MEDIUM"
        result["reason"] = f"Trained on {fmt_model['train_samples']} {bucket} matches · {hm}/{am} team samples"
    else:
        missing = [t for t, m in ((home, hm), (away, am)) if m < MIN_TEAM_MATCHES]
        result["reason"] = (
            f"Insufficient historic {bucket} data for {', '.join(missing)}" if missing
            else f"No trained {bucket} model yet"
        )
    return result


if __name__ == "__main__":
    client = MongoClient(os.environ["MONGO_URL"], serverSelectionTimeoutMS=5000)
    out = build_and_train(client[os.environ["DB_NAME"]])
    print({"trained_at": out["trained_at"], "matches": out["matches_ingested"], "samples": out["training_samples"],
           "formats": {k: v["metrics"] for k, v in out["formats"].items()}, "teams": len(out["teams"])})

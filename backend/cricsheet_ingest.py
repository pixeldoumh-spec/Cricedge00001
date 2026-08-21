"""Cricsheet JSON importer and transparent chronological baseline backtest."""
from __future__ import annotations

import hashlib
import json
import os
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from io import BytesIO
from pathlib import PurePosixPath

import httpx
from pymongo import MongoClient, ASCENDING
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

ARCHIVE_URL = os.environ.get("CRICSHEET_ARCHIVE_URL", "https://cricsheet.org/downloads/ipl_json.zip")
DATA_VERSION = "cricsheet-ipl-json"


def _runs(innings: dict) -> tuple[int, int, int]:
    total = wickets = balls = 0
    for over in innings.get("overs", []):
        deliveries = over.get("deliveries", [])
        balls += len(deliveries)
        for delivery in deliveries:
            total += int(delivery.get("runs", {}).get("total", 0))
            wickets += len(delivery.get("wickets", []))
    return total, wickets, balls


def normalize_match(raw: dict, match_id: str, archive_hash: str, run_id: str) -> dict | None:
    info = raw.get("info", {})
    teams = info.get("teams", [])
    dates = info.get("dates", [])
    if len(teams) != 2 or not dates:
        return None
    event = info.get("event") or {}
    innings = []
    for item in raw.get("innings", []):
        runs, wickets, balls = _runs(item)
        innings.append({"team": item.get("team"), "runs": runs, "wickets": wickets, "balls": balls})
    return {
        "match_id": f"cricsheet:{match_id}",
        "source_match_id": match_id,
        "source": "Cricsheet",
        "source_url": ARCHIVE_URL,
        "archive_sha256": archive_hash,
        "data_version": raw.get("meta", {}).get("data_version"),
        "revision": raw.get("meta", {}).get("revision"),
        "match_date": str(dates[0]),
        "season": str(info.get("season", "")),
        "competition": event.get("name", "Indian Premier League"),
        "match_type": info.get("match_type", "T20"),
        "gender": info.get("gender", "unknown"),
        "teams": teams,
        "venue": info.get("venue", "Unknown venue"),
        "city": info.get("city"),
        "toss": info.get("toss", {}),
        "outcome": info.get("outcome", {}),
        "innings": innings,
        "ingestion_run_id": run_id,
    }


def _backtest(matches: list[dict]) -> dict:
    ordered = sorted(matches, key=lambda item: item["match_date"])
    wins = defaultdict(int)
    played = defaultdict(int)
    by_season = defaultdict(lambda: {"correct": 0, "total": 0})
    evaluated = []
    for match in ordered:
        winner = match.get("outcome", {}).get("winner")
        teams = match["teams"]
        if winner not in teams:
            continue
        rates = {team: (wins[team] / played[team] if played[team] else 0.5) for team in teams}
        predicted = max(teams, key=lambda team: rates[team])
        probability = rates[predicted]
        correct = predicted == winner
        season = match["season"]
        by_season[season]["correct"] += int(correct)
        by_season[season]["total"] += 1
        evaluated.append((probability, correct))
        for team in teams:
            played[team] += 1
        wins[winner] += 1
    total = len(evaluated)
    accuracy = sum(int(correct) for _, correct in evaluated) / total if total else 0
    brier = sum((probability - int(correct)) ** 2 for probability, correct in evaluated) / total if total else 1
    series = [{"month": season, "accuracy": round(values["correct"] / values["total"] * 100, 1), "calibration": round(max(0, 100 - brier * 100), 1)} for season, values in sorted(by_season.items())]
    markets = [{"name": "Match result", "samples": total, "accuracy": f"{accuracy * 100:.1f}%", "brier": f"{brier:.3f}"}]
    return {"metrics": {"accuracy": round(accuracy * 100, 1), "brier": round(brier, 3), "tracked": total, "calibration": round(max(0, 100 - brier * 100), 1)}, "series": series, "markets": markets, "dataset": "Cricsheet IPL JSON", "source": ARCHIVE_URL}


def ingest() -> dict:
    client = MongoClient(os.environ["MONGO_URL"], serverSelectionTimeoutMS=5000)
    db = client[os.environ["DB_NAME"]]
    collection = db["cricsheet_matches"]
    runs = db["cricsheet_ingestion_runs"]
    collection.create_index([("match_date", ASCENDING)])
    runs.create_index("archive_sha256", unique=True)
    run_id = datetime.now(timezone.utc).isoformat()
    with httpx.Client(timeout=120, follow_redirects=True) as http:
        response = http.get(ARCHIVE_URL)
        response.raise_for_status()
    archive = response.content
    archive_hash = hashlib.sha256(archive).hexdigest()
    normalized = []
    with zipfile.ZipFile(BytesIO(archive)) as bundle:
        for member in bundle.infolist():
            filename = PurePosixPath(member.filename)
            if member.is_dir() or filename.suffix != ".json" or filename.name != member.filename.split("/")[-1]:
                continue
            raw = json.loads(bundle.read(member))
            match = normalize_match(raw, filename.stem, archive_hash, run_id)
            if match:
                normalized.append(match)
    for match in normalized:
        collection.replace_one({"match_id": match["match_id"]}, match, upsert=True)
    summary = _backtest(normalized)
    run = {"run_id": run_id, "archive_sha256": archive_hash, "archive_url": ARCHIVE_URL, "inserted": len(normalized), "summary": summary, "created_at": run_id}
    runs.replace_one({"archive_sha256": archive_hash}, run, upsert=True)
    return {"run_id": run_id, "archive_sha256": archive_hash, "matches": len(normalized), "summary": summary}


if __name__ == "__main__":
    print(json.dumps(ingest(), indent=2))
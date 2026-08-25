"""Audit whether a CPL ball-by-ball corpus can reconstruct the market contract.

This is an audit, not a trainer. It never fits a model and never uses
bookmaker prices. Missing or ambiguous targets are counted explicitly.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from app.model.data.parser import iter_matches

CPL_NAMES = {
    "caribbean premier league",
    "caribbean premier league men",
    "cpl",
}


def event_name(info: dict[str, Any]) -> str:
    event = info.get("event") or {}
    if isinstance(event, dict):
        return str(event.get("name") or "")
    return str(event or "")


def is_cpl(info: dict[str, Any]) -> bool:
    name = event_name(info).strip().lower()
    return name in CPL_NAMES or "caribbean premier league" in name


def deliveries(match: dict[str, Any]):
    for innings_index, innings in enumerate(match.get("innings", [])):
        team = innings.get("team")
        for over in innings.get("overs", []):
            over_number = int(over.get("over", -1))
            for delivery in over.get("deliveries", []):
                yield innings_index, team, over_number, delivery


def innings_totals(match: dict[str, Any]):
    totals = []
    for innings in match.get("innings", []):
        runs = 0
        wickets = 0
        legal_balls = 0
        for over in innings.get("overs", []):
            for delivery in over.get("deliveries", []):
                extras = delivery.get("extras") or {}
                runs += int((delivery.get("runs") or {}).get("total", 0))
                wickets += len(delivery.get("wickets") or [])
                if not any(k in extras for k in ("wides", "noballs")):
                    legal_balls += 1
        totals.append({"team": innings.get("team"), "runs": runs, "wickets": wickets, "legal_balls": legal_balls})
    return totals


def target_status(match: dict[str, Any]) -> dict[str, Any]:
    info = match.get("info") or {}
    innings = match.get("innings") or []
    totals = innings_totals(match)
    status = {}

    outcome = info.get("outcome") or {}
    winner = outcome.get("winner")
    status["match_winner"] = bool(winner)
    status["super_over_metadata"] = bool(outcome.get("method") == "super over" or outcome.get("winner") and len(innings) > 2)

    pom = info.get("player_of_match")
    status["player_of_match"] = bool(pom)

    status["innings_totals"] = len(totals) >= 1 and all(t["team"] and t["legal_balls"] > 0 for t in totals)

    player_runs = defaultdict(int)
    player_balls = defaultdict(int)
    player_fours = defaultdict(int)
    player_sixes = defaultdict(int)
    bowler_wickets = Counter()
    team_fours = Counter()
    team_sixes = Counter()
    over_runs = defaultdict(int)

    for innings_index, team, over_number, delivery in deliveries(match):
        runs = delivery.get("runs") or {}
        batter = delivery.get("batter")
        player_runs[batter] += int(runs.get("batter", 0))
        extras = delivery.get("extras") or {}
        if not any(k in extras for k in ("wides", "noballs")):
            player_balls[batter] += 1
        if int(runs.get("batter", 0)) == 4:
            player_fours[batter] += 1
            team_fours[team] += 1
        if int(runs.get("batter", 0)) == 6:
            player_sixes[batter] += 1
            team_sixes[team] += 1
        over_runs[(innings_index, team, over_number)] += int(runs.get("total", 0))
        for wicket in delivery.get("wickets") or []:
            # A wicket belongs to the bowler except run-out/retired hurt/etc.
            kind = str(wicket.get("kind") or "").lower()
            if kind not in {"run out", "retired hurt", "retired out", "obstructing the field"}:
                bowler_wickets[delivery.get("bowler")] += 1

    status["player_runs"] = bool(player_runs)
    status["over_1_to_6"] = all(any(k[0] == i and k[2] == over for k in over_runs) for i in range(min(2, len(innings))) for over in range(0, 6))
    status["total_fours_sixes"] = bool(innings)
    status["top_batter"] = bool(player_runs)
    status["top_bowler"] = bool(bowler_wickets)
    status["most_fours"] = len(team_fours) >= 2
    status["most_sixes"] = len(team_sixes) >= 2

    # Team-top-player markets are derivable from the player distributions once
    # player identity and innings membership are reliable.
    status["team_top_batter_derivable"] = status["top_batter"] and len(totals) >= 2
    status["team_top_bowler_derivable"] = status["top_bowler"] and len(totals) >= 2

    return status


def audit(archive: Path) -> dict[str, Any]:
    counts = Counter()
    dates: list[str] = []
    competition_names = Counter()
    examples: dict[str, list[str]] = defaultdict(list)

    for index, match in enumerate(iter_matches(archive)):
        info = match.get("info") or {}
        if not is_cpl(info):
            continue
        match_id = str(match.get("meta", {}).get("data_version") or f"match-{index:06d}")
        date_values = info.get("dates") or []
        if date_values:
            dates.append(str(date_values[0]))
        competition_names[event_name(info)] += 1
        counts["cpl_matches"] += 1
        status = target_status(match)
        for key, ok in status.items():
            if ok:
                counts[key] += 1
            else:
                if len(examples[key]) < 5:
                    examples[key].append(match_id)

    result = {
        "corpus": str(archive),
        "cpl_match_count": counts["cpl_matches"],
        "earliest_date": min(dates) if dates else None,
        "latest_date": max(dates) if dates else None,
        "competition_names": competition_names,
        "target_coverage": {k: v for k, v in sorted(counts.items()) if k != "cpl_matches"},
        "missing_examples": dict(examples),
        "status": "audit_only_no_model_fit",
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.archive)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, default=lambda x: dict(x)) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, default=lambda x: dict(x)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

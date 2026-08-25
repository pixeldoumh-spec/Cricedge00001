"""Build the frozen CPL historical target corpus from Cricsheet JSON.

The builder is deliberately target-driven. It extracts only information needed
by the fixed CPL market contract and records source provenance for every row.
It does not fit models and does not use bookmaker prices.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Iterable


TARGETS = (
    "match_winner",
    "player_of_match",
    "team_innings_total",
    "player_innings_total",
    "first_innings_over_1_to_6",
    "total_fours",
    "total_sixes",
    "most_fours",
    "most_sixes",
    "team_top_batter",
    "team_top_bowler",
)

EXCLUDED_INFO_FIELDS = {
    "bookmaker_odds",
    "bookmaker_lines",
    "future_result",
}

NON_BOWLER_WICKET_KINDS = {
    "run out",
    "retired hurt",
    "retired out",
    "obstructing the field",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json_members(archive: Path) -> Iterable[tuple[str, dict[str, Any]]]:
    with zipfile.ZipFile(archive) as zf:
        for name in sorted(zf.namelist()):
            if not name.lower().endswith(".json"):
                continue
            with zf.open(name) as raw:
                yield name, json.load(raw)


def competition_name(info: dict[str, Any]) -> str:
    event = info.get("event") or {}
    if isinstance(event, dict):
        return str(event.get("name") or "")
    return str(event or "")


def is_cpl(info: dict[str, Any]) -> bool:
    return "caribbean premier league" in competition_name(info).lower()


def match_date(info: dict[str, Any]) -> str | None:
    values = info.get("dates") or []
    return str(values[0]) if values else None


def innings_stats(innings: dict[str, Any]) -> dict[str, Any]:
    team = innings.get("team")
    total_runs = 0
    total_fours = 0
    total_sixes = 0
    legal_balls = 0
    player_runs: Counter[str] = Counter()
    bowler_wickets: Counter[str] = Counter()
    over_runs: dict[int, int] = Counter()

    for over in innings.get("overs", []):
        over_no = int(over.get("over", -1))
        for d in over.get("deliveries", []):
            runs = d.get("runs") or {}
            total_runs += int(runs.get("total", 0))
            batter_runs = int(runs.get("batter", 0))
            batter = d.get("batter")
            if batter:
                player_runs[str(batter)] += batter_runs
            if batter_runs == 4:
                total_fours += 1
            elif batter_runs == 6:
                total_sixes += 1
            extras = d.get("extras") or {}
            if not any(k in extras for k in ("wides", "noballs")):
                legal_balls += 1
            over_runs[over_no] += int(runs.get("total", 0))
            for wicket in d.get("wickets") or []:
                kind = str(wicket.get("kind") or "").lower()
                if kind not in NON_BOWLER_WICKET_KINDS:
                    bowler = d.get("bowler")
                    if bowler:
                        bowler_wickets[str(bowler)] += 1

    return {
        "team": team,
        "runs": total_runs,
        "fours": total_fours,
        "sixes": total_sixes,
        "legal_balls": legal_balls,
        "player_runs": dict(player_runs),
        "bowler_wickets": dict(bowler_wickets),
        "over_runs": {str(k): v for k, v in sorted(over_runs.items())},
    }


def extract_match(member_name: str, match: dict[str, Any], source_sha: str) -> dict[str, Any] | None:
    info = match.get("info") or {}
    if not is_cpl(info):
        return None
    innings = [innings_stats(x) for x in match.get("innings", [])]
    teams = [x.get("team") for x in innings if x.get("team")]
    if len(teams) < 2:
        return None

    player_of_match = info.get("player_of_match") or []
    outcome = info.get("outcome") or {}
    team_fours = {x["team"]: x["fours"] for x in innings if x.get("team")}
    team_sixes = {x["team"]: x["sixes"] for x in innings if x.get("team")}

    # Player and team comparative targets are computed from completed historical
    # match outcomes only. These are labels, never features.
    all_player_runs: dict[str, int] = {}
    all_bowler_wickets: dict[str, int] = {}
    player_team: dict[str, str] = {}
    for x in innings:
        for p, runs in x["player_runs"].items():
            all_player_runs[p] = all_player_runs.get(p, 0) + runs
            player_team[p] = x["team"]
        for p, wickets in x["bowler_wickets"].items():
            all_bowler_wickets[p] = all_bowler_wickets.get(p, 0) + wickets

    top_batter = max(all_player_runs.values()) if all_player_runs else None
    top_bowl = max(all_bowler_wickets.values()) if all_bowler_wickets else None
    top_batter_players = sorted(p for p, v in all_player_runs.items() if v == top_batter) if top_batter is not None else []
    top_bowler_players = sorted(p for p, v in all_bowler_wickets.items() if v == top_bowl) if top_bowl is not None else []
    top_batter_teams = sorted({player_team[p] for p in top_batter_players})
    top_bowler_teams = sorted({player_team[p] for p in top_bowler_players})

    return {
        "source": {
            "provider": "Cricsheet",
            "format": "JSON",
            "archive_sha256": source_sha,
            "member": member_name,
        },
        "match": {
            "date": match_date(info),
            "teams": teams,
            "competition": competition_name(info),
            "venue": (info.get("venue") or None),
            "gender": info.get("gender"),
        },
        "labels": {
            "match_winner": outcome.get("winner"),
            "player_of_match": player_of_match,
            "innings": innings,
            "total_fours": sum(team_fours.values()),
            "total_sixes": sum(team_sixes.values()),
            "most_fours": {
                "leaders": sorted(k for k, v in team_fours.items() if v == max(team_fours.values())),
                "counts": team_fours,
            } if team_fours else None,
            "most_sixes": {
                "leaders": sorted(k for k, v in team_sixes.items() if v == max(team_sixes.values())),
                "counts": team_sixes,
            } if team_sixes else None,
            "team_top_batter": {"leaders": top_batter_teams, "players": top_batter_players, "runs": top_batter},
            "team_top_bowler": {"leaders": top_bowler_teams, "players": top_bowler_players, "wickets": top_bowl},
        },
        "quality": {
            "has_two_innings": len(innings) >= 2,
            "first_innings_has_six_overs": all(str(i) in innings[0]["over_runs"] for i in range(6)),
            "has_pom": bool(player_of_match),
            "has_winner": bool(outcome.get("winner")),
        },
    }


def build(archive: Path, output: Path) -> dict[str, Any]:
    source_sha = sha256(archive)
    rows = []
    seen = set()
    for member, match in read_json_members(archive):
        row = extract_match(member, match, source_sha)
        if row is None:
            continue
        key = (row["match"]["date"], tuple(row["match"]["teams"]), member)
        if key in seen:
            continue
        seen.add(key)
        rows.append(row)

    rows.sort(key=lambda r: (r["match"]["date"] or "", r["source"]["member"]))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    dates = [r["match"]["date"] for r in rows if r["match"]["date"]]
    return {
        "dataset": "cpl_outcome_labels_v0_1",
        "source_archive_sha256": source_sha,
        "rows": len(rows),
        "earliest_date": min(dates) if dates else None,
        "latest_date": max(dates) if dates else None,
        "targets": list(TARGETS),
        "bookmaker_prices_used": False,
        "sorted_chronologically": True,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    print(json.dumps(build(args.archive, args.output), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

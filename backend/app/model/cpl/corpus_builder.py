"""Build the frozen CPL historical target corpus from Cricsheet JSON."""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

TARGETS = ("match_winner", "player_of_match", "team_innings_total", "player_innings_total", "first_innings_over_1_to_6", "total_fours", "total_sixes", "most_fours", "most_sixes", "team_top_batter", "team_top_bowler")
NON_BOWLER_WICKET_KINDS = {"run out", "retired hurt", "retired out", "obstructing the field"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json_members(archive: Path) -> Iterable[tuple[str, dict[str, Any]]]:
    with zipfile.ZipFile(archive) as zf:
        for name in sorted(zf.namelist()):
            if name.lower().endswith(".json"):
                with zf.open(name) as raw:
                    yield name, json.load(raw)


def competition_name(info: dict[str, Any]) -> str:
    event = info.get("event") or {}
    return str(event.get("name") or "") if isinstance(event, dict) else str(event)


def is_cpl(info: dict[str, Any]) -> bool:
    return "caribbean premier league" in competition_name(info).lower()


def match_date(info: dict[str, Any]) -> str | None:
    dates = info.get("dates") or []
    return str(dates[0]) if dates else None


def innings_stats(innings: dict[str, Any]) -> dict[str, Any]:
    team = innings.get("team")
    total_runs = total_fours = total_sixes = legal_balls = 0
    player_runs: Counter[str] = Counter()
    bowler_wickets: Counter[str] = Counter()
    over_runs: Counter[int] = Counter()
    for over in innings.get("overs", []):
        over_no = int(over.get("over", -1))
        for d in over.get("deliveries", []):
            runs = d.get("runs") or {}
            total_runs += int(runs.get("total", 0))
            batter_runs = int(runs.get("batter", 0))
            if d.get("batter"):
                player_runs[str(d["batter"])] += batter_runs
            if batter_runs == 4: total_fours += 1
            elif batter_runs == 6: total_sixes += 1
            extras = d.get("extras") or {}
            if not any(k in extras for k in ("wides", "noballs")): legal_balls += 1
            over_runs[over_no] += int(runs.get("total", 0))
            for wicket in d.get("wickets") or []:
                kind = str(wicket.get("kind") or "").lower()
                if kind not in NON_BOWLER_WICKET_KINDS and d.get("bowler"):
                    bowler_wickets[str(d["bowler"])] += 1
    return {"team": team, "runs": total_runs, "fours": total_fours, "sixes": total_sixes, "legal_balls": legal_balls, "player_runs": dict(player_runs), "bowler_wickets": dict(bowler_wickets), "over_runs": {str(k): v for k, v in sorted(over_runs.items())}}


def extract_match(member_name: str, match: dict[str, Any], source_sha: str) -> dict[str, Any] | None:
    info = match.get("info") or {}
    if not is_cpl(info): return None
    innings = [innings_stats(x) for x in match.get("innings", [])]
    team_order = list(dict.fromkeys(x["team"] for x in innings if x.get("team")))
    if len(team_order) < 2: return None

    batting_runs: dict[str, int] = {}
    batting_team: dict[str, str] = {}
    bowling_wickets: dict[str, int] = {}
    bowling_team: dict[str, str] = {}
    for x in innings:
        bat_team = x["team"]
        bowl_team = next((t for t in team_order if t != bat_team), None)
        for p, runs in x["player_runs"].items():
            batting_runs[p] = batting_runs.get(p, 0) + runs
            batting_team[p] = bat_team
        for p, wickets in x["bowler_wickets"].items():
            bowling_wickets[p] = bowling_wickets.get(p, 0) + wickets
            bowling_team[p] = bowl_team

    def leaders(values: dict[str, int]):
        if not values: return [], None
        maximum = max(values.values())
        return sorted(k for k, v in values.items() if v == maximum), maximum

    top_batter_players, top_batter_runs = leaders(batting_runs)
    top_bowler_players, top_bowler_wickets = leaders(bowling_wickets)
    top_batter_teams = sorted({batting_team[p] for p in top_batter_players})
    top_bowler_teams = sorted({bowling_team[p] for p in top_bowler_players})
    team_fours = {x["team"]: x["fours"] for x in innings if x.get("team")}
    team_sixes = {x["team"]: x["sixes"] for x in innings if x.get("team")}

    return {
        "source": {"provider": "Cricsheet", "format": "JSON", "archive_sha256": source_sha, "member": member_name},
        "match": {"date": match_date(info), "teams": team_order, "competition": competition_name(info), "venue": info.get("venue"), "gender": info.get("gender")},
        "labels": {
            "match_winner": (info.get("outcome") or {}).get("winner"),
            "player_of_match": info.get("player_of_match") or [],
            "innings": innings,
            "total_fours": sum(team_fours.values()), "total_sixes": sum(team_sixes.values()),
            "most_fours": {"leaders": sorted(k for k, v in team_fours.items() if v == max(team_fours.values())), "counts": team_fours},
            "most_sixes": {"leaders": sorted(k for k, v in team_sixes.items() if v == max(team_sixes.values())), "counts": team_sixes},
            "team_top_batter": {"leaders": top_batter_teams, "players": top_batter_players, "runs": top_batter_runs},
            "team_top_bowler": {"leaders": top_bowler_teams, "players": top_bowler_players, "wickets": top_bowler_wickets},
        },
        "quality": {"has_two_innings": len(innings) >= 2, "first_innings_has_six_overs": bool(innings) and all(str(i) in innings[0]["over_runs"] for i in range(6)), "has_pom": bool(info.get("player_of_match")), "has_winner": bool((info.get("outcome") or {}).get("winner"))},
    }


def build(archive: Path, output: Path) -> dict[str, Any]:
    source_sha = sha256(archive)
    rows = []
    for member, match in read_json_members(archive):
        row = extract_match(member, match, source_sha)
        if row is not None: rows.append(row)
    rows.sort(key=lambda r: (r["match"]["date"] or "", r["source"]["member"]))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    dates = [r["match"]["date"] for r in rows if r["match"]["date"]]
    return {"dataset": "cpl_outcome_labels_v0_1", "source_archive_sha256": source_sha, "rows": len(rows), "earliest_date": min(dates) if dates else None, "latest_date": max(dates) if dates else None, "targets": list(TARGETS), "bookmaker_prices_used": False, "sorted_chronologically": True}


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--archive", type=Path, required=True); ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args(); print(json.dumps(build(args.archive, args.output), indent=2)); return 0

if __name__ == "__main__": raise SystemExit(main())

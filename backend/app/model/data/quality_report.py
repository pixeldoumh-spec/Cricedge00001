"""Generate a quality report from a Cricsheet JSON ZIP archive."""

from __future__ import annotations

import argparse
import json
import zipfile
from collections import Counter
from pathlib import Path

from .normalizer import normalize_match


def build_report(archive: Path) -> dict:
    matches = 0
    trainable = 0
    deliveries = 0
    innings = 0
    wickets = 0
    missing = Counter()
    seasons = Counter()
    competitions = Counter()
    teams = Counter()
    players = set()
    venues = set()
    result_types = Counter()
    gender = Counter()
    match_types = Counter()

    with zipfile.ZipFile(archive) as zf:
        names = [n for n in zf.namelist() if n.endswith(".json") and not n.endswith("/metadata.json")]
        for name in names:
            match_id = Path(name).stem
            with zf.open(name) as handle:
                raw = json.load(handle)
            match = normalize_match(match_id, raw)
            matches += 1
            trainable += int(
                match.match_type == "T20"
                and len(match.teams) == 2
                and match.winner in match.teams
                and match.gender == "male"
            )
            deliveries += len(match.deliveries)
            innings += len({d.innings for d in match.deliveries})
            wickets += sum(d.wicket for d in match.deliveries)
            seasons[str(match.season)] += 1
            competitions[match.competition or "<missing>"] += 1
            gender[match.gender or "<missing>"] += 1
            match_types[match.match_type or "<missing>"] += 1
            result_types[match.result_type or "<missing>"] += 1
            teams.update(match.teams)
            venues.add(match.venue or "<missing>")
            for roster in match.players.values():
                players.update(p.registry_id or p.name for p in roster)
            for field, value in {
                "venue": match.venue,
                "city": match.city,
                "season": match.season,
                "competition": match.competition,
                "toss_winner": match.toss_winner,
                "toss_decision": match.toss_decision,
                "winner": match.winner,
            }.items():
                if value is None:
                    missing[field] += 1

    return {
        "archive": str(archive),
        "matches": matches,
        "trainable_t20_matches": trainable,
        "innings": innings,
        "deliveries": deliveries,
        "wickets": wickets,
        "unique_players": len(players),
        "unique_teams": len(teams),
        "unique_venues": len(venues),
        "seasons": dict(sorted(seasons.items())),
        "competitions": dict(competitions),
        "teams": dict(teams),
        "result_types": dict(result_types),
        "gender": dict(gender),
        "match_types": dict(match_types),
        "missing_fields": dict(missing),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Report quality of Cricsheet T20 JSON data")
    parser.add_argument(
        "archive",
        type=Path,
        nargs="?",
        default=Path("backend/data/raw/cricsheet/t20s_json.zip"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("backend/data/reports/t20_quality.json"),
    )
    args = parser.parse_args()
    report = build_report(args.archive)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote quality report: {args.output}")


if __name__ == "__main__":
    main()

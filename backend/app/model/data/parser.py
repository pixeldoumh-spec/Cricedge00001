"""Cricsheet JSON archive parser and schema inspection helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator
from zipfile import ZipFile


def iter_matches(archive: Path) -> Iterator[dict[str, Any]]:
    """Yield match JSON objects from a Cricsheet archive."""
    with ZipFile(archive) as bundle:
        for name in sorted(bundle.namelist()):
            if not name.endswith(".json"):
                continue
            with bundle.open(name) as raw:
                yield json.load(raw)


def inspect_match(match: dict[str, Any]) -> dict[str, Any]:
    """Return a compact structural summary without transforming match data."""
    info = match.get("info", {})
    innings = match.get("innings", [])
    delivery_count = sum(
        len(over.get("deliveries", []))
        for inning in innings
        for over in inning.get("overs", [])
    )

    return {
        "meta_keys": sorted(match.get("meta", {}).keys()),
        "info_keys": sorted(info.keys()),
        "teams": info.get("teams", []),
        "match_type": info.get("match_type"),
        "gender": info.get("gender"),
        "dates": info.get("dates", []),
        "venue": info.get("venue"),
        "toss_keys": sorted(info.get("toss", {}).keys()),
        "outcome_keys": sorted(info.get("outcome", {}).keys()),
        "innings": len(innings),
        "delivery_count": delivery_count,
        "registry_present": "registry" in info,
        "players_present": "players" in info,
    }


def inspect_first_match(archive: Path) -> dict[str, Any]:
    """Inspect the first JSON match in an archive."""
    try:
        match = next(iter_matches(archive))
    except StopIteration as exc:
        raise ValueError("Cricsheet archive contains no JSON match files") from exc
    return inspect_match(match)

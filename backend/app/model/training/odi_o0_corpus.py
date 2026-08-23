"""Locked men's ODI corpus ingestion for the canonical O0 pipeline."""
from __future__ import annotations

from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List
import zipfile

LOCKED_CORPUS_SHA256 = "f0798ef14e1f3f61720d41978289fe7318257263f59edba5dca0b35dbba64d6c"
EXPECTED_ARCHIVE_JSON_FILES = 2569
EXPECTED_DECISIVE_ROWS = 2440


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_locked_matches(path: str | Path) -> List[Dict[str, Any]]:
    """Load and deterministically order the exact locked Cricsheet archive."""
    path = Path(path)
    actual = sha256_file(path)
    if actual != LOCKED_CORPUS_SHA256:
        raise ValueError(f"locked ODI corpus SHA-256 mismatch: {actual}")
    matches: List[Dict[str, Any]] = []
    with zipfile.ZipFile(path) as archive:
        names = [n for n in archive.namelist() if n.endswith(".json")]
        if len(names) != EXPECTED_ARCHIVE_JSON_FILES:
            raise ValueError(f"expected {EXPECTED_ARCHIVE_JSON_FILES} JSON matches, got {len(names)}")
        for name in names:
            match = json.loads(archive.read(name))
            match["_match_id"] = Path(name).stem
            matches.append(match)
    matches.sort(key=lambda m: (date.fromisoformat(str(m["info"]["dates"][0])), str(m["_match_id"])))
    return matches


def build_locked_o0_rows(path: str | Path) -> List[Dict[str, Any]]:
    from .odi_o0_features import build_feature_rows
    rows = build_feature_rows(load_locked_matches(path))
    if len(rows) != EXPECTED_DECISIVE_ROWS:
        raise ValueError(f"expected {EXPECTED_DECISIVE_ROWS} decisive rows, got {len(rows)}")
    return rows

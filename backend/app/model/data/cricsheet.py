"""Cricsheet download boundary.

Cricsheet JSON is the canonical historical match source for the first CricEdge
model. Raw archives are downloaded outside the source tree and are never
committed to Git.
"""

from __future__ import annotations

from pathlib import Path
from urllib.request import urlopen

CRICSHEET_T20_JSON_URL = "https://cricsheet.org/downloads/t20s_json.zip"


def download_t20_archive(destination: Path, *, url: str = CRICSHEET_T20_JSON_URL) -> Path:
    """Download the official Cricsheet T20 JSON archive to *destination*."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(url, timeout=60) as response, destination.open("wb") as output:
        output.write(response.read())
    return destination

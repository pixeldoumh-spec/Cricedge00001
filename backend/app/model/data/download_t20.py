"""Download the official Cricsheet T20 JSON archive.

Usage:
    python -m app.model.data.download_t20
    python -m app.model.data.download_t20 --output backend/data/raw/cricsheet
"""

from __future__ import annotations

import argparse
from pathlib import Path
from urllib.request import urlopen

# Official Cricsheet JSON archive for T20 internationals.
T20_JSON_URL = "https://cricsheet.org/downloads/t20s_json.zip"


def download(url: str, output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(url) as response, output.open("wb") as handle:
        while chunk := response.read(1024 * 1024):
            handle.write(chunk)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Download Cricsheet T20 JSON data")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("backend/data/raw/cricsheet/t20s_json.zip"),
    )
    parser.add_argument("--url", default=T20_JSON_URL)
    args = parser.parse_args()
    path = download(args.url, args.output)
    print(f"Downloaded Cricsheet T20 archive: {path}")


if __name__ == "__main__":
    main()

"""Fetch and freeze the official Cricsheet men's CPL JSON archive.

The archive is deliberately stored outside git. This script records its
cryptographic identity and basic file inventory in a manifest so every model
run can be reproduced against the same source snapshot.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_URL = "https://cricsheet.org/downloads/cpl_json.zip"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(args.url, args.output)

    with zipfile.ZipFile(args.output) as archive:
        members = [m for m in archive.namelist() if m.lower().endswith(".json")]
        bad = [m for m in members if Path(m).name != Path(m).name.strip()]
        manifest = {
            "source_url": args.url,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "archive": str(args.output),
            "archive_sha256": sha256(args.output),
            "json_member_count": len(members),
            "json_members_sha256": {
                m: hashlib.sha256(archive.read(m)).hexdigest() for m in members
            },
            "zip_validation": {"readable": True, "suspicious_member_names": bad},
            "status": "frozen_source_snapshot",
        }

    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

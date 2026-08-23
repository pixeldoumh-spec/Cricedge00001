#!/usr/bin/env python3
"""Execute an ODI experiment runner and register a reproducibility manifest.

The runner is intentionally external to the provenance layer. An experiment
must provide a deterministic command that consumes the locked corpus and
writes its complete result artifact. This wrapper hashes the corpus, source
files, runner output, and repository revision after execution.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from backend.app.model.training.odi_provenance import (
    assert_locked_corpus,
    build_manifest,
    write_manifest,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", required=True)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--result", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--protocol", required=True, help="JSON protocol file")
    parser.add_argument("--source", action="append", required=True)
    parser.add_argument("--runner", required=True, help="Deterministic experiment command")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    corpus = Path(args.corpus).resolve()
    result = Path(args.result).resolve()
    protocol_path = Path(args.protocol).resolve()

    assert_locked_corpus(corpus)
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))

    completed = subprocess.run(args.runner, cwd=repo_root, shell=True, check=False)
    if completed.returncode != 0:
        print(f"experiment runner failed with exit code {completed.returncode}", file=sys.stderr)
        return completed.returncode
    if not result.exists():
        print(f"runner completed but result artifact is missing: {result}", file=sys.stderr)
        return 2

    manifest = build_manifest(
        experiment=args.experiment,
        repo_root=repo_root,
        corpus_path=corpus,
        runner_command=args.runner,
        source_paths=args.source,
        result_path=result,
        protocol=protocol,
        status="completed_reproducible_run",
    )
    write_manifest(manifest, args.manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

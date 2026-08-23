"""Provenance primitives for locked men's ODI experiments.

This module deliberately does not make modeling decisions. It records the exact
inputs, source files, runner command, repository revision, and result hash used
by an ODI experiment so a result can be reproduced and audited later.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Iterable, Mapping


LOCKED_CORPUS_SHA256 = "f0798ef14e1f3f61720d41978289fe7318257263f59edba5dca0b35dbba64d6c"
LOCKED_DECISIVE_ROWS = 2440
LOCKED_CHRONOLOGICAL_FINGERPRINT = "2b04bca99fabde61f33f7dc9d265b797a58a36f7fb1725a2671186e764da2f64"


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_json(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(encoded)


def git_revision(cwd: str | Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=str(cwd), text=True
    ).strip()


def git_dirty(cwd: str | Path) -> bool:
    return bool(subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=str(cwd), text=True
    ).strip())


def source_hashes(repo_root: str | Path, paths: Iterable[str]) -> dict[str, str]:
    root = Path(repo_root)
    return {path: sha256_file(root / path) for path in paths}


def assert_locked_corpus(path: str | Path) -> None:
    actual = sha256_file(path)
    if actual != LOCKED_CORPUS_SHA256:
        raise ValueError(
            f"locked ODI corpus hash mismatch: expected {LOCKED_CORPUS_SHA256}, got {actual}"
        )


def build_manifest(
    *,
    experiment: str,
    repo_root: str | Path,
    corpus_path: str | Path,
    runner_command: str,
    source_paths: Iterable[str],
    result_path: str | Path,
    protocol: Mapping[str, Any],
    status: str,
) -> dict[str, Any]:
    root = Path(repo_root)
    corpus = Path(corpus_path)
    result = Path(result_path)
    manifest: dict[str, Any] = {
        "schema_version": "odi_provenance_v1",
        "experiment": experiment,
        "status": status,
        "repository": {
            "revision": git_revision(root),
            "dirty_worktree": git_dirty(root),
        },
        "corpus": {
            "path": str(corpus),
            "sha256": sha256_file(corpus),
            "expected_sha256": LOCKED_CORPUS_SHA256,
            "decisive_rows": LOCKED_DECISIVE_ROWS,
            "chronological_fingerprint": LOCKED_CHRONOLOGICAL_FINGERPRINT,
        },
        "runner": {"command": runner_command},
        "source_files": source_hashes(root, source_paths),
        "result": {
            "path": str(result),
            "sha256": sha256_file(result),
        },
        "protocol": dict(protocol),
    }
    if manifest["corpus"]["sha256"] != LOCKED_CORPUS_SHA256:
        raise ValueError("result cannot be registered against an unlocked corpus")
    return manifest


def write_manifest(manifest: Mapping[str, Any], path: str | Path) -> None:
    Path(path).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

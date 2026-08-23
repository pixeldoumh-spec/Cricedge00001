from pathlib import Path

import pytest

from backend.app.model.training.odi_provenance import (
    LOCKED_CORPUS_SHA256,
    sha256_bytes,
    sha256_json,
)


def test_sha256_bytes_is_deterministic():
    assert sha256_bytes(b"cricedge") == sha256_bytes(b"cricedge")
    assert sha256_bytes(b"cricedge") != sha256_bytes(b"cricedge2")


def test_sha256_json_is_key_order_independent():
    assert sha256_json({"a": 1, "b": 2}) == sha256_json({"b": 2, "a": 1})


def test_locked_corpus_contract_is_pinned():
    assert len(LOCKED_CORPUS_SHA256) == 64
    assert all(char in "0123456789abcdef" for char in LOCKED_CORPUS_SHA256)


def test_missing_corpus_is_not_silently_accepted(tmp_path: Path):
    from backend.app.model.training.odi_provenance import assert_locked_corpus

    with pytest.raises(FileNotFoundError):
        assert_locked_corpus(tmp_path / "missing.zip")

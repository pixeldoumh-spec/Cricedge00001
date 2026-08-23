"""Versioned fingerprints for canonical ODI supervised feature rows."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

LEGACY_V0_ALGORITHM = "sha256(canonical_json(rows))"
LEGACY_V0_EXPECTED = "a64c5b01d338b08e018c92bf34c30355e41a380ba0209f190fad457bccc60d42"


def fingerprint_legacy_v0(rows: Sequence[Mapping[str, Any]]) -> str:
    """Reconstructed legacy_v0 fingerprint.

    Serialization: complete supervised rows, JSON encoded with sorted keys,
    compact separators, UTF-8, NaN disallowed; then SHA-256.
    """
    payload = json.dumps(
        list(rows), separators=(",", ":"), sort_keys=True, allow_nan=False
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def fingerprint_v1(rows: Sequence[Mapping[str, Any]]) -> str:
    """Canonical v1 fingerprint; currently identical serialization to v0.

    v1 is a formally specified contract and is intentionally versioned so its
    serialization can evolve only through an explicit contract change.
    """
    return fingerprint_legacy_v0(rows)

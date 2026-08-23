"""Reproducible ODI feature-row fingerprints.

These identifiers are provenance contracts, not model versions. In particular,
do not use the repository's T20 V0/V1 terminology here.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

ODI_LEGACY_FEATURE_FINGERPRINT_ALGORITHM = "sha256(canonical_json(rows))"
ODI_LEGACY_FEATURE_FINGERPRINT_EXPECTED = "a64c5b01d338b08e018c92bf34c30355e41a380ba0209f190fad457bccc60d42"


def fingerprint_odi_legacy(rows: Sequence[Mapping[str, Any]]) -> str:
    """Reconstructed legacy ODI fingerprint.

    Serialization: complete supervised rows, JSON encoded with sorted keys,
    compact separators, UTF-8, NaN disallowed; then SHA-256.
    """
    payload = json.dumps(
        list(rows), separators=(",", ":"), sort_keys=True, allow_nan=False
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def fingerprint_odi_canonical(rows: Sequence[Mapping[str, Any]]) -> str:
    """Canonical ODI provenance fingerprint.

    The current canonical contract intentionally preserves the exact bytes of
    the reconstructed legacy fingerprint. It is an ODI provenance contract,
    not a model version.
    """
    return fingerprint_odi_legacy(rows)

# ODI Feature-Row Fingerprint Provenance

## Finding

The legacy O0 report contains fingerprint `a64c5b01d338b08e018c92bf34c30355e41a380ba0209f190fad457bccc60d42`, but Git history/code search did not locate the original hashing implementation. The repository's reconstructed O0 runner independently reproduced that exact value using the algorithm below.

Therefore `legacy_v0` is **reconstructed and hash-validated**, not historically recovered from an original source implementation.

## legacy_v0

Algorithm:

1. Take the complete supervised O0 rows in canonical chronological order.
2. Serialize the complete row objects as JSON.
3. Use `sort_keys=True`.
4. Use compact separators `(',', ':')`.
5. Use UTF-8 encoding.
6. Set `allow_nan=False`.
7. SHA-256 the resulting UTF-8 bytes.

Expected hash for the locked 2,440-row O0 population:

`a64c5b01d338b08e018c92bf34c30355e41a380ba0209f190fad457bccc60d42`

Implementation: `backend/app/model/training/odi_feature_fingerprint.py`.

## v1

`v1` is now the formally specified provenance contract. It currently uses the same byte serialization as `legacy_v0`, but it is versioned independently so future changes cannot silently alter the fingerprint semantics.

All future O12/O14 reproducibility artifacts must record:

- fingerprint version (`v1`)
- fingerprint value
- locked corpus SHA-256
- chronological fingerprint
- source-file hashes
- runner commit
- result-artifact SHA-256

## Status

- Legacy value: exact match reproduced.
- Original historical implementation: not found in searchable Git history/code.
- legacy_v0: reconstructed + hash-validated.
- v1: frozen for future experiments.

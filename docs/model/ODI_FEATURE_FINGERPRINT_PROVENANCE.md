# ODI Feature-Row Fingerprint Provenance

## Legacy O0 fingerprint

The frozen O0 report contains fingerprint:

`a64c5b01d338b08e018c92bf34c30355e41a380ba0209f190fad457bccc60d42`

Git history/code search did not recover the original historical hashing source. The exact legacy value was nevertheless independently reproduced from the locked 2,440-row O0 population.

The reconstructed serialization is:

1. complete supervised O0 rows in canonical chronological order;
2. JSON serialization of the complete row objects;
3. `sort_keys=True`;
4. compact separators `(',', ':')`;
5. UTF-8 encoding;
6. `allow_nan=False`;
7. SHA-256 of the resulting bytes.

**Provenance status:** reconstructed and hash-validated; historical source implementation not recovered.

## Canonical ODI fingerprint

Future ODI reproducibility artifacts use the explicit name **ODI canonical feature fingerprint**. It is not a model version and does not use the repository's T20 V0/V1 terminology.

The current canonical serialization is intentionally identical to the reconstructed legacy serialization so the locked O0 population remains byte-compatible. Any future serialization change must be introduced as an explicit ODI fingerprint-contract revision, without reusing T20 model-version identifiers.

Future O12/O14 artifacts must record:

- locked corpus SHA-256;
- canonical chronological ordering;
- ODI feature fingerprint value;
- source Git revision/blob identifiers;
- runner command;
- protocol identifier;
- result-artifact SHA-256.

## Namespace rule

- **T20 V0/V1:** existing T20 model lineage; unchanged.
- **ODI O0/O12/O14:** ODI experiment lineage.
- **ODI legacy feature fingerprint / ODI canonical feature fingerprint:** provenance identifiers only; never model versions.

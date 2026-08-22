# Model v0 artifact

This directory is the versioned runtime artifact boundary for the verified,
frozen Model v0.

Required runtime files:

- `model.joblib` — fitted StandardScaler + LogisticRegression estimator.
- `calibrator.joblib` — validation-only Platt calibrator.
- `metadata.json` — immutable model/data/evaluation contract.

The binary artifacts are intentionally not generated or committed from the
GitHub connector. They must be built from the verified corpus using the
repository's artifact-builder command, then checksummed and deployed as a
matched set with `metadata.json`.

The acceptance test has already verified the canonical 13-feature contract and
3,411-match chronological 2,387/511/513 experiment before artifact creation.

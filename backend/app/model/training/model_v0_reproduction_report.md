# Model v0 exact reproduction report

## Acceptance test

The canonical 13-feature implementation was executed against the uploaded Cricsheet T20 archive.

- Population: men's T20, exactly two teams, known winner
- Rows: **3,411**
- Chronological ordering: `date` ascending, matching the canonical feature builder
- Split: **2,387 train / 511 validation / 513 test**
- Base estimator: `StandardScaler + LogisticRegression(max_iter=2000)`
- Features: exact canonical 13-feature contract
- Calibration: validation-only Platt scaling on logit-transformed validation probabilities, `LogisticRegression(max_iter=2000)`
- Test set: never used for fitting model or calibrator

## Exact test reproduction

| Metric | Recorded frozen-v0 | Reproduced | Absolute difference |
|---|---:|---:|---:|
| Accuracy (calibrated) | 69.20% | **69.20%** | 0.00000 pp |
| Log loss (calibrated) | 0.58121 | **0.58121235** | < 0.00001 |
| Brier score (calibrated) | 0.19722 | **0.19722380** | < 0.00001 |
| ROC AUC (calibrated) | 0.76851 | **0.76850698** | < 0.00001 |
| 10-bin ECE (calibrated) | 0.04980 | **0.04980010** | < 0.00001 |

The uncalibrated test metrics also reproduce the recorded values:

- Accuracy: **69.785575%**
- Log loss: **0.58865063**
- Brier score: **0.20103854**

## Integrity fingerprints

- Feature-row CSV SHA-256: `9bb8a33338a7876a03490ff865079ca6c6bc8a6d8326763f85443aad27cbecaf`
- Chronological match-id sequence SHA-256: `a29e2ada9a28f7daab8479472ee5c988dc824069a65d3df1eadc79f57f73ae69`

## Result

**PASS.** The canonical 13-feature implementation reproduces the recorded frozen Model v0 evaluation within numerical tolerance. The model artifact can now be serialized without changing the feature contract, split protocol, estimator, or calibration procedure.

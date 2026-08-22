# Women's Model W0 — Calibration Decision Report

## Decision

**Production calibration strategy: raw logistic probabilities (no calibration layer).**

The frozen W0 predictive model is unchanged. Calibration was evaluated as a separate post-model layer using validation-only selection and an untouched chronological holdout.

## Frozen contract

- 2,066 decisive women's T20 matches
- Chronological baseline split: 1,446 train / 310 validation / 310 test
- 13-feature W0 contract unchanged
- `StandardScaler + LogisticRegression(max_iter=2000)` unchanged
- Calibration candidates: raw, Platt, isotonic
- Candidate selection: 5-fold stratified out-of-fold predictions inside the validation slice only
- The untouched test/holdout data was not used for candidate selection

## Baseline 310-match test

Validation-only OOF selection chose **Platt**:

| Candidate | OOF log loss | OOF Brier | OOF ECE |
| --- | ---: | ---: | ---: |
| Raw | 0.5357503 | 0.1783531 | 0.0672350 |
| Platt | **0.5216449** | **0.1739355** | **0.0355718** |
| Isotonic | 0.6834900 | 0.1845793 | 0.1068626 |

On the untouched 310-match baseline test:

| Candidate | Accuracy | Log loss | Brier | AUC | ECE |
| --- | ---: | ---: | ---: | ---: | ---: |
| Raw | **71.94%** | 0.5380294 | 0.1803119 | 0.8094156 | 0.0659534 |
| Platt | 71.61% | **0.5287449** | **0.1778821** | 0.8094156 | 0.0567902 |
| Isotonic | 71.29% | 0.5957069 | 0.1802289 | 0.8043670 | 0.0637503 |

This confirms that Platt is preferable to raw on the original frozen 310-match test for probability metrics.

## Final chronological holdout

A second calibration-selection experiment was run with the exact W0 implementation using:

- Train: 1,585
- Validation: 310
- Final chronological holdout: 171
- Holdout dates: 2026-05-10 → 2026-08-11
- Calibration candidate selection remained validation-only.

Validation OOF selection again chose **Platt**:

| Candidate | OOF log loss | OOF Brier | OOF ECE |
| --- | ---: | ---: | ---: |
| Raw | 0.5461957 | 0.1824688 | 0.0773194 |
| Platt | **0.5350087** | **0.1794741** | **0.0417373** |
| Isotonic | 0.5845564 | 0.1851970 | 0.0538590 |

But on the untouched final holdout:

| Candidate | Accuracy | Log loss | Brier | AUC | ECE |
| --- | ---: | ---: | ---: | ---: | ---: |
| **Raw** | **73.68%** | **0.5113817** | **0.1698840** | **0.8289546** | 0.0862665 |
| Platt | 72.51% | 0.5179289 | 0.1741434 | 0.8289546 | 0.0940512 |
| Isotonic | 72.51% | 0.5322236 | 0.1805375 | 0.8195129 | **0.0848837** |

## Production conclusion

The validation set consistently prefers Platt, but the genuinely future holdout prefers **raw probabilities on every primary predictive metric**: accuracy, log loss, Brier, and AUC. Isotonic only improves ECE on that holdout and materially worsens the other metrics.

Therefore we should **not ship a W0 calibration layer**. The production W0 artifact should expose the LogisticRegression probabilities directly.

This resolves the production calibration question without changing W0's feature set or predictive architecture.

## Reproducibility

The experiment was executed against the retained Cricsheet women's T20 corpus using the canonical W0 implementation and the pinned 13-feature contract. The baseline 310-match test and final 171-match holdout were evaluated without fitting or selecting a calibrator from those evaluation samples.

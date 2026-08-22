# Women's Model W0 — Final Evaluation Decision Report

## Scope

W0 is evaluated as a separate women's T20 model. The men's Model v0 remains frozen and is not modified by this experiment.

## Frozen baseline contract

- Population: 2,114 women's T20 matches in the retained corpus.
- Decisive matches: 2,066.
- Chronological baseline split: 1,446 train / 310 validation / 310 test.
- Feature contract: the frozen 13-feature v0 contract, applied to the women's corpus.
- Estimator: `StandardScaler + LogisticRegression(max_iter=2000)`.
- Calibration: `ValidationPlattCalibrator`, fitted only on the validation slice.
- The 310-match baseline test set is never used for fitting or calibration.

## Reproduced W0 baseline

The canonical implementation reproduced the recorded W0 baseline on the untouched 310-match test set:

| Metric | Calibrated W0 |
| --- | ---: |
| Accuracy | 71.6129% |
| Log loss | 0.5287449 |
| Brier | 0.1778821 |
| ROC AUC | 0.8094156 |
| 10-bin ECE | 0.0567902 |

## Rolling-origin robustness

Executed five expanding windows with validation-only calibration. The results are reasonably stable across the windows, with expected chronological variation and no evidence of catastrophic regime failure.

| Train fraction | Accuracy | Log loss | Brier | AUC | ECE |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 50% | 77.18% | 0.5200 | 0.1712 | 0.8164 | 0.0907 |
| 55% | 71.36% | 0.5600 | 0.1895 | 0.7814 | 0.0577 |
| 60% | 78.16% | 0.5029 | 0.1645 | 0.8332 | 0.0775 |
| 65% | 75.24% | 0.5184 | 0.1715 | 0.8263 | 0.0699 |
| 70% | 71.36% | 0.5471 | 0.1831 | 0.7987 | 0.0929 |

Mean across the five windows:

- Accuracy: 74.66%
- Log loss: 0.52966
- Brier: 0.17595
- AUC: 0.81121
- ECE: 0.07773

## Time-regime diagnostic

| Period | Accuracy | Log loss | Brier | AUC |
| --- | ---: | ---: | ---: | ---: |
| Middle | 70.06% | 0.5779 | 0.1964 | 0.7681 |
| Newer | 72.75% | 0.5328 | 0.1778 | 0.8130 |

The newer regime is stronger than the middle regime in this diagnostic; there is no evidence of recent-regime collapse.

## Competition and team-history diagnostics

Competition and team-history diagnostics were completed by the harness. A reliable home/away field is not available in `CanonicalMatch`, so no home advantage was inferred from venue.

## Final chronological holdout

The committed harness was executed against the retained Cricsheet archive after correcting the harness to assert the exact frozen 1,446/310/310 split rather than deriving it through integer rounding.

The final temporal holdout contains the last 171 decisive matches:

- Train: 1,585
- Validation: 310
- Holdout: 171
- Holdout dates: 2026-05-10 → 2026-08-11
- Calibration was fitted only on the preceding 310-match validation slice.
- The frozen 310-match baseline test set was not used for fitting or calibration.

### Final holdout — calibrated W0

| Metric | Baseline 310-test | Final 171 holdout |
| --- | ---: | ---: |
| Accuracy | 71.6129% | **72.5146%** |
| Log loss | 0.5287449 | **0.5179289** |
| Brier | 0.1778821 | **0.1741434** |
| ROC AUC | 0.8094156 | **0.8289546** |
| 10-bin ECE | 0.0567902 | 0.0940512 |

### Calibration check

On the final holdout, the uncalibrated logistic model scored:

- Accuracy: 73.6842%
- Log loss: 0.5113817
- Brier: 0.1698840
- AUC: 0.8289546
- ECE: 0.0862665

Validation-only Platt calibration therefore **did not improve the final holdout**: it reduced accuracy and increased log loss, Brier, and ECE, while leaving AUC unchanged.

## Decision

**W0 implementation: FROZEN AS THE WOMEN'S REFERENCE BASELINE.**

**W0 calibrated model: NOT PROMOTED TO PRODUCTION YET.**

The predictive model itself shows credible robustness: rolling-origin results are stable and the final chronological holdout improves accuracy, log loss, Brier, and AUC relative to the recorded baseline test metrics. However, the validation-only calibration does not survive the final holdout. Because probability quality is central to this prediction system, that calibration instability is sufficient reason not to promote the calibrated W0 artifact yet.

Any future W1 work should therefore be motivated specifically by calibration robustness or another clearly justified architectural improvement, not by subgroup weakness. No changes are made to men's v0.

## Reproducibility

These final holdout results were generated from the retained Cricsheet archive using the canonical W0 feature/training implementation and the pinned robustness harness. The harness now asserts the exact 1,446/310/310 contract and contains the final holdout and subgroup evaluation paths.

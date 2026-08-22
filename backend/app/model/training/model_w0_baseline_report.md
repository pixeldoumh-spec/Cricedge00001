# Women's T20 Model W0 baseline report

## Status

**Baseline established.** W0 is not yet promoted or frozen as a production model.

## Exact experiment

The baseline was executed against the retained T20 corpus using the committed W0 implementation at commit `52b94d75`.

- Population: women's T20
- Total women's T20 matches: 2,114
- Decisive matches used for supervised learning: 2,066
- Excluded: 35 no-results and 13 ties
- Chronological split: 1,446 train / 310 validation / 310 test
- First eligible match: 2009-06-18
- Last eligible match: 2026-08-11
- Features: exact canonical 13-feature v0 contract
- Estimator: `StandardScaler + LogisticRegression(max_iter=2000)`
- Calibration: Platt calibration using validation predictions only
- Test set: untouched during fitting and calibration

## Class balance

| Split | Matches | Home/team-positive rate |
|---|---:|---:|
| Train | 1,446 | 50.21% |
| Validation | 310 | 55.16% |
| Test | 310 | 55.16% |

## Calibrated test-set baseline

| Metric | W0 |
|---|---:|
| Accuracy | 71.61% |
| Log loss | 0.528745 |
| Brier score | 0.177882 |
| ROC AUC | 0.809416 |
| 10-bin ECE | 0.056790 |

## Uncalibrated test-set reference

| Metric | Raw W0 |
|---|---:|
| Accuracy | 71.94% |
| Log loss | 0.538029 |
| Brier score | 0.180312 |
| ROC AUC | 0.809416 |
| 10-bin ECE | 0.065953 |

Calibration therefore improves log loss, Brier score, and ECE while leaving AUC unchanged, with a small decrease in threshold accuracy.

## Decision

This report establishes the **W0 baseline only**. It does not establish robustness or production readiness.

The next evaluation phase should use the same robustness framework applied to men's v0/v1: rolling-origin backtests, temporal regime checks, competition/team-history subgroups, confidence buckets, and a genuinely future holdout.

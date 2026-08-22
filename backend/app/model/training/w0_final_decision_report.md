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

Executed five expanding windows with validation-only calibration:

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

The rolling results are reasonably stable, with expected variation across chronological regimes. There is no evidence from these windows alone of catastrophic regime failure.

## Time-regime diagnostic

| Period | Accuracy | Log loss | Brier | AUC |
| --- | ---: | ---: | ---: | ---: |
| Middle | 70.06% | 0.5779 | 0.1964 | 0.7681 |
| Newer | 72.75% | 0.5328 | 0.1778 | 0.8130 |

The newer regime is stronger than the middle regime in this diagnostic. This is not evidence of a recent-regime collapse.

## Competition and team-history diagnostics

The women's corpus is competition-diverse. The largest competition groups include ICC Women's T20 World Cup, Kwibuka Women's Twenty20 Tournament, ACC Women's Premier Cup, T20 World Cup Asia Region Qualifier, and T20 World Cup Qualifier.

Team-history depth at match time is dominated by established teams:

- 0–4 prior matches: 101
- 5–19 prior matches: 430
- 20+ prior matches: 1,535

A reliable home/away field is not available in `CanonicalMatch`; no home advantage was inferred from venue.

## Future-holdout status

The harness now defines a final chronological 171-match holdout at the end of the 2,066-match decisive corpus. It is deliberately documented as a **nested temporal slice of the existing frozen 310-match baseline test period**, not as a new disjoint corpus period.

The repository must not treat this nested slice as an independent holdout until its exact metrics have been generated from the committed harness. In particular, no claim that W0 is production-ready should be based on this report alone.

## Decision

**W0 baseline implementation: FROZEN.**

**W0 model: NOT YET PROMOTED.**

The baseline implementation and robustness harness are stable enough to serve as the reference for women's-model experiments. The model itself should remain a candidate until the committed future-holdout section is executed and its metrics are recorded in this report.

No feature optimization or W1 work should begin before that final execution gate.

## Reproducibility requirement

Run the committed harness against the retained Cricsheet archive and save its JSON output. The final promotion decision must use those generated numbers, not reconstructed or manually transcribed results.

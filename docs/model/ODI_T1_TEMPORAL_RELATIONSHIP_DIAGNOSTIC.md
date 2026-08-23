# ODI T1 — Temporal Relationship Diagnostic

## Status

**Diagnostic complete. O0 remains frozen. O13 is not yet executed.**

## Objective

Determine whether the apparent temporal non-stationarity is primarily caused by changing feature magnitude, changing feature/outcome relationship, or changing score-to-probability calibration.

## Corpus and control

- Locked men's ODI corpus: 2,569 matches
- Decisive chronological rows: 2,440
- Corpus SHA-256: `f0798ef14e1f3f61720d41978289fe7318257263f59edba5dca0b35dbba64d6c`
- Canonical O0 feature contract: 13 features
- O0 training: rows 0:1708
- Diagnostic predictions: fixed O0 model applied chronologically to all 2,440 rows
- No feature engineering, parameter search, or O13 fitting was performed

## D1/T1 — Score-to-probability calibration drift

The fixed O0 raw score was evaluated in eight chronological blocks of 305 decisive matches. A descriptive logistic calibration of outcome against the O0 raw logit was estimated separately within each block. These block calibrations are diagnostic summaries only and were not used to tune O0.

| Block | Date range | Calibration intercept | Calibration slope | Raw log loss |
|---:|---|---:|---:|---:|
| 0 | 2002-06-27 → 2006-05-28 | -0.194 | 0.881 | 0.561 |
| 1 | 2006-06-13 → 2009-01-26 | -0.159 | 1.088 | 0.555 |
| 2 | 2009-01-28 → 2011-09-16 | 0.043 | 0.996 | 0.601 |
| 3 | 2011-09-19 → 2014-11-23 | 0.030 | 0.959 | 0.631 |
| 4 | 2014-11-23 → 2017-10-18 | 0.302 | 1.109 | 0.589 |
| 5 | 2017-10-20 → 2021-06-29 | 0.280 | 0.538 | 0.656 |
| 6 | 2021-07-01 → 2023-09-17 | -0.236 | 0.848 | 0.647 |
| 7 | 2023-09-17 → 2026-08-13 | -0.354 | 0.657 | 0.696 |

The calibration slope moves from approximately 1.0–1.1 in much of the earlier history to 0.538 in block 5 and 0.657 in the latest block. The intercept also changes materially, including a reversal from positive to negative in the final two blocks.

**Finding:** the mapping from O0 score to outcome probability is not stationary. Calibration drift is real, but this alone does not explain the full degradation because the underlying component/outcome relationships also change.

## D2/T1 — Component/outcome relationship drift

For each O0 historical component, the signed matchup difference A−B was compared against outcome in the same eight chronological blocks. The following are outcome gaps (mean feature value for A wins minus mean feature value for A losses):

| Component | Block 0 | Block 7 | Relative change |
|---|---:|---:|---:|
| Recent win rate | 0.2572 | 0.0586 | -77.2% |
| Batting runs/ball | 0.1061 | 0.0260 | -75.5% |
| Wickets/ball | 0.00351 | 0.00066 | -81.3% |
| Runs conceded/ball | -0.0136 | -0.00187 | magnitude -86.3% |
| Chase win rate | 0.3116 | 0.0518 | -83.4% |
| Defend win rate | 0.2753 | 0.0672 | -75.6% |
| Strength | 0.1567 | 0.0337 | -78.5% |

The deterioration is therefore broad rather than isolated to strength. This is stronger evidence for changing feature/outcome relationships than for a simple loss of feature magnitude alone.

The O0 `strength` feature is itself the mean of the six paired historical component differences, so it is not an independent information source. The T1 evidence therefore does not justify another isolated strength transformation.

## D3 — Context / matchup

The chase and defend components both show substantial temporal deterioration, but this diagnostic does not yet isolate whether the deterioration is caused by a context-specific mechanism or by the broader temporal shift. Therefore no context interaction is promoted from this diagnostic.

A future diagnostic should condition chase/defend residuals jointly on era and history depth before proposing a context interaction.

## Conclusion

T1 provides direct evidence that the ODI environment is non-stationary at two levels:

1. **feature/outcome relationships weaken or change over chronological eras**;
2. **the score-to-probability calibration mapping changes over chronological eras**.

This confirms that O7's fixed targeted-decay approach was structurally too narrow. O7 already showed that a single 20-match half-life harms the untouched baseline test and loses 3 of 5 rolling-origin windows. O12 likewise failed to improve the frozen probability metrics.

## Decision

- Keep O0 frozen.
- Do not tune O7 or O12.
- Do not propose another generic decay or strength transform.
- The next controlled hypothesis may investigate a **regularized time-varying mapping** of O0 features, but only after a pre-registered specification is frozen.

### Candidate O13 direction — not yet executed

A restrained time-varying logistic model in which feature coefficients can change smoothly with chronological time, with strong regularization toward the frozen O0 coefficients.

The purpose would be to test whether explicitly modeling coefficient drift is superior to uniformly discounting old observations.

No half-life, spline degree, regularization strength, or other O13 hyperparameter has been selected in this diagnostic. Those choices must be frozen before O13 evaluation.

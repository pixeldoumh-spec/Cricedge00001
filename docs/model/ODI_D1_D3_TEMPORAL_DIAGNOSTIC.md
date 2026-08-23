# ODI D1–D3 Diagnostic Assessment

## Status

**Diagnostic-only. O0 remains frozen. No O13 is authorized by this artifact.**

## Purpose

Determine whether the remaining O0 limitation is primarily:

1. calibration instability;
2. historical-strength representation;
3. matchup/context asymmetry; or
4. temporal distribution shift.

## Evidence boundary

The locked ODI population is 2,440 decisive chronological matches. The canonical O6 diagnostic is descriptive-only and requires the frozen chronological O0 population; it does not fit or tune a model. The repository implementation explicitly gates temporal-decay candidates using both meaningful change in outcome separation and meaningful feature-magnitude drift.

The current repository also contains the canonical O0 training/evaluation and calibration modules, but the recovered feature-row artifact is not stored as a committed dataset. Therefore this document does **not** claim a new numerical D1–D3 rerun beyond the already recorded O6/O7/O12 evidence.

## D1 — Temporal calibration drift

**Finding: supported, but secondary to feature/relationship drift.**

The O12 future-holdout analysis showed that validation-selected calibration can become harmful under later temporal conditions: calibrated O12 future-holdout log loss was 0.965596 while raw O12 was 0.666876. The same pattern exists for O0 at a smaller magnitude: calibrated O0 future-holdout log loss was 0.674297 versus raw O0 at 0.666934.

This demonstrates temporal instability in the score-to-probability mapping. It does not establish calibration as the primary root cause because the O6 component diagnostic independently shows broad deterioration in outcome separation across historical components.

## D2 — Component relationship drift

**Finding: primary evidence.**

The existing O6 diagnostic compares the first and second chronological halves without fitting or tuning. Outcome separation falls materially in multiple O0 components, including recent win rate, batting runs/ball, chase win rate, defend win rate, and strength. Strength therefore does not behave as a stationary predictive representation.

This is broader than a strength-only problem. The O0 strength feature is itself derived from the underlying historical components, so another isolated transformation of strength is not currently justified.

## D3 — Context / matchup asymmetry

**Finding: not isolated as the primary cause.**

Chase and defend components are already present in O0 and both exhibit temporal deterioration in the existing O6 evidence. This means contextual asymmetry may contribute to residual error, but its observed instability is currently entangled with the broader temporal shift. No new interaction should be proposed until context is evaluated conditionally on era and feature depth.

## Cross-diagnostic conclusion

| Candidate | Assessment | Confidence |
|---|---|---|
| Temporal distribution shift | **Primary limitation** | High |
| Calibration instability | Secondary manifestation / contributing issue | Medium–High |
| Strength representation | Not isolated as primary | Medium–High |
| Matchup/context asymmetry | Plausible contributor, not isolated | Medium |

## Interpretation

The existing evidence supports the following causal working hypothesis:

**historical signals become less discriminative as the ODI environment changes over time; the score-to-probability calibration also becomes less stationary under that shift.**

O7 is important negative evidence: a simple uniform 20-match targeted-decay response did not improve O0 and substantially degraded untouched-test probability quality. Therefore the next experiment should not be another arbitrary decay half-life.

O12 is additional negative evidence: multiplying strength by history depth did not improve the frozen test probability metrics and failed the future calibrated holdout.

## Decision

1. Keep O0 frozen.
2. Do not tune O7 or O12 retrospectively.
3. Do not propose O13 as another strength transform or generic decay transform.
4. The next controlled experiment should target **non-stationarity explicitly**, but only after a diagnostic that separates:
   - changing feature variance;
   - changing feature/outcome relationship;
   - changing calibration mapping;
   - context-specific temporal drift.

## Required next diagnostic before O13

If the exact regenerated O0 feature rows become available from the canonical pipeline, run a fresh D1–D3 numerical pass with:

- chronological era bins;
- score calibration slope/intercept by era;
- component-level outcome separation and rank association by era;
- chase/defend × era residual analysis;
- history-depth × era residual analysis;
- no parameter search and no use of the untouched test for selection.

Until that rerun is available, this report is an evidence synthesis, not a claim of a new model experiment.

# ODI O13 Decision

## Status

**REJECTED — keep O0 frozen.**

O13 tested the diagnosed temporal non-stationarity directly by augmenting every frozen O0 feature with one training-anchored linear time interaction `x_j * t`. It did not introduce a decay half-life, a strength transformation, or new raw match information.

## Verification checkpoint

The canonical O0 implementation was regenerated from the locked 2,440-row corpus. The O0 reproduction exactly matched the committed frozen baseline test metrics, including isotonic calibration: log loss 0.6749556551, Brier 0.2412253816, AUC 0.6364371500, accuracy 0.5409836066.

This checkpoint is required before trusting the O13 comparison.

## O13 result

On the untouched baseline test, O13 improved AUC and classification accuracy but worsened the primary probability-quality metrics:

- O0 log loss: 0.6749556551
- O13 log loss: 0.6763198544
- O0 Brier: 0.2412253816
- O13 Brier: 0.2416664661
- O0 AUC: 0.6364371500
- O13 AUC: 0.6479678936
- O0 accuracy: 0.5410
- O13 accuracy: 0.5902

The independent future holdout is more unfavorable:

- O0 log loss: 0.6742973212
- O13 log loss: 0.7011726758
- O0 Brier: 0.2410391413
- O13 Brier: 0.2531937985
- O0 AUC: 0.6513317191
- O13 AUC: 0.6203927899

The validation-selected isotonic calibration therefore does not make the time-varying coefficient model robust to later temporal conditions.

## Decision

Reject O13. Keep O0 frozen.

Do not tune the temporal interaction, add nonlinear time terms, change regularization, search alternative time bases, or modify calibration after observing these results. Those would convert the completed controlled experiment into post-hoc rescue work.

## What O13 teaches us

The earlier temporal-drift diagnosis was real, but allowing every O0 coefficient to drift linearly with time is too flexible in the wrong way. It improves discrimination on the primary test while degrading probability quality and fails to generalize to the independent future holdout.

Therefore the correct conclusion is **not** that temporal non-stationarity is absent. Rather:

> The current evidence does not support a globally time-varying coefficient model as the right structural response.

## Next research direction

Do not propose O14 immediately. First isolate whether the non-stationarity is concentrated in the **score-to-probability mapping** rather than in the individual feature coefficients. A smaller diagnostic should compare chronological calibration slope/intercept behavior of the frozen O0 score before any new model is specified.

# ODI O14 Hypothesis Contract

## Status

**FROZEN FOR CONTROLLED EVALUATION — NOT YET PROMOTED**

O14 is the smallest hypothesis justified by the completed temporal-drift diagnostics. O0 remains the immutable control.

## Motivation

Conditional coefficient diagnostics identified three reproducible temporal effects after converting the positional Team-A/Team-B variables into semantically symmetric signed differences:

1. recent win-rate difference;
2. runs-conceded-per-ball difference;
3. defend-win-rate difference.

The effects survived the positional-symmetry diagnostic. Other candidate components did not meet the same reproducibility threshold.

## Representation

For teams A and B, define:

- `recent_win_diff = A_recent_win_rate - B_recent_win_rate`
- `runs_conceded_diff = A_runs_conceded_per_ball - B_runs_conceded_per_ball`
- `defend_win_diff = A_defend_win_rate - B_defend_win_rate`

The six signed paired differences are conceptually available, but O14 may time-vary **only these three validated components**. O0's derived `strength` must not receive an additional temporal interaction because it is the mean of all six paired differences and would introduce redundant structure.

## Time-varying structure

O14 uses a **single linear time interaction only for the three validated components**:

`logit(P(A wins)) = O0_linear_predictor + gamma1 * recent_win_diff * t + gamma2 * runs_conceded_diff * t + gamma3 * defend_win_diff * t`

where `t` is a chronological scalar normalized using the training prefix only.

No time interactions are permitted for the other O0 features.

## Guardrails

- O0 coefficients remain the base coefficients.
- Exactly three temporal interaction terms are permitted.
- No decay/half-life parameter.
- No history-depth interaction.
- No adaptive calibration is part of the O14 feature hypothesis.
- No new match-level/context features.
- No post-hoc feature selection.
- No test or future-holdout outcomes may influence fitting, selection, or calibration choices.
- The temporal scalar must be computed without future information.

## Evaluation protocol

Use the established chronological protocol:

- baseline training: rows `0:1708`
- validation: rows `1708:2074`
- untouched test: rows `2074:2440`

Also evaluate the established five rolling-origin windows and the independent future holdout. O0 must be refit under exactly the corresponding training prefix for any rolling-origin comparison.

## Promotion criteria

O14 is not promoted unless it provides a defensible improvement over O0 on the untouched test, with **log loss primary** and Brier, AUC, and ECE secondary, while avoiding a material future-holdout regression.

A validation improvement alone is insufficient.

The experiment must report both raw probability output and any permitted validation-only calibration under the existing protocol.

## Decision discipline

This document freezes the hypothesis before untouched-test evaluation. If O14 fails, do not tune the three interactions after observing test/future results. Record the failure and return to diagnosis.

# ODI O12 Decision

## Status

**REJECTED — keep O0 frozen.**

O12 was evaluated against the locked men's ODI corpus of 2,569 JSON matches / 2,440 decisive matches using the frozen chronological protocol.

## Hypothesis

`team_a_minus_team_b_strength × log1p(minimum_pre_match_decisive_history)`

The purpose was to test whether the existing O0 strength signal should receive an interaction with the minimum pre-match decisive history of the two teams.

## Result

O12 improved validation log loss and raw rolling-origin behavior, and slightly improved classification accuracy on the untouched baseline test. However, it lost the untouched test on every probability-quality metric: log loss, Brier score, AUC, and ECE.

The history-depth diagnostic also failed to support the hypothesis: O12 was worse than O0 in both reported depth buckets (20–49 and 50+).

The independent future holdout exposed a major calibration failure for the validation-selected calibrated model. O12 future-holdout log loss was 0.965596 versus O0 at 0.674297. Raw O12 log loss was 0.666876 versus O0 at 0.666934, so the failure is specifically evidence that the interaction does not yield robust calibrated probabilities under temporal shift.

## Decision rules

- Do not promote O12.
- Do not modify O0.
- Do not tune the O12 transform, coefficient, calibration, or regularization after seeing the test/future results.
- Treat O12 as a completed controlled experiment.
- Before O13, diagnose the source of remaining O0 error rather than applying another arbitrary transformation of the same strength feature.

## Next direction

Perform a diagnostic-only analysis separating four possible causes:

1. probability calibration;
2. team-strength representation;
3. matchup/context asymmetry;
4. temporal distribution shift.

Only after that diagnosis should a new controlled hypothesis be proposed.

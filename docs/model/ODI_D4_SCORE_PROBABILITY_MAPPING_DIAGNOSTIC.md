# ODI D4 — Score → Probability Mapping Stability Diagnostic

## Status

**COMPLETED — diagnostic only. No O0 modification and no new model registered.**

## Purpose

D4 isolates whether the temporal instability identified by T1 is primarily in the final mapping from the frozen O0 score to win probability, rather than only in the underlying feature/outcome relationships.

The analysis uses the locked chronological 2,440-row decisive ODI population and the canonical O0 training protocol:

- Train: rows `0:1708`
- Validation: rows `1708:2074`
- Untouched test: rows `2074:2440`
- O0 model: `StandardScaler → LogisticRegression(max_iter=2000)`
- Validation-only isotonic calibration is retained exactly as the frozen O0 procedure.

No era result is used to fit or modify O0 or any candidate model.

## Reproduction checkpoint

Canonical O0 regenerated from the locked corpus reproduces the committed baseline test exactly after validation-only isotonic calibration:

- Log loss: `0.6749556551`
- Brier: `0.2412253816`
- AUC: `0.6364371500`
- Accuracy: `0.5409836066`

Raw O0 test performance before calibration is:

- Log loss: `0.6815164371`
- Brier: `0.2440308480`
- AUC: `0.6368863997`
- Accuracy: `0.5737704918`

## Five chronological eras

The 2,440 rows are divided into five equal chronological blocks of 488 decisive matches. Calibration slope/intercept are descriptive diagnostics: for each era, a logistic regression of outcome on the frozen O0 logit score is fitted only to quantify the local mapping. These local fits are never used for prediction or tuning.

| Era | Dates | Actual win rate | Mean raw O0 p | Raw log loss | Raw Brier | Raw ECE | Cal. intercept | Cal. slope |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 2002-06-27 → 2007-10-23 | 0.506148 | 0.545432 | 0.574629 | 0.196856 | 0.045847 | -0.179887 | 0.888617 |
| 2 | 2007-10-25 → 2012-03-11 | 0.573770 | 0.568207 | 0.570859 | 0.195887 | 0.032846 | -0.007013 | 1.151866 |
| 3 | 2012-03-13 → 2017-03-05 | 0.608607 | 0.552499 | 0.602853 | 0.207993 | 0.058260 | 0.245285 | 1.113719 |
| 4 | 2017-03-09 → 2022-07-27 | 0.559426 | 0.572923 | 0.658745 | 0.230069 | 0.048529 | 0.037244 | 0.659776 |
| 5 | 2022-07-31 → 2026-08-13 | 0.475410 | 0.559381 | 0.677783 | 0.242164 | 0.086366 | -0.303483 | 0.749048 |

## Score discrimination by era

Frozen O0 AUC also declines materially across the same eras:

- Era 1: `0.767500`
- Era 2: `0.754584`
- Era 3: `0.713258`
- Era 4: `0.662151`
- Era 5: `0.640911`

Therefore the score-to-probability mapping is not the only unstable component. The score's ranking/discriminative information itself deteriorates over time.

## Calibration-only evidence

The local calibration slope/intercept move substantially across eras. A perfectly stable mapping would remain approximately constant around slope `1` and intercept `0`.

Observed slope range: `0.659776` to `1.151866`.

Observed intercept range: `-0.303483` to `+0.245285`.

The late-era raw O0 probability quality also deteriorates:

- Raw log loss: `0.574629` → `0.677783`
- Raw Brier: `0.196856` → `0.242164`
- Raw ECE: `0.045847` → `0.086366`

This confirms meaningful score→probability instability, especially in the latest era.

## Important interaction with frozen calibration

The frozen validation-selected isotonic mapping is not uniformly stable across eras:

| Era | Isotonic log loss | Isotonic Brier | Isotonic ECE |
|---|---:|---:|---:|
| 1 | 0.787094 | 0.201269 | 0.062523 |
| 2 | 0.584378 | 0.201444 | 0.060399 |
| 3 | 0.612013 | 0.211857 | 0.087860 |
| 4 | 0.635744 | 0.223708 | 0.016795 |
| 5 | 0.668904 | 0.238663 | 0.077814 |

The independent future segment is especially important: the existing frozen O0 validation-selected calibration worsens future log loss relative to raw O0. This is consistent with calibration drift, not evidence that O0 itself should be changed.

## Decision

### D4 conclusion: **CALIBRATION DRIFT IS REAL, BUT IT IS NOT THE SOLE ROOT CAUSE.**

Two mechanisms are simultaneously present:

1. **Score discrimination degrades over chronological eras** — AUC falls from `0.7675` in the earliest era to `0.6409` in the latest.
2. **The score→probability mapping also drifts** — calibration slope and intercept vary substantially, and frozen validation calibration is not robust to the latest temporal distribution.

Therefore we should **not** jump directly to a time-varying calibration model and claim it solves the problem. Calibration can repair probability mapping but cannot recover the lost ranking information shown by the AUC decline.

## Next isolated diagnostic before any new model

The next step should be a **calibration-only counterfactual diagnostic on the frozen O0 score**:

> Can a strictly chronological, low-complexity adaptive calibration rule improve log loss/Brier/ECE on later periods without changing the O0 ranking?

This must remain diagnostic-only until its exact protocol is frozen. It should compare the frozen O0 calibration against a small number of pre-specified chronological calibration strategies, with no feature changes and no test/future tuning.

If calibration-only adaptation cannot recover the later probability-quality degradation, the next model should target the underlying feature/discrimination drift instead. If it can, a constrained calibration mechanism becomes a defensible candidate direction.

## Experiment discipline

- O0 remains frozen.
- No feature engineering is introduced by D4.
- No test or future block is used to fit a candidate model.
- No post-hoc parameter tuning is performed.
- D4 does not create or promote O14.

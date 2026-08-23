# ODI D5 — Strictly Chronological Adaptive Calibration Diagnostic

## Status

**COMPLETED — diagnostic only. No O0 modification and no new model promoted.**

## Question

Can a strictly chronological, low-complexity adaptive calibration improve later-period log loss, Brier score, and ECE while leaving the frozen O0 ranking completely unchanged?

## Locked setup

- Corpus: locked men's ODI population, 2,569 matches / 2,440 decisive rows.
- O0 feature engine: canonical recovered implementation.
- O0 model: `StandardScaler -> LogisticRegression(max_iter=2000)` trained on rows `0:1708`.
- Validation calibration set: rows `1708:2074`.
- Later-period evaluation: rows `2074:2440`.
- No future/test labels are used before their prediction.
- O0 raw scores are fixed throughout; only the probability mapping is changed.

The O0 reproduction checkpoint remains exact: baseline calibrated test log loss `0.6749556551`, Brier `0.2412253816`, AUC `0.6364371500`, accuracy `0.5409836066`.

## Calibration strategies

### 1. Frozen Platt

A single two-parameter logistic calibration is fitted on the validation block and applied unchanged to the later period. This is the clean ranking-preserving calibration control.

### 2. Expanding chronological Platt

Initialize with the validation block. Before each later-period prediction, fit a two-parameter logistic calibration using only labels observed strictly before that prediction: validation observations plus all previously observed later-period observations.

### 3. Rolling-366 chronological Platt

Before each later-period prediction, fit the same two-parameter logistic calibration using only the most recent 366 observed calibration outcomes. The 366-row window matches the frozen validation-block size and was selected as a pre-specified diagnostic window, not tuned on the later evaluation.

## Later-period results

| Strategy | Log loss | Brier | AUC | ECE | Ranking vs raw O0 |
|---|---:|---:|---:|---:|---|
| Raw O0 | `0.681516` | `0.244031` | `0.636886` | `0.093236` | reference |
| Frozen Platt | `0.679571` | `0.243370` | `0.636886` | `0.082996` | **exactly preserved** |
| Expanding Platt | `0.673425` | `0.240397` | `0.627842` | `0.065318` | **not preserved** |
| Rolling-366 Platt | `0.666864` | `0.237145` | `0.629908` | `0.036267` | **not preserved** |

The adaptive strategies improve probability quality substantially, especially rolling-366 Platt. However, because the calibration mapping changes over time, it changes the ordering of scores across the combined later-period population. Therefore it fails the requirement that O0's ranking remain completely unchanged.

The ranking result is not a numerical accident: a single fixed positive-slope Platt transformation is monotonic and preserves every O0 ordering exactly; time-varying mappings are different functions applied at different times and can therefore create cross-time rank inversions.

## Rank-preservation diagnostics

Spearman rank correlation against raw O0 later-period scores:

- Frozen Platt: `1.000000`; zero ordering differences.
- Frozen isotonic control: `0.984702`; isotonic ties change some ordering relationships.
- Expanding Platt: `0.985616`; ordering differences occur.
- Rolling-366 Platt: `0.963061`; larger cross-time ordering change occurs.

Thus adaptive calibration cannot honestly be described as a pure ranking-preserving calibration mechanism over the whole later-period population.

## Chronological block behavior

For additional descriptive evidence, the later period was split into two chronological blocks without using either block to tune the strategy.

### Rows 2074:2257

| Strategy | Log loss | Brier | AUC | ECE |
|---|---:|---:|---:|---:|
| Raw O0 | `0.652120` | `0.230227` | `0.714646` | `0.141649` |
| Frozen Platt | `0.664642` | `0.236116` | `0.714646` | `0.110459` |
| Expanding Platt | `0.656342` | `0.232060` | `0.708995` | `0.119011` |
| Rolling-366 Platt | `0.643188` | `0.225552` | `0.714767` | `0.078661` |

### Rows 2257:2440

| Strategy | Log loss | Brier | AUC | ECE |
|---|---:|---:|---:|---:|
| Raw O0 | `0.710913` | `0.257835` | `0.548769` | `0.099581` |
| Frozen Platt | `0.694500` | `0.250625` | `0.548769` | `0.060840` |
| Expanding Platt | `0.690508` | `0.248733` | `0.546857` | `0.053097` |
| Rolling-366 Platt | `0.690540` | `0.248739` | `0.549845` | `0.035839` |

The later block shows the same pattern: adaptive calibration improves probability quality, but the mapping is no longer globally ranking-preserving.

## Decision

### D5 conclusion: **CALIBRATION ADAPTATION WORKS FOR PROBABILITY QUALITY, BUT FAILS THE STRICT RANK-PRESERVATION REQUIREMENT.**

There are two distinct findings:

1. **Calibration drift is actionable.** Strictly chronological adaptive Platt calibration improves later-period log loss, Brier score, and ECE. Rolling-366 Platt is the strongest of the tested diagnostic strategies.
2. **Adaptive calibration is not ranking-invariant.** Expanding and rolling calibration alter cross-time ordering, so they cannot be treated as a pure probability remapping that leaves the frozen O0 ranking completely unchanged.

The fixed Platt control preserves O0 ranking exactly, but its improvement over raw O0 is modest and it remains worse than the frozen validation-selected isotonic O0 result on the full later period.

## Research implication

Do **not** create O14 from this diagnostic yet.

The evidence now separates the problem cleanly:

- A fixed monotonic calibration can preserve ranking but has limited ability to repair temporal probability drift.
- Adaptive calibration can repair much of the later probability-quality degradation, but the time-varying mapping itself changes cross-time rankings.
- O0 discrimination still deteriorates over time, so calibration cannot be the complete solution.

The next controlled question should therefore be whether a **ranking-preserving temporal calibration architecture is mathematically possible under the project's evaluation definition**, or whether temporal adaptation necessarily requires allowing some cross-time ranking change. That decision must be settled before designing the next predictive model.

## Experiment discipline

- O0 remains frozen.
- No O14 is registered.
- No later-period outcome is used before its prediction.
- No hyperparameter search was performed on the later evaluation.
- The 366-row adaptive window is a pre-specified diagnostic choice tied to the frozen validation size.
- This artifact is diagnostic evidence, not a model-promotion report.

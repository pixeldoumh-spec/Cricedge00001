# Model v0 baseline

Evaluated on the uploaded Cricsheet T20 corpus after filtering to men's T20 matches with exactly two teams and a known winner.

## Dataset

- 3,411 chronological match rows
- 70% train: 2,387
- 15% validation: 511
- 15% test: 513
- Positive class (first-listed team wins): 48.90% overall
- Test positive class: 50.49%

## Features

- `team_elo`
- `opponent_elo`
- `elo_difference`
- `form_3`
- `form_5`
- `form_10`

All features are generated strictly from matches before the prediction match.

## Test metrics

- Accuracy: **0.6394**
- Log loss: **0.6188**
- Brier score: **0.2148**
- ROC AUC: **0.7189**

Validation metrics were accuracy 0.6830, log loss 0.6067 and Brier score 0.2091.

## Feature distribution summary

| Feature | Mean | Std | Min | Median | Max |
|---|---:|---:|---:|---:|---:|
| team_elo | 1520.43 | 74.45 | 1345.72 | 1511.91 | 1833.55 |
| opponent_elo | 1518.84 | 73.33 | 1340.60 | 1510.28 | 1839.03 |
| elo_difference | 1.59 | 88.44 | -344.98 | -0.02 | 324.17 |
| form_3 | 0.498 | 0.234 | 0.000 | 0.500 | 1.000 |
| form_5 | 0.498 | 0.234 | 0.000 | 0.500 | 1.000 |
| form_10 | 0.498 | 0.234 | 0.000 | 0.500 | 1.000 |

## Calibration

The uncalibrated logistic model is directionally useful but not yet production-calibrated. On the held-out test set, the highest-probability bins were notably under-represented in predicted probability versus observed win rate, so a later calibration stage is warranted.

Model v0 is a **baseline**, not a production model. The next feature additions should be evaluated against these same chronological test metrics.

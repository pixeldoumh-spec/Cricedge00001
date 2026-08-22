# Model v0 — Frozen Baseline

Status: FROZEN

## Feature set

- team Elo
- opponent Elo
- Elo difference
- rolling form (3, 5, 10 matches)
- venue team win rate
- venue bat-first win rate
- head-to-head win rate
- batting run rate from prior deliveries
- bowling run rate from prior deliveries
- batting wicket rate from prior deliveries
- bowling wicket rate from prior deliveries

## Evaluation protocol

- Population: men's T20 matches with exactly two teams and a known winner
- Chronological ordering
- 70% train / 15% validation / 15% test
- Logistic regression configuration remains fixed
- Probability calibration fitted on validation only
- Test set is evaluated exactly once after calibration
- No raw Cricsheet ZIP committed to GitHub

## Frozen test results

- Accuracy: 69.20%
- Log loss: 0.58121
- Brier score: 0.19722
- ROC AUC: 0.76851
- 10-bin ECE: 0.04980

These numbers are the baseline for subsequent robustness/backtesting work. Future feature changes must be evaluated against the same protocol and must not overwrite this baseline.

## Next phase

Backtesting and robustness checks only. Do not add new predictive features until the baseline's stability has been assessed across time periods, competitions, team history depth, and outcome subgroups.

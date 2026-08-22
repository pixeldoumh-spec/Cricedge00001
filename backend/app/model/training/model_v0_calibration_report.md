# Model v0 + context + ball-strength calibration report

## Protocol

- Corpus: uploaded Cricsheet T20 JSON archive
- Population: men's T20, exactly two teams, known winner
- Matches: 3,411
- Chronological split: 70% / 15% / 15%
- Train: 2,387
- Validation: 511
- Test: 513
- Base estimator: StandardScaler + LogisticRegression(max_iter=2000)
- Base feature set: Elo/form + venue/H2H + ball-strength
- No test-set fitting
- Calibration method: Platt scaling fitted only on validation-set predictions

## Test results

| Metric | Uncalibrated | Validation-only Platt | Change |
|---|---:|---:|---:|
| Accuracy | 69.79% | 69.20% | -0.59 pp |
| Log loss | 0.58865 | **0.58121** | **-0.00744** |
| Brier score | 0.20104 | **0.19722** | **-0.00381** |
| ROC AUC | 0.76851 | 0.76851 | 0.00000 |
| 10-bin ECE | 0.06769 | **0.04980** | **-0.01789** |

## Conclusion

The calibrated model preserves ranking/discrimination (AUC is unchanged) while improving probability quality: log loss, Brier score, and 10-bin ECE all improve. Accuracy falls slightly because calibration changes the 0.5 decision threshold behavior; calibration is not intended to optimize classification accuracy.

The calibrated probabilities are therefore the preferred probability output for downstream prediction APIs, subject to later backtesting and recalibration when the training corpus is refreshed.

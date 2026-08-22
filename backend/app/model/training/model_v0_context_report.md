# Model v0 + Context Evaluation

This is an apples-to-apples comparison using the same 3,411-match men's T20 population, chronological ordering, 70/15/15 split, StandardScaler + LogisticRegression(max_iter=2000), and the same test set.

## Split

| Set | Matches |
|---|---:|
| Train | 2,387 |
| Validation | 511 |
| Test | 513 |

## Test results

| Metric | Model v0 | v0 + venue/H2H | Change |
|---|---:|---:|---:|
| Accuracy | 65.69% | **67.84%** | +2.14 pp |
| Log loss | 0.61294 | **0.59641** | -0.01653 |
| Brier score | 0.21211 | **0.20426** | -0.00784 |
| ROC AUC | 0.72674 | **0.75414** | +0.02741 |
| 10-bin ECE | 0.02823 | 0.05264 | +0.02441 |

## Interpretation

Venue and head-to-head features improve discrimination and probabilistic scoring on the unchanged chronological test set. Accuracy, log loss, Brier score, and ROC AUC all improve.

However, the simple uncalibrated model's 10-bin expected calibration error becomes worse. Therefore these new features should be retained, but the resulting probabilities must not yet be treated as production-calibrated probabilities. Calibration should be a separate later step using only the validation portion.

## Important reproducibility note

The earlier Model v0 narrative reported different baseline numbers. Re-running the committed `model_v0.py` logic against the uploaded 3,411-match corpus produces the baseline numbers shown above. These numbers supersede the earlier narrative because this report is based on the actual corpus, the committed feature implementation, and the unchanged split procedure.

No raw Cricsheet ZIP is stored in the repository.

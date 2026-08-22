# Model v1 rolling-origin + future-holdout evaluation

## Protocol

- Population: 3,411 eligible men's T20 matches.
- Chronological ordering: unchanged from the frozen Model v0 experiment.
- Five rolling origins: 50%, 55%, 60%, 65%, and 70% training boundaries.
- Each rolling origin uses the next 10% as validation and the following 10% as test.
- Calibration is fitted only on each origin's validation predictions using Platt scaling on the prediction logit.
- A genuine future holdout is the final 10% (342 matches), with training through 80%, validation on 80%-90%, and final evaluation on 90%-100%.
- No future test observations are used for fitting, calibration, or model selection.

## Rolling-origin results

| Train | v0 log loss | v1 log loss | v0 Brier | v1 Brier | v0 AUC | v1 AUC | v0 ECE | v1 ECE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 50% | 0.62258 | 0.64490 | 0.21626 | 0.22680 | 0.73706 | 0.69836 | 0.08117 | 0.07354 |
| 55% | 0.61346 | **0.60970** | 0.21190 | **0.21064** | 0.74087 | 0.74118 | 0.05942 | 0.06084 |
| 60% | 0.61652 | 0.62728 | 0.21428 | 0.21962 | 0.71611 | 0.69670 | 0.05212 | **0.04354** |
| 65% | 0.58832 | 0.61304 | 0.20225 | 0.21328 | 0.75036 | 0.72088 | 0.04928 | 0.05640 |
| 70% | 0.57827 | **0.56335** | 0.19783 | **0.19250** | 0.76352 | **0.77649** | 0.06280 | **0.03369** |

v1 improves log loss and Brier in 2 of 5 rolling windows, is essentially tied on AUC at 55%, and shows stronger calibration in 2 windows. It loses materially in the 50%, 60%, and 65% windows.

## Genuine future holdout

Final 10%: 342 matches, from **2026-02-25 through 2026-08-21**. Neither model nor calibrator was fitted on this period.

| Metric | v0 | v1 | v1 minus v0 |
|---|---:|---:|---:|
| Accuracy | 0.64327 | **0.69591** | **+0.05263** |
| Log loss | 0.61169 | **0.58901** | **-0.02269** |
| Brier | 0.21212 | **0.20301** | **-0.00910** |
| ROC AUC | 0.72340 | **0.75017** | **+0.02677** |
| 10-bin ECE | 0.07235 | **0.04732** | **-0.02503** |

## Decision

The future holdout is strongly favorable to v1, including lower log loss/Brier and better discrimination/calibration. However, the five rolling-origin windows are mixed rather than uniformly favorable. Therefore this experiment provides **evidence for v1 as the stronger current candidate**, but is not sufficient by itself to freeze v1 as the replacement for v0.

Recommended status: **v0 remains the frozen reference; v1 is the leading candidate and should receive one final independent evaluation before promotion.**

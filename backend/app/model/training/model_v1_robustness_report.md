# Model v1 robustness / backtesting report

Model v1 was evaluated against the frozen Model v0 using the actual 3,411-match men's T20 corpus.

Primary split: chronological 2,387 train / 511 validation / 513 test.
Calibration: validation-only Platt scaling using the repository calibration convention (logit of validation probabilities). The frozen 513-match test set is not used for fitting or tuning.

## Frozen test overall

| Metric | v0 | v1 |
|---|---:|---:|
| Accuracy | 65.302% | **69.396%** |
| Log loss | 0.61190 | **0.57045** |
| Brier score | 0.21164 | **0.19635** |
| ROC AUC | 0.72674 | **0.76510** |
| 10-bin ECE | 0.05971 | **0.04854** |

On the frozen test, v1 improves every reported metric.

## Time periods

| Period | v0 log loss | v1 log loss | v0 Brier | v1 Brier | v0 AUC | v1 AUC |
|---|---:|---:|---:|---:|---:|---:|
| 2025 (n=104) | 0.54889 | **0.51946** | 0.18489 | **0.17524** | 0.79430 | **0.82760** |
| 2026 (n=409) | 0.62792 | **0.58342** | 0.21844 | **0.20172** | 0.70778 | **0.74874** |

v1 improves all three metrics in both observed test periods.

## Competition groups

Only competitions with at least 30 frozen-test matches are reported. The only qualifying group was ICC Men's T20 World Cup (n=49):

- v0: accuracy 67.35%, log loss 0.59303, Brier 0.20580, AUC 0.74830
- v1: accuracy **73.47%**, log loss **0.53275**, Brier **0.17782**, AUC **0.79592**

Smaller competition samples are not treated as evidence for or against promotion.

## Team history depth

History depth is the number of prior completed matches for the first-listed team at prediction time.

| Depth | n | v0 log loss | v1 log loss | v0 Brier | v1 Brier |
|---|---:|---:|---:|---:|---:|
| 0–4 | 10 | 0.84441 | **0.30305** | 0.32362 | **0.09272** |
| 5–19 | 61 | 0.48613 | **0.36619** | 0.15674 | **0.11194** |
| 20–49 | 181 | **0.58930** | 0.62176 | **0.20301** | 0.21696 |
| 50+ | 261 | 0.64806 | **0.59285** | 0.22616 | **0.20577** |

The 20–49 history bucket is a clear v1 weakness. It is not large enough by itself to justify changing v1, but it is a robustness warning to monitor.

## Prediction confidence

Using calibrated v1 confidence (max of p and 1-p):

| Confidence | n | v1 accuracy | v1 log loss | v1 Brier |
|---|---:|---:|---:|---:|
| 50–60% | 159 | 57.86% | 0.67839 | 0.24267 |
| 60–70% | 145 | 63.45% | 0.65885 | 0.23295 |
| 70–80% | 87 | 72.41% | 0.59391 | 0.20169 |
| 80%+ | 122 | **89.34%** | **0.30799** | **0.08869** |

Confidence ordering is sensible: higher-confidence predictions are substantially more accurate.

## Outcome subgroups

The frozen test contains 162 predicted-favorite wins, 60 predicted-favorite losses, 97 predicted-underdog wins, and 194 predicted-underdog losses. These are descriptive counts rather than separate tuning targets.

## Expanding-window backtests

Each window uses a 10% validation period for calibration and the following 10% for testing. No test window is used for fitting.

| Train | Test n | v0 log loss | v1 log loss | v0 Brier | v1 Brier | v0 AUC | v1 AUC |
|---|---:|---:|---:|---:|---:|---:|---:|
| 50% (1705) | 341 | **0.62258** | 0.64490 | **0.21626** | 0.22680 | **0.73706** | 0.69836 |
| 60% (2046) | 341 | **0.61652** | 0.62728 | **0.21428** | 0.21962 | **0.71611** | 0.69670 |
| 70% (2387) | 341 | 0.57827 | **0.56335** | 0.19783 | **0.19250** | 0.76352 | **0.77649** |
| 80% (2728) | 341 | 0.61235 | **0.58794** | 0.21244 | **0.20250** | 0.72234 | **0.75136** |

This is mixed rather than uniformly dominant: v1 loses on all principal metrics in the first two expanding windows, then wins in the later two. The later windows are more representative of the current-data regime, but this is not sufficient by itself to declare v1 universally superior.

## Decision

**Do not replace the frozen Model v0 yet.**

The frozen test and recent expanding windows strongly favor v1, including lower log loss and Brier score. However, v1 underperforms in the earliest two expanding windows and has a notable weakness in the 20–49 team-history bucket.

Therefore v1 remains a **candidate Model v1**, while v0 remains the reference baseline. The next promotion gate should be a broader rolling-origin evaluation (more than four windows) and, if available, a truly held-out future period before freezing v1.

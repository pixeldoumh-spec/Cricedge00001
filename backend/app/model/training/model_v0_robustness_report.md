# Model v0 robustness report

## Scope

This report evaluates the frozen Model v0 feature set on the same 3,411-match men's T20 population. The primary holdout remains chronological: 70% train (2,387), 15% calibration/validation (511), 15% final test (513). Calibration is fitted only on the validation block.

The frozen feature set is:

- Elo and Elo difference
- 3/5/10-match rolling form
- venue team win rate
- venue bat-first win rate
- head-to-head win rate
- team batting run rate
- opponent-derived bowling run rate
- batting wicket rate
- opponent-derived bowling wicket rate

The raw Cricsheet ZIP remains outside GitHub.

## Final test

The reproducible rerun of the current feature implementation produced:

| Metric | Calibrated Model v0 |
|---|---:|
| Accuracy | 69.79% |
| Log loss | 0.57360 |
| Brier score | 0.19410 |
| ROC AUC | 0.77608 |
| 10-bin ECE | 0.04590 |

## Time periods

The final test contains 2025 and 2026 matches.

| Period | N | Accuracy | Log loss | Brier | AUC |
|---|---:|---:|---:|---:|---:|
| 2025 | 104 | 74.04% | 0.4867 | 0.1614 | 0.8505 |
| 2026 | 409 | 68.70% | 0.5957 | 0.2024 | 0.7558 |

Performance remains positive in both periods, although 2026 is weaker than 2025.

## Team history depth

History depth is the smaller of the two teams' prior match counts at prediction time.

| Prior-history bucket | N | Accuracy | Log loss | Brier | AUC |
|---|---:|---:|---:|---:|---:|
| 5–19 | 107 | 77.57% | 0.4649 | 0.1531 | 0.8670 |
| 20–49 | 204 | 70.59% | 0.5720 | 0.1932 | 0.7786 |
| 50+ | 186 | 65.05% | 0.6380 | 0.2183 | 0.7119 |

The mature-team bucket is not automatically the easiest regime; this should not be interpreted as evidence that more history is harmful because the buckets have different team/competition compositions.

## Prediction confidence

Confidence is `max(p, 1-p)`.

| Confidence | N | Accuracy | Log loss | Brier | AUC |
|---|---:|---:|---:|---:|---:|
| 50–60% | 114 | 50.00% | 0.7010 | 0.2539 | 0.5042 |
| 60–70% | 126 | 62.70% | 0.6689 | 0.2376 | 0.6034 |
| 70–80% | 112 | 76.79% | 0.5372 | 0.1764 | 0.7865 |
| 80%+ | 161 | 84.47% | 0.4342 | 0.1301 | 0.8692 |

This is a healthy monotonic confidence pattern: higher-confidence predictions are substantially more accurate.

## Competition coverage

Only competitions with at least 20 final-test matches are shown.

| Competition | N | Accuracy | Log loss | Brier | AUC |
|---|---:|---:|---:|---:|---:|
| ICC Men's T20 World Cup | 49 | 77.55% | 0.5437 | 0.1834 | 0.8044 |
| ICC Men's T20 World Cup Sub Regional Europe Qualifier A | 24 | 66.67% | 0.7031 | 0.2386 | 0.6444 |
| ICC Men's T20 World Cup East Asia-Pacific Qualifier | 21 | 52.38% | 0.6871 | 0.2487 | 0.6346 |
| ICC Men's T20 World Cup Sub Regional Africa Qualifier | 21 | 76.19% | 0.4750 | 0.1628 | 0.8818 |
| ICC Men's T20 World Cup Sub Regional Europe Qualifier C | 21 | 85.71% | 0.3730 | 0.1116 | 0.9364 |
| West Africa Trophy | 20 | 70.00% | 0.6024 | 0.2026 | 0.7143 |

Small competition samples are noisy; no competition-specific tuning is being introduced from these results.

## Toss subgroup

There is no reliable explicit home/away/neutral field in the Cricsheet `info` schema used by this corpus, so home/away robustness is intentionally **not reported** rather than inferred from venue names.

Toss is available often enough for a simple subgroup check:

| Team toss status | N | Accuracy | Log loss | Brier | AUC |
|---|---:|---:|---:|---:|---:|
| Won toss | 238 | 72.27% | 0.5404 | 0.1808 | 0.8064 |
| Lost toss | 275 | 67.64% | 0.6023 | 0.2056 | 0.7475 |

This is diagnostic only; toss is not a Model v0 feature.

## Outcome subgroup note

A post-match split such as "won by runs" versus "won by wickets" is not a clean predictive subgroup because the label itself determines the subgroup. It is therefore not used as a model-selection criterion.

## Expanding chronological backtest

Each fold uses the same model architecture and hyperparameters. The immediately preceding 10% block is used only for probability calibration; the next 10% block is the test window. Training expands forward.

| Train end | Train N | Calibration N | Test N | Test period | Accuracy | Log loss | Brier | AUC | ECE |
|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|
| 50% | 1,705 | 341 | 341 | 2024-05-05 → 2024-11-20 | 69.21% | 0.6042 | 0.2088 | 0.7454 | 0.0629 |
| 60% | 2,046 | 341 | 341 | 2024-11-20 → 2025-07-20 | 68.92% | 0.5940 | 0.2040 | 0.7491 | 0.0478 |
| 70% | 2,387 | 341 | 341 | 2025-07-20 → 2026-02-25 | 75.07% | 0.5260 | 0.1757 | 0.8185 | 0.0553 |
| 80% | 2,728 | 341 | 342 | 2026-02-25 → 2026-08-21 | 69.59% | 0.5945 | 0.1999 | 0.7653 | 0.0623 |

## Robustness verdict

Model v0 has positive predictive signal across all four expanding test windows and both final-test calendar periods. The strongest stability signal is the confidence ladder: higher-confidence predictions perform substantially better.

There is meaningful variation by competition and history depth, so Model v0 should not yet be assumed equally reliable for every competition or team population.

No home/away classification is reported because the source data does not provide a reliable explicit field. We should not manufacture one from venue frequency.

**Decision: keep Model v0 frozen. Do not tune features or hyperparameters based on these subgroup results. Use this report as the robustness baseline for future model versions.**

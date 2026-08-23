# ODI D5 — Chronological Adaptive Calibration Decision

## Status

**Diagnostic complete. No calibration candidate promoted. O0 remains frozen.**

## Question

Can a strictly chronological, low-complexity adaptive calibration improve later-period probability quality while preserving the O0 ranking within each chronological evaluation window?

## Protocol

- Locked corpus: 2,440 decisive men's ODIs.
- Corpus SHA-256: `f0798ef14e1f3f61720d41978289fe7318257263f59edba5dca0b35dbba64d6c`.
- Rolling-origin train ends: 1037, 1244, 1451, 1658, 1865.
- Each fold uses a 104-row pre-evaluation calibration block and a following 104-row evaluation block.
- O0 is refit for each rolling-origin fold using only rows preceding that fold.
- Adaptive calibrators use only outcomes available before their evaluation window.
- Independent future holdout: train 0:1586, calibration 1586:1952, evaluation 1952:2074.
- No test or future-holdout tuning.

## Ranking result

The ranking-preservation requirement **passes** for every tested Platt method within every chronological evaluation window.

For expanding Platt, rolling-366 Platt, and block Platt:

- AUC is exactly unchanged in every fold.
- Spearman rank correlation is 1.0 in every fold.
- Exact score ordering is preserved in every fold.

This is expected because Platt calibration is monotonic within each evaluation window.

## Probability-quality result

Rolling-origin aggregate:

| Method | Log loss | Brier | AUC | ECE |
|---|---:|---:|---:|---:|
| Raw O0 | 0.629135 | **0.219399** | **0.681024** | 0.032937 |
| Expanding Platt | **0.629095** | 0.219412 | 0.680331 | 0.032737 |
| Rolling-366 Platt | 0.635509 | 0.222355 | 0.672753 | **0.024683** |
| Block Platt | 0.651343 | 0.229667 | 0.654840 | 0.068958 |

No adaptive method improves **log loss + Brier + ECE simultaneously** over raw O0.

On the independent future holdout:

| Method | Log loss | Brier | AUC | ECE |
|---|---:|---:|---:|---:|
| Raw O0 | 0.666934 | **0.236749** | 0.660210 | 0.144852 |
| Expanding Platt | **0.666582** | 0.237020 | 0.660210 | 0.107383 |
| Rolling-366 Platt | 0.670919 | 0.239197 | 0.660210 | **0.094887** |

Expanding Platt gives a very small future log-loss improvement and a clearer ECE improvement, but Brier worsens. Rolling-366 improves ECE substantially but worsens both log loss and Brier.

## Decision

**Do not promote adaptive calibration as a production candidate from D5 alone.**

The diagnostic successfully isolates an important fact:

> Within-window ranking preservation is not the blocker. Calibration drift exists, but calibration-only adaptation is not sufficient to improve the complete probability-quality objective robustly.

Therefore:

- O0 remains frozen.
- Do not create O14 from adaptive calibration alone.
- Do not tune the adaptive window length retrospectively.
- Do not tune Platt parameters against the future holdout.
- Continue investigating the deeper temporal discrimination/feature-relationship drift.

## Research implication

The next diagnostic should focus on whether the **feature-to-outcome relationship itself changes over chronological eras**, because calibration-only adaptation cannot recover discrimination that has already deteriorated.

# T20 Challenger B — Adaptive Elo Strength Representation

Date: 2026-08-24

## Hypothesis

The current T20 models use chronological Elo with `initial_elo=1500` and `k_factor=20`. Challenger B tests whether a more responsive Elo representation improves the current 13-feature logistic model without changing any other feature definition, estimator, population rule, chronological split, or target.

K is selected only on the validation partition using validation log loss from the predeclared grid:

`20, 40, 60, 80, 120, 160, 240, 320`

The test set is never used for K selection or calibration.

## Frozen references

Men's V0: accuracy 0.6920, log loss 0.58121235, Brier 0.19722380, AUC 0.76850698, ECE-10 0.04980010. Production probabilities use validation-only Platt calibration.

Women's W0: accuracy 0.71612903, log loss 0.52874491, Brier 0.17788212, AUC 0.80941563, ECE-10 0.05679023. Production uses raw logistic probabilities; the previous W0 calibrator was not promoted.

## Frozen chronological test

| | Men's V0 | Challenger B | Δ | Women's W0 | Challenger B | Δ |
|---|---:|---:|---:|---:|---:|---:|
| Accuracy | 0.6920 | **0.72461** | +0.03261 | 0.71613 | **0.74516** | +0.02903 |
| Log loss | 0.58121 | **0.55338** | -0.02783 | 0.52874 | **0.52181** | -0.00693 |
| Brier | 0.19722 | **0.18686** | -0.01036 | 0.17788 | **0.17414** | -0.00374 |
| AUC | 0.76851 | **0.79181** | +0.02330 | 0.80942 | **0.82334** | +0.01393 |
| ECE-10 | 0.04980 | **0.04401** | -0.00579 | **0.05679** | 0.06989 | +0.01310 |

Selected K: **80 for men's V0; 160 for women's W0**.

## Robustness

Five rolling-origin windows were evaluated at 50%, 55%, 60%, 65%, and 70% training boundaries, with the next 10% as validation and following 10% as test. K was re-selected using only each origin's validation partition.

### Men's T20

Challenger B improved log loss, Brier and AUC in **all five** rolling origins. ECE improved in 3/5. The genuine future holdout also improved log loss (0.59731 → 0.57055), Brier (0.20248 → 0.19203), and AUC (0.75674 → 0.78392); ECE was slightly worse (0.05720 → 0.05909).

### Women's T20

Challenger B improved log loss, Brier and AUC in **all five** rolling origins and ECE in 4/5. The genuine future holdout improved log loss (0.54167 → 0.53263), Brier (0.18414 → 0.18004), AUC (0.79722 → 0.80945), and ECE (0.08867 → 0.06758).

## Independent fixed-K confirmation

After validation selection, the selected K was fixed and evaluated on a later, untouched 10% future holdout. No K search was performed on this confirmation period.

- Men's: K=80; 342-match holdout from 2026-02-25 through 2026-08-21. Accuracy 0.71930, log loss 0.57055, Brier 0.19203, AUC 0.78392, ECE 0.05909.
- Women's: K=160; 207-match holdout from 2026-04-11 through 2026-08-11. Accuracy 0.72464, log loss 0.53263, Brier 0.18004, AUC 0.80945, ECE 0.06758.

These are the same independent future-holdout values reported above, but the confirmation is explicitly run with K fixed rather than re-selected.

## Interpretation

The evidence strongly supports the hypothesis that the fixed K=20 Elo representation is too slow to adapt to changing team strength.

The effect is not isolated to one test window: the directional gains persist across the rolling-origin evaluation and independent future holdout.

### Current decision

- **Men's V0:** Challenger B is now a **strong replacement candidate**. It improves the frozen reference on accuracy, log loss, Brier, AUC and ECE, and the fixed-K future holdout confirms gains in log loss, Brier and AUC. The current V0 artifacts remain unchanged; replacement requires the normal artifact rebuild + provenance verification step rather than an additional model experiment.
- **Women's W0:** Challenger B is a **strong modeling candidate but not yet a production replacement**. It improves accuracy, log loss, Brier and AUC on the frozen test and is favorable on the future holdout, but its frozen-test ECE is worse. A separate calibration challenger is therefore warranted; calibration is not folded into B because that would confound the strength hypothesis.
- **Overall:** Do not replace both references with one blanket decision. Treat V0 and W0 independently.

## Provenance

Corpus SHA-256: `e868d332681b38df6f39376e6d7daf14143c57fc775abbf1cc830d8bb80dd997`

Challenger B implementation SHA: `3d58c5c1af22fbee5b33509e881a838829e3e49d`

Runner SHA: `d69f56e2a7fa643f732c0ba9dfd7ba64dc174799`

V0 implementation SHA: `09b0aedbdf109095bf7e1177f57378d702d2b88d`

Team-form SHA: `496339211d1f4ce0e018baad3b5561d88c2222f1`

Context SHA: `7c95aa0be8763160d738061dc3dc60aa8955501d`

Ball-strength SHA: `4e83b5f94c3d1d9a0e1f2d0efb4dbc0a45fa06b6`

Calibration SHA: `08fbfd1a7617df7e0c8e456b1378d9d3ed095b5`

Production-lock SHA: `81d93a7f55b2c02b1a48115975490b19d5b7ce0a`

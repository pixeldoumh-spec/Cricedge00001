# T20 Bounded Recency Movement — Reconciliation Report

Date: 2026-08-25

## Corpus / provenance

- Corpus: `t20s_json.zip`
- Corpus SHA-256: `e868d332681b38df6f39376e6d7daf14143c57fc775abbf1cc830d8bb80dd997`
- Research branch: `research/t20-adaptive-calibration`
- Bounded-recency protocol commit: `926db5c0b4f6dbf10edcd12110ca1493b5c53957`
- Corrected runner commit: `236daabb578617f1c833fe3c8223715dc62922bd`
- Result JSON SHA-256: `72e35de4443e5e42b6394a4fde389b6a79fc5e26cece294c6ada03e999377826`

## Protocol

Raw Challenger B is the control. The bounded movement features are appended to the unchanged 13-feature Challenger-B representation.

- Men's fast Elo K=80
- Women's fast Elo K=160
- Horizons: H=5, 10, 20 completed team matches
- Caps: 100 or 150 Elo per-match movement
- Signed bounded movement and predeclared signed+magnitude variants
- Configuration selected only on the main chronological validation partition
- The main validation-selected configuration is held fixed for all five rolling-origin evaluations
- Frozen test and 171-match future holdout never select a configuration
- No calibration
- V0/W0 untouched

Bounded movement is `tanh(rate_H / cap)` where `rate_H = (fast_elo_t - fast_elo_{t-H}) / H`; cold-start movement is zero when fewer than H completed matches exist.

## Main validation selection

Both genders selected **H=20, cap=100, signed+magnitude**.

Men's validation log-loss ranking:

1. H=20 cap=100 magnitude: 0.566477
2. H=20 cap=100 signed: 0.567514
3. H=20 cap=150 signed: 0.567517
4. H=10 cap=100 magnitude: 0.570473
5. H=10 cap=150 signed: 0.571441
6. H=10 cap=100 signed: 0.571447
7. H=5 cap=100 signed: 0.575342

Women's validation log-loss ranking:

1. H=20 cap=100 magnitude: 0.501113
2. H=5 cap=100 signed: 0.502316
3. H=20 cap=150 signed: 0.502768
4. H=20 cap=100 signed: 0.502778
5. H=10 cap=150 signed: 0.505859
6. H=10 cap=100 signed: 0.505960
7. H=10 cap=100 magnitude: 0.508956

## Frozen test — selected configuration vs raw Challenger B

| Metric | Men B | Men bounded | Women B | Women bounded |
|---|---:|---:|---:|---:|
| Accuracy | 0.717349 | 0.717349 | 0.745161 | 0.735484 |
| Log loss | 0.561040 | 0.563409 | 0.521812 | 0.531211 |
| Brier | 0.189758 | 0.190290 | 0.174137 | 0.178146 |
| AUC | 0.791795 | 0.790229 | 0.823341 | 0.822205 |
| ECE | 0.059800 | 0.053732 | 0.069887 | 0.087063 |

The selected bounded extension loses raw predictive performance on the frozen test for both genders. Men's ECE improves, but log loss/Brier/AUC do not. Women's accuracy/log loss/Brier/AUC/ECE all worsen.

## Five rolling origins — fixed main-validation-selected configuration

### Men's log loss

| Origin | Challenger B | Bounded | Delta |
|---|---:|---:|---:|
| 50% | 0.587020 | 0.588913 | +0.001893 |
| 55% | 0.579864 | 0.575734 | -0.004130 |
| 60% | 0.601521 | 0.592565 | -0.008956 |
| 65% | 0.565919 | 0.562134 | -0.003785 |
| 70% | 0.535231 | 0.542753 | +0.007522 |

Bounded wins **3/5** rolling log-loss windows.

### Women's log loss

| Origin | Challenger B | Bounded | Delta |
|---|---:|---:|---:|
| 50% | 0.529353 | 0.528102 | -0.001251 |
| 55% | 0.550059 | 0.527871 | -0.022188 |
| 60% | 0.488350 | 0.478014 | -0.010335 |
| 65% | 0.495462 | 0.494635 | -0.000827 |
| 70% | 0.532576 | 0.554228 | +0.021651 |

Bounded wins **4/5** rolling log-loss windows, but the final origin reverses strongly.

## Future 171-match holdout

| Metric | Men B | Men bounded | Women B | Women bounded |
|---|---:|---:|---:|---:|
| Accuracy | 0.754386 | 0.754386 | 0.771930 | 0.760234 |
| Log loss | 0.555092 | 0.546870 | 0.501506 | 0.494895 |
| Brier | 0.184718 | 0.180092 | 0.165722 | 0.164077 |
| AUC | 0.795423 | 0.811318 | 0.839901 | 0.841680 |
| ECE | 0.099951 | 0.118767 | 0.077395 | 0.112760 |

The bounded extension improves future log loss, Brier and AUC for both genders, but worsens ECE for both; women's accuracy also falls.

## Decision

**REJECT promotion as a replacement for raw Challenger B.**

Reason: the independently evaluated future holdout is encouraging, but the selected extension is worse on the frozen test for both genders and does not show sufficiently uniform chronological robustness. The latest-period gains therefore are not enough to justify replacing Challenger B.

The bounded-recency representation remains a **research finding**, not a production candidate.

### Surviving finding

Bounded recent strength movement may contain useful latest-period signal, but the evidence does not establish a stable enough improvement over fast Elo to promote it. Further arbitrary H/cap searching is not justified by this experiment alone.

# ODI O14 Decision

## Result

**REJECT O14 — keep O0 frozen.**

O14 was executed against the locked 2,440-row men's ODI population using the frozen O14 contract. The corpus archive SHA-256 was verified as `f0798ef14e1f3f61720d41978289fe7318257263f59edba5dca0b35dbba64d6c` and the generated modeling population contained exactly 2,440 decisive rows.

## Hypothesis tested

O14 added exactly three chronological interactions to the frozen O0 feature matrix:

- `(A recent win rate - B recent win rate) × t`
- `(A runs conceded/ball - B runs conceded/ball) × t`
- `(A defend win rate - B defend win rate) × t`

No decay, history-depth interaction, adaptive calibration, or additional match-level feature was introduced.

## Untouched test

Validation-selected isotonic calibration produced:

| Metric | O0 | O14 |
|---|---:|---:|
| Log loss | 0.674956 | **0.674477** |
| Brier | **0.241225** | 0.241542 |
| AUC | 0.636437 | **0.642592** |
| ECE | **0.081798** | 0.093592 |
| Accuracy | 0.540984 | **0.549180** |

The primary test log loss improvement is only 0.000479 and is not accompanied by an improvement in Brier or ECE.

## Rolling-origin

O14 won the log-loss comparison in **2/5** chronological windows; O0 won **3/5**.

This does not establish robust temporal generalization.

## Independent future holdout

Validation-selected isotonic calibration gave:

| Metric | O0 | O14 |
|---|---:|---:|
| Log loss | **0.674297** | 0.678819 |
| Brier | **0.241039** | 0.241563 |
| AUC | **0.651332** | 0.649852 |
| ECE | 0.112968 | **0.097230** |
| Accuracy | 0.573770 | **0.581967** |

Raw probabilities also favored O0 on future log loss, Brier, and AUC.

## Decision rationale

O14 demonstrates that the three previously identified temporal coefficient drifts can be represented structurally, but the resulting model does not produce a robust improvement in production probability quality. The small untouched-test log-loss gain fails to survive the independent future holdout, and the candidate loses Brier/ECE on the untouched test.

Therefore:

- Do not promote O14.
- Do not tune the three temporal interactions after observing test/future results.
- Do not alter O0.
- Keep O0 frozen as the production control.

## Next research direction

The coefficient-drift hypothesis is now rejected as a sufficient structural fix. The next step must return to diagnosis rather than another arbitrary temporal interaction. In particular, investigate whether the observed drift is caused by changes in the **joint feature geometry / regime structure** rather than independently changing feature coefficients.

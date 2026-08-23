# ODI Symmetric Signed Drift Diagnostic

## Purpose

Test whether the three previously identified positional O0 conditional coefficient-drift candidates survive conversion to semantically symmetric signed representations.

## Frozen boundaries

- Canonical repository: `pixeldoumh-spec/Cricedge00001`
- O0 remains frozen.
- Locked corpus SHA-256: `f0798ef14e1f3f61720d41978289fe7318257263f59edba5dca0b35dbba64d6c`
- 2,440 decisive rows.
- Development rows used for candidate selection: `0:1952`.
- Future holdout was not used for candidate selection.
- No new predictive model was created.

## Representation

The positional O0 components were converted to six semantically symmetric signed differences:

- `team_a_minus_team_b_recent_win_rate`
- `team_a_minus_team_b_batting_runs_per_ball`
- `team_a_minus_team_b_wickets_per_ball`
- `team_a_minus_team_b_runs_conceded_per_ball`
- `team_a_minus_team_b_chase_win_rate`
- `team_a_minus_team_b_defend_win_rate`

Positive values mean Team A exceeds Team B on the corresponding metric.

The O0 `strength` feature was excluded from this diagnostic because it is exactly the mean of these six signed differences; including it with all six would introduce perfect linear dependence.

## Conditional coefficient drift

A multivariate logistic regression over all six signed differences was fit separately to the early and late halves of five expanding chronological prefixes. Drift is defined as late coefficient minus early coefficient.

### Previously identified candidates

| Symmetric component | Prefix drift values | Direction consistent | Bootstrap 95% CI | Result |
|---|---|---|---|---|
| Recent win-rate difference | +1.454, +1.393, +1.024, +1.552, +1.689 | Yes | [+0.574, +2.850] | **Survives** |
| Runs-conceded/ball difference | +0.529, +0.399, +0.273, +0.099, +0.541 | Yes | [+0.183, +1.039] | **Survives** |
| Defend-win-rate difference | −0.822, −0.728, −0.670, −1.336, −1.244 | Yes | [−1.895, −0.580] | **Survives** |

The 500-resample development-era bootstrap used only rows `0:1952`.

### Other symmetric components

- Batting runs/ball difference: direction was not consistent; bootstrap CI crossed zero.
- Wickets/ball difference: direction was not consistent; bootstrap CI crossed zero.
- Chase win-rate difference: prefix direction was consistent, but the bootstrap CI crossed zero, so it is not promoted to the reproducible subset.

## Interpretation

The three previously identified candidates survive conversion to semantically symmetric signed representations. Therefore the observed conditional coefficient drift cannot be explained away simply as a Team A/Team B positional coding artifact.

This is **diagnostic evidence, not model-selection evidence**. It does not establish causal importance or production usefulness, and it does not justify tuning a temporal model yet.

## Decision

**Three-component symmetric drift subset survives:**

1. recent win-rate difference;
2. runs-conceded-per-ball difference;
3. defend-win-rate difference.

No new model is created at this stage. O0 remains frozen.

## Next controlled step

Freeze the smallest defensible temporal-drift hypothesis using exactly these three symmetric components and pre-register its parameterization and chronological evaluation protocol before touching the untouched test or future holdout.

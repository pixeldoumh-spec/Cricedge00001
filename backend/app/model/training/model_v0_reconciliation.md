# Model v0 — 13-feature reconciliation

## Status

**Canonical implementation restored.** `model_v0.py` now uses the 13-feature
contract that was used by the later v0/v1 apples-to-apples experiments, rather
than the earlier six-feature prototype.

This reconciliation is based on the repository's historical feature engines,
training reports, and comparison harness. The raw Cricsheet archive remains
outside GitHub.

## Canonical feature contract

| # | Feature | Source | Pre-match state | Leakage boundary |
|---|---|---|---|---|
| 1 | `team_elo` | `TeamFormEngine` | Team Elo before current match | Updated only after prior completed result |
| 2 | `opponent_elo` | `TeamFormEngine` | Opponent Elo before current match | Updated only after prior completed result |
| 3 | `elo_difference` | `TeamFormEngine` | `team_elo - opponent_elo` | Derived only from pre-match Elo |
| 4 | `team_form_3` | `TeamFormEngine` | Mean of team's last 3 results | Current result is not appended until after match |
| 5 | `team_form_5` | `TeamFormEngine` | Mean of team's last 5 results | Current result is not appended until after match |
| 6 | `team_form_10` | `TeamFormEngine` | Mean of team's last 10 results | Current result is not appended until after match |
| 7 | `venue_team_win_rate` | `ContextFeatureEngine` | Team historical win rate at venue | Venue state updates after completed match |
| 8 | `venue_bat_first_win_rate` | `ContextFeatureEngine` | Historical bat-first win rate at venue | Only completed matches with known toss decision are counted |
| 9 | `head_to_head_win_rate` | `ContextFeatureEngine` | Directional team-v-opponent historical win rate | H2H state updates after completed match |
| 10 | `batting_run_rate` | `BallStrengthEngine` | Prior team runs per six-ball equivalent | Delivery aggregates update only after completed match |
| 11 | `bowling_run_rate` | `BallStrengthEngine` | Prior opponent runs conceded per six-ball equivalent | Delivery aggregates update only after completed match |
| 12 | `batting_wicket_rate` | `BallStrengthEngine` | Prior team wickets lost per six-ball equivalent | Delivery aggregates update only after completed match |
| 13 | `bowling_wicket_rate` | `BallStrengthEngine` | Prior opponent wickets taken per six-ball equivalent | Delivery aggregates update only after completed match |

## Historical implementation recovered

### Team strength and form

`TeamFormEngine` starts unseen teams at Elo 1500 and uses K=20. It exposes
pre-match Elo and rolling result form, then updates both teams only after a
completed match result is known.

### Venue and H2H

`ContextFeatureEngine` keeps separate venue/team state and directional H2H
history. Missing history uses a neutral 0.5 prior. Bat-first venue history is
only updated when the toss winner and a `bat` decision are known.

### Ball-level strength

`BallStrengthEngine` maintains cumulative team batting and bowling aggregates
from prior deliveries. It exposes only the aggregate state before the current
match and updates it after the complete match.

## Model boundary

The canonical estimator remains:

- `StandardScaler`
- `LogisticRegression(max_iter=2000)`

The 13 features above are the only estimator inputs. No toss feature is part of
the canonical contract.

## Calibration boundary

Probability calibration is separate from the base estimator and uses
`ValidationPlattCalibrator`:

1. Fit the base estimator on the chronological training partition.
2. Generate probabilities for the validation partition.
3. Fit logistic calibration on the **logit of validation probabilities only**.
4. Apply that calibrator once to the untouched test partition.

The final test partition must never be used to fit the estimator, scaler,
feature state, or calibrator.

## Important historical distinction

The repository originally contained a six-feature `model_v0.py` prototype. That
was not the later enhanced 13-feature experiment. This reconciliation replaces
that incomplete prototype with the recovered 13-feature contract so the
production artifact can correspond to the evaluated reference model.

## Artifact gate

Do **not** serialize the production artifact until the 13-feature implementation
has been executed against the available corpus and the resulting split/metrics
have been reconciled with the recorded frozen-v0 evaluation.

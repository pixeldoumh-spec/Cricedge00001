# Model v0 artifact lock

Status: **FROZEN REFERENCE**

Model v0 is the selected men's T20 reference model. Its feature contract and training configuration must not be changed in place.

## Locked contract

- Population: 3,411 trainable men's T20 matches
- Chronological split: 2,387 train / 511 validation / 513 test
- Features: 13
- Estimator: `StandardScaler + LogisticRegression(max_iter=2000)`
- Calibration: validation-only Platt scaling
- Test data is never used to fit calibration
- Feature state is pre-match only; stateful engines update after match results

## Locked features

1. `team_elo`
2. `opponent_elo`
3. `elo_difference`
4. `team_form_3`
5. `team_form_5`
6. `team_form_10`
7. `venue_team_win_rate`
8. `venue_bat_first_win_rate`
9. `head_to_head_win_rate`
10. `batting_run_rate`
11. `bowling_run_rate`
12. `batting_wicket_rate`
13. `bowling_wicket_rate`

## Artifact gate

Generate artifacts from the retained Cricsheet ZIP:

```bash
python -m app.model.training.build_v0_artifacts \
  --archive /path/to/t20s_json.zip \
  --output-dir backend/models/v0
```

Then verify them:

```bash
python -m app.model.training.verify_v0_artifacts \
  --output-dir backend/models/v0
```

The verification command must print `PASS: Model v0 artifacts verified` before the artifacts are eligible for the inference/API path.

The ZIP and generated `.joblib` binaries are intentionally kept outside GitHub unless there is a deliberate deployment decision to store them there.

## Promotion rule

No feature, estimator, calibration change, or training-population change may be made under `v0`. Such work creates a new model version and must receive a new chronological evaluation and independent holdout.

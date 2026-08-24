# T20 Challenger A — Legal-ball rate semantics

Status: **implemented; corpus execution pending**.

## Hypothesis

The current V0/W0 ball-strength features count every Cricsheet delivery record in the denominator. Challenger A tests whether using cricket-legal deliveries only (excluding wides and no-balls) produces a better T20 probability model.

## Isolation

Only these four feature values may change:

- `batting_run_rate`
- `bowling_run_rate`
- `batting_wicket_rate`
- `bowling_wicket_rate`

The following must remain unchanged:

- population
- chronological ordering
- train/validation/test membership
- target
- Elo features
- form features
- venue features
- head-to-head feature
- estimator: `StandardScaler + LogisticRegression(max_iter=2000)`
- validation-only Platt calibration procedure
- test holdout

Wicket numerators are intentionally unchanged in Challenger A. This isolates the denominator question; wicket-event semantics are a separate hypothesis.

## Current reference populations

Men's V0:

- total: 3,411
- train: 2,387
- validation: 511
- test: 513

Women's W0:

- total: 2,066
- train: 1,446
- validation: 310
- test: 310

## Runner

```bash
python -m app.model.training.run_challenger_a \
  --archive /path/to/t20s_json.zip \
  --gender male \
  --output /path/to/challenger_a_male.json

python -m app.model.training.run_challenger_a \
  --archive /path/to/t20s_json.zip \
  --gender female \
  --output /path/to/challenger_a_female.json
```

The runner compares the V0 and Challenger A feature rows and fails if any non-rate feature changes.

## Decision rule

Challenger A is not promoted merely because one metric improves.

Promotion requires a controlled improvement on the appropriate untouched reference evaluation, with particular attention to:

1. log loss;
2. Brier score;
3. AUC;
4. calibration/ECE;
5. no population/split leakage;
6. reproducibility from the retained corpus.

If the challenger is mixed or worse, reject it and retain V0/W0 unchanged.

If the challenger is consistently superior, create a new T20 model version rather than modifying V0/W0 in place.

## Execution limitation

The exact retained Cricsheet ZIP is intentionally outside GitHub according to the V0 lock. It is not present in the connected repository or the available ChatGPT file library at the time this protocol was added. Therefore the full 3,411/2,066-row metric run has not been claimed or fabricated here.

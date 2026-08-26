# CPL Outcome Engine — Research Protocol v0.1

## 1. Scope

This is a separate CPL-specific research model family. It does not replace
T20 V0, W0, or Challenger B. Challenger B may later be used as a pre-match
strength prior, but the CPL engine has its own data contract, targets,
training procedure, evaluation, and provenance.

The recurring bookmaker market families supplied from CPL Match 16 are the
authoritative initial outcome contract. Coin-toss markets are excluded.

## 2. Core modelling principle

Do not train one unrelated binary classifier per bookmaker line.

Build underlying probability distributions from which recurring bookmaker
lines are queried. Examples:

- team runs -> P(runs > line)
- player runs -> P(runs > line)
- over runs -> P(over runs > line)
- total fours -> P(fours > line)
- total sixes -> P(sixes > line)

This keeps probabilities internally coherent and permits new market lines to
be evaluated without retraining the model.

## 3. Timing contract

Every prediction receives an information timestamp and a prediction snapshot.

### Pre-match
Only information known before the match is permitted.

### Confirmed-XI
Only information available after the playing XI is confirmed is permitted.

### Live
At event t, only state information through event t-1 may be used. The event
being predicted and every later event are forbidden.

## 4. Historical target reconstruction

Before model training, audit the historical CPL corpus for every target:

- match winner, including super-over resolution where applicable
- player-of-the-match award
- innings runs
- player runs
- over 1 through over 6 runs
- fours
- sixes
- most fours
- most sixes
- team with top batter
- team with top bowler

Every target must have a documented reconstruction rule and a coverage count.
Missing or ambiguous records are retained in an exclusion ledger rather than
silently imputed.

## 5. Data requirements

The preferred historical representation is canonical ball-by-ball data with:

- match identity
- date
- competition
- teams
- venue
- toss metadata (for contextual use only, never as a predictive target)
- playing XI / player identity
- innings and over order
- batter
- non-striker
- bowler
- runs off bat
- extras
- wickets and dismissal information
- innings completion
- match result
- player-of-match award where available.

Player and team identities must be normalized before aggregation.

## 6. Leakage boundaries

No feature may depend on an outcome occurring after the prediction timestamp.

Examples:

- player-run prediction cannot use final innings runs;
- top-batter prediction cannot use completed innings totals;
- live win probability cannot use the current ball before that ball is
  resolved;
- historical team/player states must be updated only after the match/event
  has occurred;
- future-season results cannot enter a historical training row.

## 7. Chronological evaluation

Random train/test splitting is prohibited for the primary evaluation.

The research protocol will use:

1. chronological training period;
2. validation period for all model/hyperparameter decisions;
3. frozen historical test period;
4. rolling-origin evaluation;
5. untouched prospective CPL 2026 evaluation.

The 2026 prospective stream is never used to tune the model while the
prospective evaluation is open.

## 8. Evaluation by outcome family

### Binary/categorical probability markets

- log loss
- Brier score
- calibration error / reliability
- AUC where the target supports it

### Count/distribution markets

- proper distributional score where implemented
- MAE as a secondary diagnostic
- interval coverage
- calibration of threshold probabilities

### Comparative player/team markets

- multiclass log loss
- Brier where appropriate
- calibration
- rank diagnostics as secondary evidence

## 9. Bookmaker benchmark

Bookmaker odds and lines are external comparison data only.

They are not training labels.

When odds are used for comparison, the research record must preserve the
market line, timestamp, bookmaker/source, and any required margin/overround
handling. Cricedge probabilities must remain independently generated.

## 10. Promotion rule

No market family is promoted merely because accuracy improves.

Promotion requires evidence that is:

- chronologically valid;
- reproducible;
- properly scored;
- calibrated enough for its intended use;
- stable across rolling origins;
- not dependent on leakage or bookmaker prices;
- supported by adequate target coverage.

## 11. First engineering gate

Do not train the full outcome engine until the historical CPL corpus audit is
complete.

The immediate deliverable is therefore a **CPL target-coverage audit** that
reports, for each market family:

- reconstructable: yes/no
- reconstruction rule
- required source fields
- historical match count
- valid target count
- missing count
- ambiguous count
- earliest/latest date
- player-identity coverage where relevant
- known limitations.

Only after this gate passes will the training dataset contract be frozen.

# ODI Conditional Coefficient Drift Diagnostic

## Status

**Diagnostic complete — no new model created. O0 remains frozen.**

## Question

Does a small subset of O0 components show reproducible **conditional** coefficient drift after controlling for the other O0 features?

## Protocol

The locked men's ODI corpus contains 2,440 decisive rows and has SHA-256:

`f0798ef14e1f3f61720d41978289fe7318257263f59edba5dca0b35dbba64d6c`

The diagnostic used the canonical 13-feature O0 population. The future region was excluded from candidate selection. The development region was divided chronologically and analyzed with a multivariate logistic regression containing all 13 O0 features.

For each of five expanding chronological prefixes (`1037`, `1244`, `1451`, `1658`, `1865`), coefficients were estimated separately on the early and late halves. The quantity of interest was the conditional coefficient change from early half to late half.

This is deliberately a diagnostic, not a candidate model evaluation. No test/future-holdout tuning was performed.

## Reproducible subset

### 1. `team_b_recent_win_rate`

Early-to-late conditional coefficient changes across the five prefixes:

`-1.366, -1.467, -1.271, -1.611, -1.668`

The direction is negative in **all five** prefixes.

Development-era supporting bootstrap:

- early coefficient: `1.785604`
- late coefficient: `-0.324813`
- delta: `-2.110418`
- approximate bootstrap 95% interval: `[-2.411601, -0.433933]`

### 2. `team_b_runs_conceded_per_ball`

Early-to-late conditional coefficient changes:

`-0.643, -0.592, -0.491, -0.473, -0.904`

The direction is negative in **all five** prefixes.

Development-era supporting bootstrap:

- early coefficient: `0.940996`
- late coefficient: `-0.647730`
- delta: `-1.588726`
- approximate bootstrap 95% interval: `[-2.219152, -0.382121]`

### 3. `team_b_defend_win_rate`

Early-to-late conditional coefficient changes:

`+0.238, +0.274, +0.471, +1.013, +1.107`

The direction is positive in **all five** prefixes. The coefficient transitions from negative in earlier development eras to positive in later prefixes.

Development-era supporting bootstrap:

- early coefficient: `-0.876185`
- late coefficient: `0.417318`
- delta: `+1.293503`
- approximate bootstrap 95% interval: `[0.487051, 1.698471]`

## What did not qualify

The remaining O0 components did not meet the reproducibility rule. Several showed sizable early-vs-late coefficient differences, but the direction was not stable across the five expanding-prefix diagnostics and/or the supporting uncertainty included zero.

Therefore we do **not** select them for the next hypothesis.

## Important caveat: positional asymmetry

The three identified components are `team_b_*` fields. In the O0 contract, team A/team B are positional representations derived from the match record; they are not semantic home/away roles.

Therefore we must **not** immediately interpret these three positional coefficients as three independent cricket mechanisms.

The observed subset may partly reflect:

- positional coding;
- multicollinearity among paired A/B features;
- the way the signed strength feature is constructed;
- genuine asymmetric temporal relationships.

The next diagnostic should therefore transform the candidate signals into a semantically symmetric representation and test whether the drift survives.

## Decision

**A small reproducible subset has been identified:**

1. `team_b_recent_win_rate`
2. `team_b_runs_conceded_per_ball`
3. `team_b_defend_win_rate`

But this is **not yet an O14 hypothesis**.

### Next step

Test whether the observed drift survives conversion to semantically symmetric signed/relative features. Only if it survives that control should an O14 contract be frozen.

O0 remains frozen throughout.

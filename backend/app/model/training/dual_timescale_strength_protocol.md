# T20 Dual-Timescale Strength Diagnostic

## Purpose

Test whether the Challenger-B gain is better explained by a two-timescale
strength state than by a single faster Elo K.

## Representation

Maintain two leakage-safe Elo states for every team:

- slow state: K=20
- fast state: predeclared fast K (men=80, women=160)

The logistic model receives the slow and fast team/opponent states and their
differences. No other model feature changes.

## Why this is not another arbitrary K sweep

The slow state preserves persistent team quality while the fast state tracks
recent strength changes. The model can learn whether the long-run and recent
states contain distinct predictive information instead of forcing one K to
represent both.

## Safeguards

- states are computed strictly before each match;
- update occurs only after the result is known;
- fast K is fixed from the already completed Challenger-B validation selection;
- no test or future-holdout selection;
- no calibration;
- V0/W0 artifacts are untouched.

## Decision gate

The dual-timescale representation is only a candidate if it improves
chronological validation and survives all five rolling-origin evaluations and
the independent future holdout on log loss/Brier without sacrificing the
existing Challenger-B strength gain. Otherwise reject it and do not continue
adding strength-state complexity.

# Model W0 — Women's T20 protocol

Status: **frozen reference; production probability strategy selected**.

## Population

The retained Cricsheet T20 corpus contains 2,114 women's matches. Of these:

- 2,066 have a recorded winner and are trainable under the current binary-outcome contract.
- 35 are no-results.
- 13 are ties.

The 2,066 trainable matches are ordered chronologically and split 70/15/15:

- Train: 1,446
- Validation: 310
- Test: 310

## Feature contract

W0 uses the same 13 leakage-safe pre-match features as the frozen men's v0 architecture:

1. team_elo
2. opponent_elo
3. elo_difference
4. team_form_3
5. team_form_5
6. team_form_10
7. venue_team_win_rate
8. venue_bat_first_win_rate
9. head_to_head_win_rate
10. batting_run_rate
11. bowling_run_rate
12. batting_wicket_rate
13. bowling_wicket_rate

The stateful engines are updated only after a completed match, so the current match's outcome and deliveries cannot enter its own feature row.

## Model

- StandardScaler
- LogisticRegression(max_iter=2000)
- **Production probability output: raw LogisticRegression probability; no calibration layer**
- Validation-only calibration experiments were performed with raw, Platt, and isotonic candidates.
- The untouched baseline test and final chronological holdout were not used for calibrator selection.

## Calibration decision

Platt was selected by validation-only 5-fold OOF scoring on both evaluation setups, but it failed to improve the final chronological holdout. Raw probabilities won the final holdout on accuracy, log loss, Brier, and AUC. Isotonic improved only ECE while materially worsening the primary metrics.

Therefore **no W0 calibrator is promoted to production**. The detailed evidence is recorded in `w0_calibration_decision_report.md`.

## Promotion rule

W0's predictive implementation is frozen. Production should use the raw model probabilities until a future calibration experiment demonstrates stable out-of-sample benefit. This decision does not modify or replace frozen men's Model v0.

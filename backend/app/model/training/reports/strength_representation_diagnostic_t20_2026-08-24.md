# T20 Strength Representation Diagnostic

Date: 2026-08-24  
Status: diagnostic-only; V0/W0 unchanged

## Corpus and protocol

- Corpus SHA-256: `e868d332681b38df6f39376e6d7daf14143c57fc775abbf1cc830d8bb80dd997`
- Eligible matches: 3,411 men's; 2,066 women's.
- K grid: 20, 40, 60, 80, 120, 160, 240, 320.
- Main selection: 70% train / 15% validation / 15% test; validation log loss only.
- Rolling origins: 50%, 55%, 60%, 65%, 70% train boundaries; next 10% validation; following 10% test.
- No test or future observation was used to select K.

## Finding 1 — Faster strength responsiveness is real

On the main chronological validation split, K=80 is the winner for men's T20 and K=160 for women's T20. K=20 is substantially worse on validation log loss for both populations.

Fixed selected K also beats K=20 in every rolling-origin test window on log loss, Brier and AUC for both genders.

## Finding 2 — A universal K is not stable

Men's rolling-origin validation winners:

- Origin 1: K=160
- Origin 2: K=160
- Origin 3: K=160
- Origin 4: K=120
- Origin 5: K=120

Women's:

- Origin 1: K=160
- Origin 2: K=120
- Origin 3: K=80
- Origin 4: K=160
- Origin 5: K=240

Therefore the evidence supports **time-varying responsiveness**, not another arbitrary choice of one fixed K.

## Finding 3 — Elo is materially predictive

Removing the three Elo-derived features (`team_elo`, `opponent_elo`, `elo_difference`) from the selected-K model materially worsens validation log loss in every rolling origin for both genders.

Men's Elo removal increases validation log loss by 0.0282–0.0488 across the five origins. Women's increases it by 0.0150–0.0455.

On the main test, the selected-K model also materially outperforms the no-Elo ablation.

## Finding 4 — The strength state is becoming more dispersed

The later-period distribution of `elo_difference` is substantially wider under the faster-adapting K than under K=20.

For men's T20, standard deviation of Elo difference in 2022→2026 changes from approximately 84.8, 95.1, 84.5, 101.1, 105.3 at K=20 to 168.0, 180.1, 181.2, 213.9, 211.1 at K=80.

For women's T20, the corresponding values change from approximately 113.1, 106.7, 103.9, 90.3, 120.2 at K=20 to 262.5, 241.5, 260.9, 313.2, 322.0 at K=160.

This is evidence that the larger K is not merely changing a coefficient: it is materially changing the distribution and responsiveness of the team-strength state.

## Finding 5 — The three Elo features are redundant by construction

`elo_difference` is mathematically derived from `team_elo - opponent_elo`, so high correlation is expected. The observed correlations are approximately:

Men: team/opponent 0.460; team/difference 0.528; opponent/difference -0.511.  
Women: team/opponent 0.501; team/difference 0.497; opponent/difference -0.502.

This does not by itself justify deleting a feature, but it confirms that the current strength representation is a single latent Elo state expressed three ways rather than three independent strength measurements.

## Reconciliation finding

The current-source reconstruction reproduces the preserved raw men's K=80 test metrics exactly: accuracy 0.7173489, log loss 0.5610395, Brier 0.1897584, AUC 0.7917946 and ECE 0.0597996.

The preserved Challenger B report labels 0.5532063 log loss / 0.1867927 Brier / 0.0457976 ECE as `challenger_test`, but the preserved male calibration report explicitly identifies those values as **calibrated** and identifies 0.5610395 as raw. Therefore the Challenger B report has an internal metric-label inconsistency. This diagnostic treats 0.5610395 as the raw B reference.

## Decision

Do **not** create another fixed-K Challenger C.

The evidence now supports a narrower next hypothesis:

> A scalar Elo K is an inadequate representation of changing T20 team strength; the model should investigate a time-varying or otherwise state-based strength representation while preserving strict chronological leakage boundaries.

The next experiment should therefore test a principled strength-state formulation, with all non-strength features and the estimator held constant. V0/W0 remain unchanged until that experiment is evaluated through the established chronological test, rolling-origin and future-holdout protocol.

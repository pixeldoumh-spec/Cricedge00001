# T20 Strength Representation Diagnostic

Status: diagnostic-only. No V0/W0 artifact is changed.

## Question

Determine whether Challenger B's improvement is evidence of genuine temporal
team-strength adaptation, rather than an arbitrary benefit from a larger Elo K.

## Locked variables

- T20 corpus and chronological population remain unchanged.
- Men's Challenger B K=80; women's K=160 remain the fixed B references.
- Existing 13-feature contract and logistic estimator remain unchanged.
- No test or future-holdout outcome is used for selecting a K or feature representation.

## Diagnostics

1. **Rolling-origin K sensitivity**
   - Evaluate the predeclared K grid on validation only for every rolling origin.
   - Record the winning K per origin.
   - Measure whether the selected K is stable or systematically increases/decreases by era.

2. **Strength-state drift**
   - Summarize chronological distributions of team Elo, opponent Elo and Elo difference.
   - Report mean, standard deviation and match counts by calendar era.
   - Do not interpret drift alone as predictive improvement; it is descriptive evidence.

3. **Feature redundancy**
   - Correlate team Elo, opponent Elo and Elo difference.
   - This determines whether the current three-column strength representation is
     effectively carrying one latent quantity multiple times.

4. **Representation attribution**
   - If the rolling-origin evidence shows stable faster adaptation, the next
     experiment may compare alternative semantically meaningful strength states.
   - If K winners are unstable or the effect is concentrated in another feature,
     do not promote a new strength representation yet.

## Decision gate

A future strength challenger is justified only if the diagnostic shows a
reproducible temporal pattern that explains why K=80/K=160 beats K=20.

The frozen test and future holdout are evaluation-only. They cannot select the
next representation.

# CPL Historical Recovery Ledger

Cricsheet's current coverage snapshot reports 419 of 428 men's Caribbean Premier League matches, leaving 9 missing from its current ball-by-ball coverage. The missing page identifies these nine matches:

| Date | Match | Status |
|---|---|---|
| 2013-08-08 | Barbados Tridents vs St Lucia Zouks | Cricsheet missing |
| 2014-07-12 | St Lucia Zouks vs Jamaica Tallawahs | Cricsheet missing |
| 2014-07-17 | Red Steel vs Guyana Amazon Warriors | Cricsheet missing |
| 2014-07-25 | Antigua Hawksbills vs Barbados Tridents | Cricsheet missing |
| 2016-07-05 | Patriots vs Barbados Tridents | Cricsheet missing |
| 2016-07-07 | Jamaica Tallawahs vs Guyana Amazon Warriors | Cricsheet missing |
| 2016-07-09 | Patriots vs Guyana Amazon Warriors | Cricsheet missing |
| 2016-07-12 | St Lucia Zouks vs Guyana Amazon Warriors | Cricsheet missing |
| 2016-07-23 | Barbados Tridents vs St Lucia Zouks | Cricsheet missing |

## Recovery policy

1. Do not fabricate missing ball-by-ball events.
2. Search authoritative historical scorecards first.
3. Recover complete scorecard-level targets where possible: winner, innings totals, player runs, fours, sixes, top batter, top bowler, and Player of the Match.
4. Only add ball-by-ball-derived targets (overs 1-6, exact boundary counts, live-replay-compatible fields) if a trustworthy ball-by-ball source is recovered.
5. Record the source URL, retrieval date, source type, and a local SHA-256 of any recovered artifact.
6. Preserve a field-level provenance map so a recovered match can be excluded from any target whose source does not support the required granularity.
7. Never mix a scorecard-only recovery into the ball-by-ball training rows as if it were equivalent to native Cricsheet JSON.

## Coverage interpretation

The nine missing matches represent only about 2.1% of the current 428-match coverage denominator. However, the effect is target-specific: a match can be usable for some markets and unusable for others. Therefore the final corpus should report coverage separately for each target family rather than simply reporting a single match-count percentage.

## Acceptance rule

A recovered match enters the canonical CPL corpus only after schema validation and target-level provenance checks. Until then it remains in this recovery ledger and is excluded from model training.

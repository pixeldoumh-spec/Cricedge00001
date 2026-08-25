# CPL Outcome Corpus Build Specification v0.1

## Scope

Build the smallest high-quality historical corpus that completely supports the fixed CPL outcome contract, while preserving raw provenance and enough ball-by-ball information to regenerate every target.

## Required target families

1. Match winner, including Super Over resolution where applicable.
2. Player of the Match.
3. First-innings team total.
4. First-innings player runs for every participating batter.
5. First-innings overs 1–6 team totals.
6. Match total fours.
7. Match total sixes.
8. Most fours by team, including draw/tie state.
9. Most sixes by team, including draw/tie state.
10. Team containing the top batter.
11. Team containing the top bowler.

## Raw-to-derived principle

Keep raw match JSON as the immutable source layer. Derived target rows are reproducible products, not the source of truth.

Every derived row must retain:

- source match identifier;
- source archive SHA-256;
- source member/path;
- match date;
- season;
- teams;
- venue;
- target family;
- prediction timing class;
- reconstruction version.

## Historical match inclusion

Include men's CPL matches covered by the frozen source corpus from the first covered season onward. Do not mix WCPL into the men's corpus.

Cricsheet's current coverage page reports 419 of 428 men's CPL matches, while its downloads page can show a different downloadable subset count at a different snapshot. The exact downloaded archive therefore controls the local corpus; coverage pages are reconciliation references, not substitutes for the archive.

The nine currently listed missing CPL matches must be reconciled explicitly. They may remain missing if no reliable ball-by-ball source can be found, but they must appear in a missing-match ledger.

## Missing-match recovery hierarchy

For each missing match, attempt:

1. official CPL scorecard/statistics;
2. established cricket scorecard provider with complete ball-by-ball;
3. established archival scorecard/database;
4. secondary source only when it can be independently cross-checked.

Do not fabricate delivery-level data from final scorecards. If only a final scorecard exists, it may support match-result/POM enrichment but cannot repair ball-level targets such as over totals, fours, or sixes.

## Player of the Match

Use the explicit award field from the raw source when present. If absent, recover the award from a source with an explicit award designation. Never infer Player of the Match from runs/wickets.

## Target reconstruction rules

### Runs
Use delivery `runs.total` for team innings totals and `runs.batter` for batter totals.

### Over totals
Use `runs.total` grouped by innings and over number. Preserve wides/no-balls as runs in the over total because bookmaker innings-over totals represent scoreboard runs, not legal-ball-only runs.

### Fours and sixes
Count batter-run values of exactly 4 and 6 respectively. Extras do not create a batter four/six target.

### Most fours/sixes
Compare the two teams' final counts. If equal, retain `draw` rather than forcing a team label.

### Top batter
Define the top batter from the highest individual runs in the match. If multiple players tie at the highest runs, preserve all tied players in a deterministic tie representation; do not arbitrarily select one.

### Team with top batter
Map the top-batter result back to the player's batting team. A tied top-batter outcome must remain explicitly tied/ambiguous if the bookmaker market has no single deterministic resolution.

### Top bowler
Define bowling wickets from dismissals credited to the bowler. Exclude run outs, retired hurt/out, and obstructing-the-field dismissals. Preserve ties rather than selecting a winner arbitrarily.

### Team with top bowler
Map the top-bowler result to the bowling team, i.e. the opposition to the batting innings in which the wicket occurred. Never attribute a wicket to the batting team merely because the delivery appears inside that innings object.

## Super Overs

Super-over innings must be identified separately from ordinary innings. For the winner target, use the official match outcome. Do not merge Super Over runs into the ordinary first-innings target.

If a bookmaker market says winner including Super Over, the target is the final official winner, not the winner after regulation innings alone.

## Corpus quality gates

A corpus is not frozen until:

- duplicate match identities are zero or explained;
- every included match has a date and two teams;
- target reconstruction passes invariant checks;
- team/batter/bowler identities are normalized;
- first-innings over numbering is validated;
- fours/sixes reconcile against innings/batting aggregates where source aggregates exist;
- final innings totals reconcile to scorecard/source totals;
- winner reconciles to official result;
- POM is explicit rather than inferred;
- missing/ambiguous records have an exclusion reason;
- source archive hash is recorded;
- parser/reconstruction version is recorded.

## Do not include yet

- bookmaker odds as features or labels;
- 2026 prospective results while evaluation is open;
- live delivery timestamps that are not available from the historical source;
- ball-tracking variables not present in the source;
- guessed player roles/styles;
- inferred POM labels;
- synthetic repair of missing ball-by-ball matches.

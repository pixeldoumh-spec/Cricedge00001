# CPL Canonical Corpus Schema v0.1

The canonical training corpus is target-driven and retains provenance for every row.

## Match-level identity

- `match_key`
- `match_date`
- `season`
- `competition`
- `match_number`
- `venue`
- `team_a`
- `team_b`
- `source_kind`
- `source_artifact`
- `source_sha256`
- `source_revision`

## Match outcomes

- `winner`
- `winner_including_super_over`
- `super_over_used`
- `player_of_match`

## Innings outcomes

For each innings:

- `batting_team`
- `innings_number`
- `runs`
- `wickets`
- `balls`
- `fours`
- `sixes`

## Player batting outcomes

For each batter innings:

- `player_id`
- `player_name`
- `batting_team`
- `innings_number`
- `runs`
- `balls`
- `fours`
- `sixes`
- `dismissed`

## Over outcomes

For innings 1 and the bookmaker-covered opening six overs:

- `innings_number`
- `batting_team`
- `over_number`
- `over_runs`
- `over_fours`
- `over_sixes`
- `legal_balls`

An incomplete over is retained with an explicit completion flag rather than
being silently padded.

## Bowling outcomes

For each bowler innings:

- `player_id`
- `player_name`
- `bowling_team`
- `innings_number`
- `balls`
- `runs_conceded`
- `wickets`

## Derived comparative labels

- `top_batter_player`
- `top_batter_team`
- `top_bowler_player`
- `top_bowler_team`
- `most_fours_team_or_draw`
- `most_sixes_team_or_draw`

Ties are preserved explicitly. They are not broken by arbitrary ordering.

## Provenance and quality flags

- `has_ball_by_ball`
- `has_player_of_match`
- `has_complete_first_six_overs`
- `has_complete_innings_totals`
- `has_complete_batting`
- `has_complete_bowling`
- `target_eligible_*` flags per market family
- `exclusion_reason` when a target is not eligible.

## Critical rule

The canonical corpus is not a single rectangular table where missing targets
are filled. Different market families may have different eligible subsets.
Every model training job must select rows using the target-specific eligibility
flag and preserve the corresponding provenance.

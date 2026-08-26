# CPL Derived Target Schema v0.1

The corpus should expose normalized target records without discarding the raw JSON.

## Match-level record

- `match_id`
- `date`
- `season`
- `team_a`
- `team_b`
- `venue`
- `winner`
- `winner_resolution` (`regulation`, `super_over`, other explicit source state)
- `player_of_match[]`
- `source_archive_sha256`
- `source_member`
- `reconstruction_version`

## Innings-level record

- `match_id`
- `innings_number`
- `batting_team`
- `bowling_team`
- `runs`
- `wickets`
- `overs_completed`
- `fours`
- `sixes`
- `is_super_over`

## Player-batting record

- `match_id`
- `innings_number`
- `team`
- `player`
- `runs`
- `balls`
- `fours`
- `sixes`
- `dismissed`
- `dismissal_kind`

## Over record

- `match_id`
- `innings_number`
- `batting_team`
- `over_number_zero_based`
- `over_number_one_based`
- `runs`
- `wickets`
- `fours`
- `sixes`
- `legal_balls`

## Bowling record

- `match_id`
- `innings_number`
- `bowling_team`
- `bowler`
- `runs_conceded`
- `legal_balls`
- `wickets`
- `fours_conceded`
- `sixes_conceded`

## Comparative target record

- `match_id`
- `market_family`
- `winner_entity_or_draw`
- `tied_entities[]`
- `resolution_status`
- `source_archive_sha256`
- `reconstruction_version`

## Important distinction

`player_of_match` is an explicit award target.
`top_batter` and `top_bowler` are performance-derived targets.
They must never be conflated.

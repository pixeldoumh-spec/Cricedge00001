# Cricsheet T20 schema reconnaissance

Source: official Cricsheet JSON format documentation and T20 download catalogue.

## Observed top-level structure

A match JSON object contains:

- `meta`
- `info`
- `innings`

The current documented JSON format is **1.2.0**.

## `info` fields useful for the pre-match model

- `dates`
- `event`
- `gender`
- `match_type`
- `overs`
- `season`
- `team_type`
- `teams`
- `venue`
- `city` (when available)
- `toss`
- `outcome`
- `players`
- `registry`
- `player_of_match` (post-match only; never a training feature for pre-match prediction)
- `missing` (data-quality signal)

## `innings` / ball-level fields

Each innings contains a batting `team` and `overs`. Each over contains `deliveries`.
A delivery provides:

- `actual_delivery`
- `batter`
- `bowler`
- `non_striker`
- `runs.batter`
- `runs.extras`
- `runs.total`
- optional `extras`
- optional `wickets`
- optional `review`
- optional `replacements`

## Immediate model implications

This source is sufficient to derive historical team/player/venue statistics and
ball-derived batting/bowling features. It also contains toss and lineup context.

The parser must preserve the original match object until normalization so that
we can handle optional fields, missing data, ties/no-results, shortened matches,
penalty runs, super overs, and player replacements explicitly.

## Data policy

The raw Cricsheet archive is an external training input and must not be committed
to the Git repository. The repository should contain only ingestion code,
normalization logic, compact development fixtures, and reproducible dataset
manifests/hashes.

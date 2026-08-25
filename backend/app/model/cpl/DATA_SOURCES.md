# CPL Outcome Engine — Data Sources

## Historical source: Cricsheet

Primary historical source: Cricsheet JSON ball-by-ball match data.

Cricsheet identifies JSON as its main/official match format and describes it
as the most complete of its supplied formats. The current downloads page lists
Caribbean Premier League men's matches as a dedicated club-competition JSON
subset. Coverage changes as missing historical matches are recovered, so the
exact downloaded archive and SHA-256 must be frozen locally before training.

Current web audit observed on 2026-08-25:

- men's CPL: 407 matches on the downloads page snapshot used for this research
  audit;
- Cricsheet's coverage page reports 419 of 428 men's CPL matches checked/provided
  in its current coverage snapshot, demonstrating that coverage figures can
  change between page snapshots;
- Cricsheet's missing-match page explicitly lists nine historical men's CPL
  matches currently missing in its coverage snapshot.

Therefore the model must never identify a corpus merely as "CPL data". It must
record:

- exact source URL/page;
- retrieval timestamp;
- archive filename;
- archive SHA-256;
- match count;
- earliest/latest match date;
- coverage/missing-match status;
- parser version/commit.

## Live source

The 2026 prospective stream is a separate source layer. Live 2026 results and
fixtures must be preserved with source, timestamp, and retrieval snapshot.
They must not be silently merged into the historical training archive.

## Bookmaker source

Bookmaker markets supplied by the user define the target-market contract.
Bookmaker odds/lines are benchmark observations only. They are not training
labels and must not be fed into model fitting.

# CPL Historical Corpus Enrichment Protocol

Cricsheet JSON is the primary ball-by-ball source. It is preferred because JSON
is Cricsheet's official/main format and is the most complete of its supplied
formats. citeturn0search0

## Source hierarchy

1. **Cricsheet JSON** — primary source for deliveries, innings, players, result,
   and any award metadata present in the file.
2. **CricketArchive scorecards** — secondary verification/recovery source for
   scorecard-level fields such as Player of the Match and innings summaries.
3. **ESPNcricinfo/CPL/other authoritative scorecards** — secondary recovery or
   cross-check when a Cricsheet target is absent/ambiguous.
4. General statistical pages — discovery only; never preferred over a primary
   scorecard for a row-level label.

## Enrichment rule

A missing field is never silently filled.

Every enrichment row must contain:

- stable match key;
- field being enriched;
- original value (usually null);
- recovered value;
- source URL;
- source retrieval date;
- source type;
- confidence (`verified`, `corroborated`, `unresolved`);
- reviewer/automation note.

## Player of the Match

Player of the Match is an explicit award target. It must come from match-level
award metadata or an authoritative scorecard/presentation record. It must not
be inferred from runs, wickets, or a model score.

For example, CricketArchive scorecards expose a dedicated `Player of the
Match` field, demonstrating a suitable row-level recovery source. citeturn4search3turn4search9

## Missing historical matches

Cricsheet's current coverage page reports 419 of 428 men's CPL matches and its
missing-match page lists nine historical men's CPL matches. citeturn0search9turn0search5

Those missing matches are not to be fabricated or silently discarded. We first
attempt row-level recovery from authoritative scorecards. If complete
ball-by-ball data cannot be recovered, the match remains in a coverage ledger
with `status=missing_ball_by_ball` and is excluded from targets that require
ball-level reconstruction.

## 2026 separation

CPL 2026 results/fixtures are prospective evaluation data. They are stored in a
separate ledger and cannot enter historical training while the prospective
evaluation remains open.

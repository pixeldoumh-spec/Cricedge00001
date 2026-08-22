# Men's T20 expansion reconciliation

## Result

The retained Cricsheet T20 archive contains **3,526 men's T20 matches** and **2,114 women's T20 matches**.

The frozen Model v0 population contains **3,411 men's matches**. The difference is exactly **115 matches**.

Those 115 matches are not missing-data records. They are the men's matches without a decisive winner:

- **77 no-result matches**
- **38 tied matches**

Therefore the frozen v0 dataset is equivalent to the archive's men's matches with `outcome.winner` present. This explains the 3,411-row training population without inventing an additional competition/date filter.

## Integrity check

| Population | Matches |
| --- | ---: |
| Men's T20 in retained archive | 3,526 |
| Men's decisive matches | 3,411 |
| Men's no-results | 77 |
| Men's ties | 38 |
| Men's excluded total | 115 |
| Women's T20 | 2,114 |

3,411 + 77 + 38 = 3,526.

## Why v0 excludes these 115

The current binary target is a two-class match-winner target. A no-result has no winner, and a tie does not provide a unique winning team. Including either class in the current binary logistic-regression target would require changing the target definition and evaluation protocol.

Consequently, these 115 matches **must not be silently appended to v0**. Doing so would change the target contract and invalidate the frozen 3,411-match reproduction.

## Chronological boundary

The 115 excluded matches occur throughout the historical archive rather than forming one contiguous time block. They therefore cannot be treated as a simple future holdout or appended training tail.

The excluded matches are retained in the raw corpus and remain available for future research involving:

- three-class outcomes (home win / away win / tie)
- no-result-aware modeling
- match-state/reliability analysis

## Competition coverage

The excluded set spans international series, ICC events, regional qualifiers and domestic/associate competitions. Examples include ICC Men's T20 World Cup events, bilateral tours, regional qualifiers and tri-nation competitions.

The largest competition-level groups in the excluded set include:

- ICC Men's T20 World Cup Sub Regional Africa Qualifier — 7
- ICC World Twenty20 — 5
- West Indies tour of New Zealand — 4
- ICC Men's T20 World Cup — 4
- India tour of Australia — 3
- England tour of New Zealand — 3
- India tour of New Zealand — 3
- Pakistan tour of West Indies — 3

## Decision

**Model v0 remains unchanged.**

The correct next men's expansion experiment is therefore **not** to add these 115 matches to v0. There are no additional decisive men's matches in the retained corpus outside the 3,411-match v0 population.

The meaningful expansion tracks are:

1. build a separate no-result/tie-aware research target if desired; and
2. build the separate women's T20 model from the 2,114 women's matches.

Any model using either track receives a new version and must not modify the frozen v0 artifact.

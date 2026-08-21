# CricEdge Product Requirements

## Original problem statement
CricEdge is a read-only cricket analytics engine that normalizes fixtures, odds, historic data, model probabilities, same-game combinations, multi-fixture portfolios, historic performance, and model insights through a no-auth API and React UI. It must clearly frame all outputs as analytical and educational, not wagering advice.

## Architecture decisions
- React SPA with React Router, Recharts, Lucide icons, and a dense dark analytics interface.
- FastAPI service with read-only `/api` endpoints and Pydantic response models.
- Curated sample records currently power the MVP while the odds-provider adapter remains ready for a compliant provider integration.
- Existing `REACT_APP_BACKEND_URL` and `MONGO_URL` environment variables remain unchanged.

## User personas
- Cricket analyst comparing upcoming fixtures and model signals.
- Data science/product stakeholder reviewing calibration and feature importance.
- Research or education user exploring transparent, non-wagering probability outputs.

## Core requirements (static)
- Fixture explorer with upcoming matches, odds, probabilities, confidence tags, and source context.
- Fixture detail with event probabilities and fixture-specific same-game combinations.
- Cross-fixture analytical portfolios.
- Historic performance metrics, trend chart, and market breakdown.
- Model registry view with feature importance.
- No authentication, wager controls, stake sizing, or user data.
- Prominent analytical disclaimer and responsive mobile experience.

## Implemented (2026-08-21)
- Replaced starter screen with CricEdge dashboard and four navigable views.
- Added fixture, prediction, portfolio, history, and model API endpoints.
- Added fixture-derived prediction content for all curated fixtures.
- Added responsive fixed mobile navigation rail and unique data-testid coverage for key flows.
- Added API-ready sample data labeling and read-only disclaimers.
- Validated desktop and mobile navigation, detail flow, API regressions, and no-overflow behavior.

## Prioritized backlog
- P0: Connect a compliant bookmaker/odds provider through a backend-only adapter. **Done 2026-08-21: The Odds API live adapter is active.**
- P1: Ingest and persist Cricsheet historic data with scheduled normalization jobs.
- P1: Replace curated model records with a reproducible trained model artifact and backtest pipeline.
- P2: Add live odds refresh, provider attribution links, and freshness/staleness states.
- P2: Add league/market filters and historical date range controls.

## Remaining next tasks
- Confirm the odds provider and credentials/terms before enabling live data.
- Add MongoDB serving snapshots and TTL cleanup once live ingestion is enabled.
- Add model version comparison and exportable analytical reports.

## Feature addition (2026-08-21)
- Added The Odds API adapter with server-only credential handling, cricket sport-key polling, h2h decimal odds normalization, provider error mapping, and live/sample status flags.
- `/api/fixtures` now returns live upcoming provider events when available; the curated fallback remains code-only and is clearly marked if ever used.
- Verified live provider response, browser rendering, fixture detail navigation, mobile layout, and absence of key exposure.

## 2026-02-21 — Format filter + format-aware predictions
- Added `GET /api/fixtures/formats` returning per-format counts and profile blurbs (T20, ODI, Test, Hundred).
- `GET /api/fixtures?format=T20|ODI|Test|Hundred` filters normalized live/sample fixtures.
- Introduced `FORMAT_STRATEGY` registry: format-specific run lines (T20 168.5, Hundred 148.5, ODI 276.5, Test 340.5 first-innings), batter thresholds (30+/25+/50+/60+), driver sets (powerplay vs middle-overs vs session momentum), and an extra "Draw not ruled out" market for Test and "Team score band" for ODI.
- Sport-key → (format, competition) resolver removes hard-coded T20 assumption on live feed events; added CPL/PSL sport keys.
- Added a 30s in-memory cache for The Odds API response to prevent duplicate provider calls between /fixtures and /fixtures/formats and to gracefully fall back on transient provider errors.
- Frontend: `FormatFilter` chip row on the fixture explorer, active-state chip styling, empty-format disable, per-format loaded count. Detail view now surfaces the format strategy banner and driver pills per event.
- Verified: T20 filter → 2 CPL fixtures; Test filter → 3 fixtures with 3-way h2h (incl. Draw); Test predictions include the Draw market at 22% and 340.5 first-innings run line.

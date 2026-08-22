# CricEdge Backend Architecture Audit

## Scope

Audit of the current FastAPI backend before production-oriented refactoring. This document records the current architecture, risks, and the extraction plan. No API contract is intentionally changed by this audit.

## Current architecture

`backend/server.py` currently owns most backend responsibilities:

- FastAPI application and `/api` router creation
- MongoDB client/database initialization
- CORS configuration
- format profiles and supported formats
- team/player registry
- sport/competition mapping
- large format-specific market catalogue
- market construction and model overrides
- fixture Pydantic schemas
- sample fixture data
- live odds normalization
- external Odds API calls and in-memory caching
- fixture endpoints
- prediction/market endpoint

The model implementation is separately located in `backend/cric_model.py`, but it also loads environment variables and creates its own MongoDB dependency path for model operations.

## Priority findings

### P0 — Security boundary

1. No authentication/authorization boundary is visible around backend operations.
2. CORS currently accepts `*` by default and permits all methods/headers.
3. External provider credentials are read from environment variables, which is correct, but the provider call path lives directly inside the API module.
4. There is no explicit rate-limit layer at the API boundary.

### P0 — Runtime/data correctness

1. `fetch_live_fixtures()` can raise provider-related `HTTPException`s directly from the data-fetching function.
2. A missing live-provider configuration silently switches the application to sample fixtures. This is useful for development but should be explicit in production so a stale/demo dataset cannot be mistaken for live data.
3. Live data is cached in process memory (`_LIVE_CACHE`), which is not shared across workers and disappears on restart.
4. Sample fixture timestamps are generated when the module is imported, so they are synthetic and process-start dependent.
5. Venue data for normalized live events is currently `Venue pending` rather than a verified provider venue.

### P1 — Architecture

`server.py` is a monolithic module containing transport, domain, integration, configuration, schema, and data responsibilities. This makes testing and safe changes harder.

Recommended boundaries:

```text
app/
├── main.py                 # FastAPI app assembly only
├── api/
│   ├── fixtures.py         # HTTP routes
│   ├── predictions.py      # HTTP routes
│   └── health.py           # health/readiness routes
├── core/
│   ├── config.py           # environment/settings
│   ├── logging.py          # structured logging
│   └── errors.py           # API exception mapping
├── db/
│   └── mongo.py            # database lifecycle/dependency
├── schemas/
│   ├── fixture.py          # response/request contracts
│   └── prediction.py       # prediction/market contracts
├── services/
│   ├── fixture_service.py
│   ├── prediction_service.py
│   └── odds_service.py
├── domain/
│   ├── markets.py          # market catalogue/domain rules
│   └── formats.py          # format profiles/mappings
└── integrations/
    └── odds_provider.py    # external provider adapter
```

`cric_model.py` should eventually become a model service/domain module that receives a database/repository dependency instead of owning environment/database setup itself.

## API contract currently covered by tests

The existing tests cover:

- `GET /api/fixtures`
- `GET /api/fixtures?format=...`
- `GET /api/fixtures/formats`
- `GET /api/fixtures/{fixture_id}`
- `GET /api/fixtures/{fixture_id}/predictions`
- basic response/market/selection structure

The test suite is useful but currently validates mostly happy-path response shapes. It should later add provider failure, malformed provider payload, schema validation, cache behavior, and database failure cases.

## Recommended extraction sequence

### Phase A — zero/low behavior change

1. Extract configuration into `app/core/config.py`.
2. Extract Pydantic response schemas into `app/schemas/fixture.py` and prediction schemas.
3. Extract MongoDB lifecycle into `app/db/mongo.py`.
4. Extract the Odds API adapter into `app/integrations/odds_provider.py`.
5. Extract market/domain catalog into `app/domain/markets.py`.
6. Extract fixture and prediction business logic into services.
7. Convert `server.py` into `app/main.py` plus route registration.

### Phase B — production hardening

8. Add explicit application settings validation.
9. Add structured logging and request correlation IDs.
10. Add centralized exception handlers.
11. Add authentication and admin authorization if admin operations are introduced.
12. Add rate limiting.
13. Harden CORS and security headers.
14. Add readiness/health checks for MongoDB and provider dependencies.

### Phase C — data/model hardening

15. Separate sample/demo data from live data.
16. Version prediction/model artifacts and record provenance.
17. Move provider caching to a shared cache if multi-worker deployment requires it.
18. Add model calibration and monitoring metrics.

## Important rule for the refactor

Keep the existing `/api/...` URLs and response shapes stable while extracting modules. Each extraction should be followed by backend tests before the next extraction.

## First implementation step

The safest first code extraction is **configuration + schemas**, because both can be moved behind stable imports without changing business behavior. Do not begin by rewriting the entire `server.py`.

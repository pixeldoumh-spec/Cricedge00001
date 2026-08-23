# CricEdge Security & Reliability Remediation

**Updated:** 2026-08-23

## Completed in this pass

- Replaced wildcard CORS with environment-controlled origins.
- Added production protection against wildcard CORS configuration.
- Added bounded fixture-ID validation for API path parameters.
- Added strict Pydantic validation for prediction model features, including missing/extra-key rejection and finite-number checks.
- Added request rate limiting (120 requests/minute/IP/process) and documented the multi-instance limitation.
- Added structured request timing and unhandled-error logging.
- Added MongoDB connection pooling, connection timeout, socket timeout, and retryable writes.
- Added a FastAPI lifespan handler for MongoDB cleanup.
- Added safe API error responses that do not expose model-artifact filesystem details.
- Added frontend API timeout and environment fallback.
- Added frontend response-shape validation for fixture and prediction queries.
- Added React error boundary recovery UI.
- Fixed the frontend/backend `strategy` response contract mismatch.
- Removed stale hard-coded dashboard performance claims.
- Added `backend/.env.example` and deterministic test environment bootstrap.
- Added React Query stale-time/retry policies for fixture data.

## Intentionally not added yet

### Authentication / authorization
The current public API has no administrative mutation or user-private data endpoint. Authentication should be introduced when CricEdge adds protected operations such as model training, ingestion controls, user accounts, or private portfolios. Public read-only fixture and prediction endpoints can remain unauthenticated behind rate limiting.

### Distributed rate limiting
The current limiter is process-local. Production deployments with multiple API instances should move this control to an API gateway/CDN or Redis-backed limiter.

### Full response schemas
The prediction and fixture responses are currently normalized and validated on the frontend. The next backend contract step is to replace the remaining `dict` response types with explicit Pydantic response models once the public payload contract is frozen.

### TypeScript migration
The frontend is still JavaScript/JSX. A gradual TypeScript migration is recommended after the API contract stabilizes, starting with API payload types and feature boundaries.

## Production gate

Before public production deployment, configure real `MONGO_URL`, `DB_NAME`, `CORS_ORIGINS`, and any required provider keys through the deployment secret manager. Do not commit `.env` files or provider credentials.

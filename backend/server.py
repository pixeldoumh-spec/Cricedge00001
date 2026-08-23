"""FastAPI application entrypoint with production-safe middleware."""

from collections import defaultdict, deque
from contextlib import asynccontextmanager
import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import api
from app.core.config import cors_origins, settings
from app.db.mongo import get_mongo_client


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("cricedge.api")

_rate_window_seconds = 60
_rate_limit = 120
_rate_hits: dict[str, deque[float]] = defaultdict(deque)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Manage shared application resources for the process lifetime."""
    logger.info("Starting CricEdge API in %s mode", settings.environment)
    yield
    logger.info("Closing MongoDB client")
    get_mongo_client().close()
    _rate_hits.clear()


app = FastAPI(
    title="CricEdge Analytics API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
)

origins = cors_origins()
if not origins:
    raise RuntimeError("At least one CORS origin must be configured")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.middleware("http")
async def request_guard(request: Request, call_next):
    client_host = request.client.host if request.client else "unknown"
    now = time.monotonic()
    hits = _rate_hits[client_host]
    while hits and now - hits[0] >= _rate_window_seconds:
        hits.popleft()
    if len(hits) >= _rate_limit:
        return JSONResponse(status_code=429, content={"detail": "Too many requests"})
    hits.append(now)

    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Unhandled API error: %s %s", request.method, request.url.path)
        raise
    finally:
        elapsed_ms = (time.perf_counter() - started) * 1000
        logger.info("%s %s %.1fms", request.method, request.url.path, elapsed_ms)
    return response


@app.get("/")
def root() -> dict[str, str]:
    return {"name": "CricEdge Analytics API", "status": "ok"}


app.include_router(api)

"""HTTP API routes for CricEdge's current frontend contract."""

from typing import Any

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query

from app.data.cricket_catalogue import FORMAT_MARKETS, FORMAT_PROFILES, SUPPORTED_FORMATS
from app.db.mongo import get_database


api = APIRouter(prefix="/api")


def _json(value: Any) -> Any:
    """Convert MongoDB values into JSON-compatible values."""
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, dict):
        return {key: _json(item) for key, item in value.items() if key != "_id"}
    if isinstance(value, list):
        return [_json(item) for item in value]
    return value


def _fixture(doc: dict) -> dict:
    """Normalize a stored fixture without changing its public fields."""
    item = _json(dict(doc))
    item.setdefault("id", str(item.get("_id", "")))
    item.setdefault("competition", "Cricket")
    item.setdefault("format", "T20")
    item.setdefault("venue", "")
    item.setdefault("start_time", "")
    item.setdefault("teams", [])
    item.setdefault("status", "scheduled")
    item.setdefault("model_tag", "pending")
    item.setdefault("confidence", 0)
    item.setdefault("odds", [])
    return item


def _market_payload(fixture: dict) -> list[dict]:
    """Build the catalogue-backed market shape used by the frontend."""
    fmt = fixture.get("format") if fixture.get("format") in FORMAT_MARKETS else "T20"
    teams = list(fixture.get("teams") or [])
    home = teams[0] if teams else "Home"
    away = teams[1] if len(teams) > 1 else "Away"
    markets = []

    for template in FORMAT_MARKETS.get(fmt, []):
        market = {key: value for key, value in template.items() if key not in {"selections", "source"}}
        market["label"] = str(market.get("label", "")).format(home=home, away=away)
        market["selections"] = []
        for selection in template.get("selections", []):
            probability = float(selection.get("prob", 0))
            name = str(selection.get("name", "")).format(home=home, away=away)
            market["selections"].append({
                "key": selection.get("key"),
                "name": name,
                "price": round(100 / probability, 2) if probability else 0,
                "probability": probability,
            })
        if template.get("source") == "odds":
            market["selections"] = fixture.get("odds", [])
        markets.append(market)
    return markets


@api.get("/health")
def health() -> dict:
    return {"status": "ok", "model": {"status": "not_implemented"}}


@api.get("/fixtures")
def get_fixtures(format: str | None = Query(default=None)) -> list[dict]:
    query = {}
    if format and format != "ALL":
        query["format"] = format
    docs = get_database()["fixtures"].find(query).sort("start_time", 1)
    return [_fixture(doc) for doc in docs]


@api.get("/fixtures/formats")
def get_fixture_formats() -> dict:
    collection = get_database()["fixtures"]
    formats = []
    for key in SUPPORTED_FORMATS:
        count = collection.count_documents({"format": key})
        formats.append({
            "key": key,
            "label": key,
            "count": count,
            "profile": FORMAT_PROFILES[key],
        })
    return {"formats": formats, "total": collection.count_documents({})}


@api.get("/fixtures/{fixture_id}")
def get_fixture(fixture_id: str) -> dict:
    doc = get_database()["fixtures"].find_one({"id": fixture_id})
    if doc is None and ObjectId.is_valid(fixture_id):
        doc = get_database()["fixtures"].find_one({"_id": ObjectId(fixture_id)})
    if doc is None:
        raise HTTPException(status_code=404, detail="Fixture not found")
    return _fixture(doc)


@api.get("/fixtures/{fixture_id}/predictions")
def get_fixture_predictions(fixture_id: str) -> dict:
    fixture = get_fixture(fixture_id)
    markets = _market_payload(fixture)
    return {
        "fixture": fixture,
        "markets": markets,
        "strategy": "catalogue_baseline",
        "notice": "Model predictions are not implemented yet and are not wagering advice.",
    }

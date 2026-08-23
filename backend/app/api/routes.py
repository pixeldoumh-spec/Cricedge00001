"""HTTP API routes for CricEdge's current frontend contract."""

from math import isfinite
from typing import Any

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.data.cricket_catalogue import FORMAT_MARKETS, FORMAT_PROFILES, SUPPORTED_FORMATS
from app.db.mongo import get_database
from app.model.inference.artifact_registry import registry
from app.model.inference.service import predict as predict_model
from app.model.training.model_v0 import FEATURES


api = APIRouter(prefix="/api")


class PredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_version: str = Field(default="v0", pattern=r"^(v0|W0)$")
    features: dict[str, float] = Field(min_length=len(FEATURES), max_length=len(FEATURES))

    @field_validator("features")
    @classmethod
    def validate_features(cls, value: dict[str, float]) -> dict[str, float]:
        missing = set(FEATURES) - set(value)
        extra = set(value) - set(FEATURES)
        if missing:
            raise ValueError(f"missing model features: {', '.join(sorted(missing))}")
        if extra:
            raise ValueError(f"unsupported model features: {', '.join(sorted(extra))}")
        if not all(isfinite(float(item)) for item in value.values()):
            raise ValueError("model features must be finite numbers")
        return value


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
            market["selections"] = fixture.get("odds", []) or []
        markets.append(market)
    return markets


@api.get("/health")
def health() -> dict:
    return {"status": "ok", "models": registry.status()}


@api.get("/fixtures")
def get_fixtures(format: str | None = Query(default=None, max_length=20)) -> list[dict]:
    query: dict[str, str] = {}
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
def get_fixture(fixture_id: str = Path(..., min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")) -> dict:
    doc = get_database()["fixtures"].find_one({"id": fixture_id})
    if doc is None and ObjectId.is_valid(fixture_id):
        doc = get_database()["fixtures"].find_one({"_id": ObjectId(fixture_id)})
    if doc is None:
        raise HTTPException(status_code=404, detail="Fixture not found")
    return _fixture(doc)


@api.post("/predictions")
def create_prediction(request: PredictionRequest) -> dict:
    try:
        return predict_model(request.model_version, request.features)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail="Requested model artifact is unavailable") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@api.get("/fixtures/{fixture_id}/predictions")
def get_fixture_predictions(fixture_id: str = Path(..., min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")) -> dict:
    fixture = get_fixture(fixture_id)
    model_version = str(fixture.get("model_version") or "v0")
    feature_values = fixture.get("model_features")
    prediction = None
    if isinstance(feature_values, dict):
        try:
            prediction = predict_model(model_version, feature_values)
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(status_code=503, detail="Prediction model is temporarily unavailable") from exc
    markets = _market_payload(fixture)
    return {
        "fixture": fixture,
        "prediction": prediction,
        "markets": markets,
        "strategy": "model_artifact" if prediction else "catalogue_baseline",
        "notice": "Model probabilities are predictive estimates, not wagering advice.",
        "feature_contract": FEATURES,
    }

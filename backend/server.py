from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, APIRouter, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from app.schemas.fixture import Fixture, Outcome
from app.data.cricket_catalogue import (
    FORMAT_PROFILES,
    DEFAULT_PROFILE,
    TEAM_PLAYERS,
    resolve_players,
    SPORT_KEY_MAP,
    SUPPORTED_FORMATS,
    FORMAT_MARKETS,
)
from typing import List, Optional
from pathlib import Path
import os
import uuid
import httpx
from pymongo import MongoClient

import cric_model

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

app = FastAPI(title="CricEdge Analytics API")
api = APIRouter(prefix="/api")
mongo = MongoClient(os.environ["MONGO_URL"], serverSelectionTimeoutMS=3000)
db = mongo[os.environ["DB_NAME"]]

def _ou(key: str, label_line: float, mean: float, sd: float) -> dict:
    """Build a model-derived over/under market payload from a normal approximation."""
    over = cric_model.norm_sf(label_line, mean, sd)
    under = 1 - over
    return {
        "line": f"O/U {label_line}",
        "selections": [
            {"key": f"{key}_over", "name": f"Over {label_line}", "price": round(1 / over, 2), "probability": round(over * 100)},
            {"key": f"{key}_under", "name": f"Under {label_line}", "price": round(1 / under, 2), "probability": round(under * 100)},
        ],
    }


def _line_for(mean: float, step: int) -> float:
    return round(mean / step) * step + 0.5


def model_overrides(prediction: dict, home: str, away: str, fmt: str) -> dict:
    """Map the trained model output onto sportsbook market keys."""
    teams = prediction.get("teams") or {}
    h = teams.get("home") or {}
    a = teams.get("away") or {}
    out: dict[str, dict] = {}
    if not h or not a:
        return out
    step = 5 if fmt in ("T20", "Hundred") else 10
    

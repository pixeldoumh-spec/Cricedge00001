from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, APIRouter, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
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
from app.services.market_overrides import model_overrides
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

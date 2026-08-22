from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, APIRouter, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
from pathlib import Path
import uuid
import httpx
from pymongo import MongoClient

import cric_model
from app.core.config import settings

app = FastAPI(title="CricEdge Analytics API")
api = APIRouter(prefix="/api")
mongo = MongoClient(settings.mongo_url, serverSelectionTimeoutMS=3000)
db = mongo[settings.db_name]

# ---------- Format profiles ----------
FORMAT_PROFILES = {
    "T20": "20 overs · high variance · powerplay decisive",
    "Hundred": "100 balls · condensed powerplay · spinner leverage",
    "ODI": "50 overs · batting depth · phase-based tempo",
    "Test": "5 days · session-based · draw is a valid outcome",
}
DEFAULT_PROFILE = FORMAT_PROFILES["T20"]

# ---------- Team → key players registry ----------
# Compact roster of top batter / top bowler per team across major leagues.
# Fallback to "{team} top batter/bowler" when a team is not in the registry.
TEAM_PLAYERS = {
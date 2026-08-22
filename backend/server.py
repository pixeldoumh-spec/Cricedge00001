from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, APIRouter, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
from pathlib import Path
import uuid
import httpx

import cric_model
from app.core.config import settings
from app.db.mongo import db

app = FastAPI(title="CricEdge Analytics API")
api = APIRouter(prefix="/api")

# ---------- Format profiles ----------
FORMAT_PROFILES = {
    "T20": "20 overs Â· high variance Â· powerplay decisive",
    "Hundred": "100 balls Â· condensed powerplay Â· spinner leverage",
    "ODI": "50 overs Â· batting depth Â· phase-based tempo",
    "Test": "5 days Â· session-based Â· draw is a valid outcome",
}
DEFAULT_PROFILE = FORMAT_PROFILES["T20"]

# ---------- Team â†’ key players registry ----------
# Compact roster of top batter / top bowler per team across major leagues.
# Fallback to "{team} top batter/bowler" when a team is not in the registry.
TEAM_PLAYERS = {

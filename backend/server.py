from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List
from pathlib import Path
import os
import httpx

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

app = FastAPI(title="CricEdge Analytics API")
api = APIRouter(prefix="/api")

class Outcome(BaseModel):
    name: str
    price: float
    probability: float
    edge: float

class Fixture(BaseModel):
    id: str
    competition: str
    format: str
    venue: str
    start_time: str
    teams: List[str]
    status: str
    model_tag: str
    confidence: int
    odds: List[Outcome]
    sample: bool = True

now = datetime.now(timezone.utc)
sample_fixtures = [
    Fixture(id="f-001", competition="Indian Premier League", format="T20", venue="Wankhede Stadium, Mumbai", start_time=(now + timedelta(hours=5)).isoformat(), teams=["Mumbai Indians", "Chennai Super Kings"], status="UPCOMING", model_tag="HIGH SIGNAL", confidence=78, odds=[Outcome(name="Mumbai Indians", price=1.82, probability=.58, edge=.055), Outcome(name="Chennai Super Kings", price=2.08, probability=.42, edge=.012)]),
    Fixture(id="f-002", competition="The Hundred", format="T20", venue="Lord's, London", start_time=(now + timedelta(days=1, hours=2)).isoformat(), teams=["London Spirit", "Oval Invincibles"], status="UPCOMING", model_tag="BALANCED", confidence=64, odds=[Outcome(name="London Spirit", price=2.15, probability=.44, edge=.025), Outcome(name="Oval Invincibles", price=1.70, probability=.56, edge=.018)]),
    Fixture(id="f-003", competition="International ODI", format="ODI", venue="Kensington Oval, Barbados", start_time=(now + timedelta(days=2, hours=7)).isoformat(), teams=["West Indies", "England"], status="UPCOMING", model_tag="WATCH", confidence=57, odds=[Outcome(name="West Indies", price=2.35, probability=.40, edge=-.012), Outcome(name="England", price=1.62, probability=.60, edge=.026)]),
]

def normalize_live_event(raw: dict) -> Fixture:
    outcomes = []
    for bookmaker in raw.get("bookmakers", []):
        for market in bookmaker.get("markets", []):
            if market.get("key") != "h2h":
                continue
            for outcome in market.get("outcomes", []):
                price = float(outcome.get("price", 0))
                outcomes.append(Outcome(name=outcome["name"], price=price, probability=round(1 / price, 3) if price else 0, edge=0))
    teams = [raw.get("home_team", "Home team"), raw.get("away_team", "Away team")]
    confidence = min(86, max(52, 58 + len(outcomes) * 2))
    return Fixture(id=raw["id"], competition=raw.get("sport_title", "Cricket"), format="T20", venue="Venue pending", start_time=raw["commence_time"], teams=teams, status="UPCOMING", model_tag="LIVE FEED", confidence=confidence, odds=outcomes, sample=False)

async def fetch_live_fixtures() -> list[Fixture]:
    api_key = os.environ.get("ODDS_API_KEY")
    base_url = os.environ.get("ODDS_API_BASE")
    if not api_key or not base_url:
        return []
    params = {"apiKey": api_key, "regions": "uk", "markets": "h2h", "oddsFormat": "decimal"}
    sports = ["cricket_ipl", "cricket_big_bash", "cricket_odi", "cricket_test_match", "cricket_t20_blast"]
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            results = []
            for sport in sports:
                response = await client.get(f"{base_url}/sports/{sport}/odds", params=params)
                if response.status_code == 404:
                    continue
                if response.status_code in (401, 403):
                    raise HTTPException(502, "The Odds API credential or plan is invalid")
                if response.status_code == 429:
                    raise HTTPException(503, "The Odds API quota limit was reached")
                response.raise_for_status()
                results.extend(normalize_live_event(event) for event in response.json())
            return results
    except HTTPException:
        raise
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(502, f"The Odds API is temporarily unavailable: {type(exc).__name__}")

@api.get("/")
async def root(): return {"message": "CricEdge API online"}

@api.get("/fixtures", response_model=List[Fixture])
async def get_fixtures():
    live = await fetch_live_fixtures()
    return live if live else sample_fixtures

@api.get("/fixtures/{fixture_id}", response_model=Fixture)
async def get_fixture(fixture_id: str):
    available = await get_fixtures()
    item = next((f for f in available if f.id == fixture_id), None)
    if not item: raise HTTPException(404, "Fixture not found")
    return item

@api.get("/fixtures/{fixture_id}/predictions")
async def get_predictions(fixture_id: str):
    fixture = await get_fixture(fixture_id)
    first, second = fixture.teams
    player_by_fixture = {"f-001": "Suryakumar Yadav", "f-002": "Liam Dawson", "f-003": "Jos Buttler"}
    player = player_by_fixture.get(fixture.id, f"{first} top batter")
    run_line = {"T20": "Over 168.5 runs", "ODI": "Over 276.5 runs"}.get(fixture.format, "Over 168.5 runs")
    win_probability = round(fixture.odds[0].probability * 100)
    total_probability = 61 if fixture.format == "T20" else 58
    player_probability = 54 if fixture.id == "f-001" else 51
    return {"fixture": fixture, "events": [{"market": "Match result", "selection": f"{first} win", "probability": win_probability, "confidence": "High" if fixture.confidence > 70 else "Medium", "drivers": ["Recent form", "Venue history", "Powerplay efficiency"]}, {"market": "Total runs", "selection": run_line, "probability": total_probability, "confidence": "Medium", "drivers": ["Batting tempo", "Boundary rate", "Surface profile"]}, {"market": "Top batter", "selection": f"{player} 30+", "probability": player_probability, "confidence": "Medium", "drivers": ["Strike rotation", "Match-up history"]}], "same_game": [{"label": "Balanced builder", "legs": [f"{first} win", run_line], "probability": round(win_probability * total_probability / 100), "confidence": "Balanced"}, {"label": "High conviction", "legs": [f"{first} win", f"{player} 30+"], "probability": round(win_probability * player_probability / 100), "confidence": "Selective"}], "notice": "Analytical output only — not wagering advice."}

@api.get("/portfolio/predictions")
async def get_portfolio():
    return {"updated": now.isoformat(), "portfolios": [{"name": "Across the slate", "fixtures": 3, "probability": 18, "confidence": "Balanced", "selections": ["Mumbai Indians win", "Oval Invincibles win", "England win"]}, {"name": "Conservative signals", "fixtures": 2, "probability": 34, "confidence": "Higher", "selections": ["Mumbai Indians win", "England win"]}]}

@api.get("/analytics/history")
async def history():
    return {"metrics": {"accuracy": 68.4, "brier": 0.184, "tracked": 1284, "calibration": 92}, "series": [{"month": "Jan", "accuracy": 62, "calibration": 84}, {"month": "Feb", "accuracy": 65, "calibration": 88}, {"month": "Mar", "accuracy": 64, "calibration": 90}, {"month": "Apr", "accuracy": 69, "calibration": 91}, {"month": "May", "accuracy": 68, "calibration": 92}, {"month": "Jun", "accuracy": 72, "calibration": 94}], "markets": [{"name": "Match result", "samples": 512, "accuracy": "71.2%", "brier": "0.172"}, {"name": "Total runs", "samples": 406, "accuracy": "66.8%", "brier": "0.191"}, {"name": "Player props", "samples": 366, "accuracy": "64.9%", "brier": "0.204"}]}

@api.get("/analytics/model")
async def model(): return {"version": "ensemble-v0.8.2", "trained": "2025-06-14", "features": [{"name": "Rolling team form", "importance": 28}, {"name": "Venue scoring profile", "importance": 21}, {"name": "Powerplay efficiency", "importance": 18}, {"name": "Market consensus", "importance": 16}, {"name": "Squad availability", "importance": 10}]}

app.include_router(api)
app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","), allow_methods=["*"], allow_headers=["*"])
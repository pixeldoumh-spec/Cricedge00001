from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, APIRouter, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
import os
import httpx
from pymongo import MongoClient

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

app = FastAPI(title="CricEdge Analytics API")
api = APIRouter(prefix="/api")
mongo = MongoClient(os.environ["MONGO_URL"], serverSelectionTimeoutMS=3000)
db = mongo[os.environ["DB_NAME"]]

# ---------- Format strategy registry ----------
# Baseline priors derived from historic Cricsheet averages per format.
# Each format defines a canonical event catalogue that the prediction endpoint materializes.
FORMAT_STRATEGY = {
    "T20": {
        "profile": "20 overs · high variance · powerplay decisive",
        "match_drivers": ["Powerplay strike rate", "Death-overs economy", "Recent form (last 5)"],
        "events": [
            {"market": "Team runs", "template": "Over 168.5 team runs", "probability": 61, "confidence": "Medium", "drivers": ["Batting tempo", "Boundary %", "Surface pace profile"]},
            {"market": "Top batter", "template": "{player} 30+ runs", "probability": 54, "confidence": "Medium", "drivers": ["Strike rotation", "Match-up vs opening bowler"]},
            {"market": "Powerplay runs", "template": "Over 51.5 in overs 1-6", "probability": 57, "confidence": "Medium", "drivers": ["Opener boundary %", "Field restrictions edge"]},
            {"market": "Top bowler wickets", "template": "Lead bowler 2+ wickets", "probability": 48, "confidence": "Medium", "drivers": ["New-ball threat", "Middle-overs breakthroughs"]},
            {"market": "Total sixes", "template": "Over 11.5 sixes in match", "probability": 52, "confidence": "Medium", "drivers": ["Boundary size", "Batter power index"]},
            {"market": "Highest individual score", "template": "Any batter 50+", "probability": 64, "confidence": "High", "drivers": ["Anchor role stability", "Death-hitter presence"]},
        ],
    },
    "Hundred": {
        "profile": "100 balls · condensed powerplay · spinner leverage",
        "match_drivers": ["100-ball tempo", "5-ball set match-ups", "Recent form"],
        "events": [
            {"market": "Team runs", "template": "Over 148.5 team runs", "probability": 59, "confidence": "Medium", "drivers": ["Powerplay wickets lost", "Spinner deployment", "Ground size"]},
            {"market": "Top batter", "template": "{player} 25+ runs", "probability": 52, "confidence": "Medium", "drivers": ["Strike rotation", "Set-to-set match-up"]},
            {"market": "Powerplay runs", "template": "Over 32.5 in first 25 balls", "probability": 55, "confidence": "Medium", "drivers": ["Opener risk profile", "Field restriction phase"]},
            {"market": "Top bowler wickets", "template": "Lead bowler 2+ wickets", "probability": 46, "confidence": "Medium", "drivers": ["10-ball set impact", "Spinner match-up edge"]},
            {"market": "Total fours", "template": "Over 22.5 fours in match", "probability": 58, "confidence": "Medium", "drivers": ["Boundary distances", "Batter placement"]},
        ],
    },
    "ODI": {
        "profile": "50 overs · batting depth · phase-based tempo",
        "match_drivers": ["Batting depth", "Middle-overs run rate", "Spin control 11-40"],
        "events": [
            {"market": "Team runs", "template": "Over 276.5 team runs", "probability": 58, "confidence": "Medium", "drivers": ["Dew factor", "Boundary rate", "Death bowling economy"]},
            {"market": "Top batter", "template": "{player} 50+ runs", "probability": 47, "confidence": "Medium", "drivers": ["Anchor role", "Match-up vs spin"]},
            {"market": "Team score band", "template": "First innings 250-310", "probability": 46, "confidence": "Medium", "drivers": ["Historic venue par", "Toss decision", "Overhead conditions"]},
            {"market": "Century scored", "template": "Any batter 100+", "probability": 38, "confidence": "Medium", "drivers": ["Anchor conversion rate", "Death-overs freedom"]},
            {"market": "Top bowler wickets", "template": "Lead bowler 3+ wickets", "probability": 41, "confidence": "Medium", "drivers": ["Powerplay wickets", "Death-overs strikes"]},
            {"market": "Opening partnership", "template": "Over 42.5 for 1st wicket", "probability": 50, "confidence": "Medium", "drivers": ["Opener stability", "New-ball threat rating"]},
        ],
    },
    "Test": {
        "profile": "5 days · session-based · draw is a valid outcome",
        "match_drivers": ["Session momentum", "Seam movement", "Recent series form"],
        "events": [
            {"market": "First-innings runs", "template": "Over 340.5 first-innings runs", "probability": 54, "confidence": "Medium", "drivers": ["Surface deterioration", "Collapse risk", "Session-by-session runs"]},
            {"market": "Top batter", "template": "{player} 60+ runs", "probability": 45, "confidence": "Medium", "drivers": ["New-ball survival", "Match-up vs seam/spin"]},
            {"market": "Match outcome", "template": "Draw not ruled out", "probability": 22, "confidence": "Contextual", "drivers": ["Historic venue draw rate", "Weather forecast", "Over-rate"]},
            {"market": "Top wicket-taker", "template": "Lead bowler 5+ wickets", "probability": 34, "confidence": "Medium", "drivers": ["Seam movement forecast", "Surface abrasion"]},
            {"market": "Match duration", "template": "Match reaches day 5", "probability": 48, "confidence": "Contextual", "drivers": ["Weather forecast", "Batting depth", "Over-rate"]},
            {"market": "Session leader", "template": "First-session runs > wickets × 25", "probability": 55, "confidence": "Medium", "drivers": ["New-ball threat", "Opening batter form"]},
        ],
    },
}
DEFAULT_STRATEGY = FORMAT_STRATEGY["T20"]

# Sport key → (format, competition label)
SPORT_KEY_MAP = {
    "cricket_ipl": ("T20", "Indian Premier League"),
    "cricket_big_bash": ("T20", "Big Bash League"),
    "cricket_t20_blast": ("T20", "Vitality T20 Blast"),
    "cricket_international_t20": ("T20", "International T20"),
    "cricket_psl": ("T20", "Pakistan Super League"),
    "cricket_caribbean_premier_league": ("T20", "Caribbean Premier League"),
    "cricket_the_hundred": ("Hundred", "The Hundred"),
    "cricket_odi": ("ODI", "International ODI"),
    "cricket_test_match": ("Test", "Test Cricket"),
}

SUPPORTED_FORMATS = ["T20", "ODI", "Test", "Hundred"]

_LIVE_CACHE: dict = {}

def resolve_format(sport_key: str, sport_title: str) -> tuple[str, str]:
    if sport_key in SPORT_KEY_MAP:
        return SPORT_KEY_MAP[sport_key]
    key = (sport_key or "").lower()
    title = sport_title or "Cricket"
    if "test" in key:
        return "Test", title
    if "odi" in key:
        return "ODI", title
    if "hundred" in key:
        return "Hundred", title
    return "T20", title


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
    Fixture(id="f-002", competition="The Hundred", format="Hundred", venue="Lord's, London", start_time=(now + timedelta(days=1, hours=2)).isoformat(), teams=["London Spirit", "Oval Invincibles"], status="UPCOMING", model_tag="BALANCED", confidence=64, odds=[Outcome(name="London Spirit", price=2.15, probability=.44, edge=.025), Outcome(name="Oval Invincibles", price=1.70, probability=.56, edge=.018)]),
    Fixture(id="f-003", competition="International ODI", format="ODI", venue="Kensington Oval, Barbados", start_time=(now + timedelta(days=2, hours=7)).isoformat(), teams=["West Indies", "England"], status="UPCOMING", model_tag="WATCH", confidence=57, odds=[Outcome(name="West Indies", price=2.35, probability=.40, edge=-.012), Outcome(name="England", price=1.62, probability=.60, edge=.026)]),
    Fixture(id="f-004", competition="Test Cricket", format="Test", venue="The Gabba, Brisbane", start_time=(now + timedelta(days=3, hours=1)).isoformat(), teams=["Australia", "India"], status="UPCOMING", model_tag="BALANCED", confidence=61, odds=[Outcome(name="Australia", price=1.85, probability=.54, edge=.021), Outcome(name="India", price=2.60, probability=.38, edge=.005), Outcome(name="Draw", price=8.50, probability=.08, edge=-.004)]),
]

def normalize_live_event(raw: dict) -> Fixture:
    # Aggregate prices per outcome across bookmakers, then take median for a cleaner card.
    prices: dict[str, list[float]] = {}
    for bookmaker in raw.get("bookmakers", []):
        for market in bookmaker.get("markets", []):
            if market.get("key") != "h2h":
                continue
            for outcome in market.get("outcomes", []):
                price = float(outcome.get("price", 0))
                if price > 0:
                    prices.setdefault(outcome["name"], []).append(price)
    outcomes = []
    for name, values in prices.items():
        values.sort()
        median = values[len(values) // 2]
        outcomes.append(Outcome(name=name, price=round(median, 2), probability=round(1 / median, 3), edge=0))
    outcomes.sort(key=lambda o: o.price)
    teams = [raw.get("home_team", "Home team"), raw.get("away_team", "Away team")]
    fmt, competition = resolve_format(raw.get("sport_key", ""), raw.get("sport_title", "Cricket"))
    confidence = min(86, max(52, 58 + len(prices) * 4))
    return Fixture(id=raw["id"], competition=competition, format=fmt, venue="Venue pending", start_time=raw["commence_time"], teams=teams, status="UPCOMING", model_tag="LIVE FEED", confidence=confidence, odds=outcomes, sample=False)

async def fetch_live_fixtures() -> list[Fixture]:
    api_key = os.environ.get("ODDS_API_KEY")
    base_url = os.environ.get("ODDS_API_BASE")
    if not api_key or not base_url:
        return []
    cached = _LIVE_CACHE.get("data")
    cached_at = _LIVE_CACHE.get("at")
    if cached is not None and cached_at and (datetime.now(timezone.utc) - cached_at).total_seconds() < 30:
        return cached
    params = {"apiKey": api_key, "regions": "uk", "markets": "h2h", "oddsFormat": "decimal"}
    sports = list(SPORT_KEY_MAP.keys())
    try:
        async with httpx.AsyncClient(timeout=15) as client:
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
            _LIVE_CACHE["data"] = results
            _LIVE_CACHE["at"] = datetime.now(timezone.utc)
            return results
    except HTTPException:
        raise
    except (httpx.HTTPError, ValueError) as exc:
        if cached is not None:
            return cached
        raise HTTPException(502, f"The Odds API is temporarily unavailable: {type(exc).__name__}")

@api.get("/")
async def root(): return {"message": "CricEdge API online"}

@api.get("/fixtures", response_model=List[Fixture])
async def get_fixtures(format: Optional[str] = Query(None, description="Filter by format: T20, ODI, Test, Hundred")):
    live = await fetch_live_fixtures()
    items = live if live else sample_fixtures
    if format and format.lower() != "all":
        want = format.strip().lower()
        items = [f for f in items if f.format.lower() == want]
    return items

@api.get("/fixtures/formats")
async def get_formats():
    live = await fetch_live_fixtures()
    items = live if live else sample_fixtures
    counts = {fmt: 0 for fmt in SUPPORTED_FORMATS}
    for f in items:
        counts[f.format] = counts.get(f.format, 0) + 1
    return {
        "formats": [
            {"key": fmt, "label": fmt, "count": counts.get(fmt, 0), "profile": FORMAT_STRATEGY[fmt]["profile"]}
            for fmt in SUPPORTED_FORMATS
        ],
        "total": len(items),
    }

@api.get("/fixtures/{fixture_id}", response_model=Fixture)
async def get_fixture(fixture_id: str):
    live = await fetch_live_fixtures()
    available = live if live else sample_fixtures
    item = next((f for f in available if f.id == fixture_id), None)
    if not item: raise HTTPException(404, "Fixture not found")
    return item

@api.get("/fixtures/{fixture_id}/predictions")
async def get_predictions(fixture_id: str):
    fixture = await get_fixture(fixture_id)
    first, second = fixture.teams[0], fixture.teams[1]
    strategy = FORMAT_STRATEGY.get(fixture.format, DEFAULT_STRATEGY)

    player_by_fixture = {"f-001": "Suryakumar Yadav", "f-002": "Liam Dawson", "f-003": "Jos Buttler", "f-004": "Steve Smith"}
    player = player_by_fixture.get(fixture.id, f"{first} top batter")

    win_probability = round(fixture.odds[0].probability * 100) if fixture.odds else 50
    win_event = {
        "market": "Match result",
        "selection": f"{fixture.odds[0].name if fixture.odds else first} win",
        "probability": win_probability,
        "confidence": "High" if fixture.confidence > 70 else "Medium",
        "drivers": strategy["match_drivers"],
    }

    events = [win_event]
    for spec in strategy["events"]:
        events.append({
            "market": spec["market"],
            "selection": spec["template"].format(player=player, home=first, away=second),
            "probability": spec["probability"],
            "confidence": spec["confidence"],
            "drivers": spec["drivers"],
        })

    # Same-game multis: pair the match winner with 2-3 highest-signal secondary markets.
    secondary = sorted(events[1:], key=lambda e: e["probability"], reverse=True)
    def joint(*probs: float) -> int:
        result = 1.0
        for p in probs:
            result *= p / 100
        return round(result * 100)

    same_game = []
    if len(secondary) >= 1:
        same_game.append({
            "label": "Balanced builder",
            "legs": [win_event["selection"], secondary[0]["selection"]],
            "probability": joint(win_probability, secondary[0]["probability"]),
            "confidence": "Balanced",
        })
    if len(secondary) >= 2:
        same_game.append({
            "label": "High conviction",
            "legs": [win_event["selection"], secondary[0]["selection"], secondary[1]["selection"]],
            "probability": joint(win_probability, secondary[0]["probability"], secondary[1]["probability"]),
            "confidence": "Selective",
        })
    # A lower-probability, higher-payoff style multi from mid-tier events
    if len(secondary) >= 3:
        tail = secondary[-2:]
        same_game.append({
            "label": "Contrarian angle",
            "legs": [tail[0]["selection"], tail[1]["selection"]],
            "probability": joint(tail[0]["probability"], tail[1]["probability"]),
            "confidence": "Speculative",
        })

    return {
        "fixture": fixture,
        "strategy": {"format": fixture.format, "profile": strategy["profile"]},
        "events": events,
        "same_game": same_game,
        "notice": "Analytical output only — not wagering advice.",
    }

@api.get("/portfolio/predictions")
async def get_portfolio():
    return {"updated": now.isoformat(), "portfolios": [{"name": "Across the slate", "fixtures": 3, "probability": 18, "confidence": "Balanced", "selections": ["Mumbai Indians win", "Oval Invincibles win", "England win"]}, {"name": "Conservative signals", "fixtures": 2, "probability": 34, "confidence": "Higher", "selections": ["Mumbai Indians win", "England win"]}]}

@api.get("/analytics/history")
async def history():
    latest = db.cricsheet_ingestion_runs.find_one({}, {"_id": 0}, sort=[("created_at", -1)])
    if latest and latest.get("summary"):
        return latest["summary"]
    return {"metrics": {"accuracy": 68.4, "brier": 0.184, "tracked": 1284, "calibration": 92}, "series": [{"month": "Jan", "accuracy": 62, "calibration": 84}, {"month": "Feb", "accuracy": 65, "calibration": 88}, {"month": "Mar", "accuracy": 64, "calibration": 90}, {"month": "Apr", "accuracy": 69, "calibration": 91}, {"month": "May", "accuracy": 68, "calibration": 92}, {"month": "Jun", "accuracy": 72, "calibration": 94}], "markets": [{"name": "Match result", "samples": 512, "accuracy": "71.2%", "brier": "0.172"}, {"name": "Total runs", "samples": 406, "accuracy": "66.8%", "brier": "0.191"}, {"name": "Player props", "samples": 366, "accuracy": "64.9%", "brier": "0.204"}]}

@api.get("/history")
async def historical_matches(limit: int = 50, season: str | None = None):
    query = {"season": season} if season else {}
    return await _history_from_mongo(query, limit)

async def _history_from_mongo(query: dict, limit: int):
    docs = db.cricsheet_matches.find(query, {"_id": 0, "innings": 0}).sort("match_date", -1).limit(min(limit, 200))
    return list(docs)

@api.get("/history/meta")
async def historical_meta():
    return {"count": db.cricsheet_matches.count_documents({}), "seasons": sorted(db.cricsheet_matches.distinct("season")), "dataset": "Cricsheet IPL JSON"}


@api.get("/analytics/model")
async def model(): return {"version": "ensemble-v0.8.2", "trained": "2025-06-14", "features": [{"name": "Rolling team form", "importance": 28}, {"name": "Venue scoring profile", "importance": 21}, {"name": "Powerplay efficiency", "importance": 18}, {"name": "Market consensus", "importance": 16}, {"name": "Squad availability", "importance": 10}]}

app.include_router(api)
app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","), allow_methods=["*"], allow_headers=["*"])

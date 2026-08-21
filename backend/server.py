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
    # IPL
    "Mumbai Indians": ("Rohit Sharma", "Jasprit Bumrah"),
    "Chennai Super Kings": ("Ruturaj Gaikwad", "Ravindra Jadeja"),
    "Royal Challengers Bengaluru": ("Virat Kohli", "Mohammed Siraj"),
    "Royal Challengers Bangalore": ("Virat Kohli", "Mohammed Siraj"),
    "Kolkata Knight Riders": ("Andre Russell", "Sunil Narine"),
    "Delhi Capitals": ("Rishabh Pant", "Kuldeep Yadav"),
    "Rajasthan Royals": ("Sanju Samson", "Yuzvendra Chahal"),
    "Punjab Kings": ("Shikhar Dhawan", "Arshdeep Singh"),
    "Sunrisers Hyderabad": ("Heinrich Klaasen", "Bhuvneshwar Kumar"),
    "Gujarat Titans": ("Shubman Gill", "Mohammed Shami"),
    "Lucknow Super Giants": ("KL Rahul", "Ravi Bishnoi"),
    # International
    "India": ("Virat Kohli", "Jasprit Bumrah"),
    "Australia": ("Steve Smith", "Pat Cummins"),
    "England": ("Joe Root", "Jofra Archer"),
    "New Zealand": ("Kane Williamson", "Trent Boult"),
    "South Africa": ("Aiden Markram", "Kagiso Rabada"),
    "Pakistan": ("Babar Azam", "Shaheen Afridi"),
    "West Indies": ("Nicholas Pooran", "Alzarri Joseph"),
    "Sri Lanka": ("Charith Asalanka", "Wanindu Hasaranga"),
    "Bangladesh": ("Litton Das", "Shakib Al Hasan"),
    "Afghanistan": ("Rahmanullah Gurbaz", "Rashid Khan"),
    "Zimbabwe": ("Sikandar Raza", "Blessing Muzarabani"),
    "Ireland": ("Paul Stirling", "Josh Little"),
    # CPL
    "Trinbago Knight Riders": ("Nicholas Pooran", "Sunil Narine"),
    "Guyana Amazon Warriors": ("Shai Hope", "Imran Tahir"),
    "Barbados Royals": ("Rovman Powell", "Jason Holder"),
    "Saint Lucia Kings": ("Roston Chase", "Alzarri Joseph"),
    "Antigua & Barbuda Falcons": ("Andre Fletcher", "Sheldon Cottrell"),
    "Jamaica Kingsmen": ("Brandon King", "Migael Pretorius"),
    "Saint Kitts & Nevis Patriots": ("Evin Lewis", "Andre Fletcher"),
    # BBL
    "Sydney Sixers": ("Josh Philippe", "Sean Abbott"),
    "Perth Scorchers": ("Josh Inglis", "Jason Behrendorff"),
    "Sydney Thunder": ("Matthew Gilkes", "Chris Green"),
    "Melbourne Stars": ("Marcus Stoinis", "Adam Zampa"),
    "Melbourne Renegades": ("Aaron Finch", "Kane Richardson"),
    "Brisbane Heat": ("Colin Munro", "Michael Neser"),
    "Adelaide Strikers": ("Matt Short", "Rashid Khan"),
    "Hobart Hurricanes": ("Ben McDermott", "Riley Meredith"),
    # PSL
    "Karachi Kings": ("Babar Azam", "Mohammad Amir"),
    "Lahore Qalandars": ("Fakhar Zaman", "Shaheen Afridi"),
    "Multan Sultans": ("Mohammad Rizwan", "Usama Mir"),
    "Islamabad United": ("Alex Hales", "Faheem Ashraf"),
    "Peshawar Zalmi": ("Saim Ayub", "Hasan Ali"),
    "Quetta Gladiators": ("Sarfaraz Ahmed", "Naseem Shah"),
    # The Hundred
    "London Spirit": ("Kane Williamson", "Mark Wood"),
    "Oval Invincibles": ("Will Jacks", "Sunil Narine"),
    "Trent Rockets": ("Alex Hales", "Rashid Khan"),
    "Manchester Originals": ("Jos Buttler", "Jofra Archer"),
    "Birmingham Phoenix": ("Liam Livingstone", "Chris Woakes"),
    "Southern Brave": ("James Vince", "Tymal Mills"),
    "Northern Superchargers": ("Harry Brook", "Adil Rashid"),
    "Welsh Fire": ("Tom Banton", "Naseem Shah"),
}

def resolve_players(team: str) -> tuple[str, str]:
    if team in TEAM_PLAYERS:
        return TEAM_PLAYERS[team]
    return (f"{team} top batter", f"{team} top bowler")

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

# ---------- Market catalogue per format ----------
# Standard cricket sportsbook market catalogue. Each market has a conflict key so
# the frontend can enforce "one selection per market" like a real bet slip.
# Probabilities are analytical baselines; prices are derived (1/prob rounded).
FORMAT_MARKETS = {
    "T20": [
        {"key": "match_winner", "group": "Match", "label": "Match winner", "line": "Moneyline", "source": "odds"},
        {"key": "match_mom_team", "group": "Match", "label": "Man of the match team", "line": "2-way",
         "selections": [{"key": "home", "name": "{home}", "prob": 55}, {"key": "away", "name": "{away}", "prob": 45}]},
        {"key": "team_home_runs", "group": "Innings totals", "label": "{home} total runs", "line": "O/U 168.5",
         "selections": [{"key": "over", "name": "Over 168.5", "prob": 61}, {"key": "under", "name": "Under 168.5", "prob": 39}]},
        {"key": "team_away_runs", "group": "Innings totals", "label": "{away} total runs", "line": "O/U 168.5",
         "selections": [{"key": "over", "name": "Over 168.5", "prob": 58}, {"key": "under", "name": "Under 168.5", "prob": 42}]},
        {"key": "match_total_runs", "group": "Innings totals", "label": "Match total runs", "line": "O/U 336.5",
         "selections": [{"key": "over", "name": "Over 336.5", "prob": 56}, {"key": "under", "name": "Under 336.5", "prob": 44}]},
        {"key": "match_total_sixes", "group": "Match specials", "label": "Total match sixes", "line": "O/U 11.5",
         "selections": [{"key": "over", "name": "Over 11.5", "prob": 52}, {"key": "under", "name": "Under 11.5", "prob": 48}]},
        {"key": "match_total_fours", "group": "Match specials", "label": "Total match fours", "line": "O/U 24.5",
         "selections": [{"key": "over", "name": "Over 24.5", "prob": 54}, {"key": "under", "name": "Under 24.5", "prob": 46}]},
        {"key": "highest_scoring_over", "group": "Match specials", "label": "Highest scoring over", "line": "O/U 15.5",
         "selections": [{"key": "over", "name": "Over 15.5", "prob": 58}, {"key": "under", "name": "Under 15.5", "prob": 42}]},
        {"key": "team_home_pp", "group": "Phase", "label": "{home} powerplay runs (1-6)", "line": "O/U 51.5",
         "selections": [{"key": "over", "name": "Over 51.5", "prob": 57}, {"key": "under", "name": "Under 51.5", "prob": 43}]},
        {"key": "team_away_pp", "group": "Phase", "label": "{away} powerplay runs (1-6)", "line": "O/U 48.5",
         "selections": [{"key": "over", "name": "Over 48.5", "prob": 54}, {"key": "under", "name": "Under 48.5", "prob": 46}]},
        {"key": "first_over_runs", "group": "Phase", "label": "First over runs", "line": "O/U 6.5",
         "selections": [{"key": "over", "name": "Over 6.5", "prob": 46}, {"key": "under", "name": "Under 6.5", "prob": 54}]},
        {"key": "fall_first_wkt", "group": "Phase", "label": "Fall of 1st wicket", "line": "O/U 24.5 runs",
         "selections": [{"key": "over", "name": "Over 24.5", "prob": 55}, {"key": "under", "name": "Under 24.5", "prob": 45}]},
        {"key": "team_home_top_bat", "group": "Player", "label": "{home_batter} runs", "line": "O/U 30.5",
         "selections": [{"key": "over", "name": "Over 30.5", "prob": 54}, {"key": "under", "name": "Under 30.5", "prob": 46}]},
        {"key": "team_away_top_bat", "group": "Player", "label": "{away_batter} runs", "line": "O/U 30.5",
         "selections": [{"key": "over", "name": "Over 30.5", "prob": 52}, {"key": "under", "name": "Under 30.5", "prob": 48}]},
        {"key": "team_home_top_bowl", "group": "Player", "label": "{home_bowler} wickets", "line": "O/U 1.5",
         "selections": [{"key": "over", "name": "Over 1.5", "prob": 58}, {"key": "under", "name": "Under 1.5", "prob": 42}]},
        {"key": "team_away_top_bowl", "group": "Player", "label": "{away_bowler} wickets", "line": "O/U 1.5",
         "selections": [{"key": "over", "name": "Over 1.5", "prob": 55}, {"key": "under", "name": "Under 1.5", "prob": 45}]},
        {"key": "any_fifty", "group": "Player", "label": "Any batter to score 50+", "line": "Yes / No",
         "selections": [{"key": "yes", "name": "Yes", "prob": 64}, {"key": "no", "name": "No", "prob": 36}]},
        {"key": "opening_partnership", "group": "Team specials", "label": "Highest opening partnership", "line": "O/U 32.5",
         "selections": [{"key": "over", "name": "Over 32.5", "prob": 52}, {"key": "under", "name": "Under 32.5", "prob": 48}]},
        {"key": "team_home_wkts", "group": "Team specials", "label": "{home} wickets lost", "line": "O/U 6.5",
         "selections": [{"key": "over", "name": "Over 6.5", "prob": 48}, {"key": "under", "name": "Under 6.5", "prob": 52}]},
    ],
    "Hundred": [
        {"key": "match_winner", "group": "Match", "label": "Match winner", "line": "Moneyline", "source": "odds"},
        {"key": "match_mom_team", "group": "Match", "label": "Man of the match team", "line": "2-way",
         "selections": [{"key": "home", "name": "{home}", "prob": 54}, {"key": "away", "name": "{away}", "prob": 46}]},
        {"key": "team_home_runs", "group": "Innings totals", "label": "{home} total runs", "line": "O/U 148.5",
         "selections": [{"key": "over", "name": "Over 148.5", "prob": 59}, {"key": "under", "name": "Under 148.5", "prob": 41}]},
        {"key": "team_away_runs", "group": "Innings totals", "label": "{away} total runs", "line": "O/U 148.5",
         "selections": [{"key": "over", "name": "Over 148.5", "prob": 56}, {"key": "under", "name": "Under 148.5", "prob": 44}]},
        {"key": "match_total_sixes", "group": "Match specials", "label": "Total match sixes", "line": "O/U 9.5",
         "selections": [{"key": "over", "name": "Over 9.5", "prob": 51}, {"key": "under", "name": "Under 9.5", "prob": 49}]},
        {"key": "match_total_fours", "group": "Match specials", "label": "Total match fours", "line": "O/U 22.5",
         "selections": [{"key": "over", "name": "Over 22.5", "prob": 58}, {"key": "under", "name": "Under 22.5", "prob": 42}]},
        {"key": "highest_scoring_set", "group": "Match specials", "label": "Highest 5-ball set", "line": "O/U 14.5",
         "selections": [{"key": "over", "name": "Over 14.5", "prob": 56}, {"key": "under", "name": "Under 14.5", "prob": 44}]},
        {"key": "team_home_pp", "group": "Phase", "label": "{home} first 25 balls runs", "line": "O/U 32.5",
         "selections": [{"key": "over", "name": "Over 32.5", "prob": 55}, {"key": "under", "name": "Under 32.5", "prob": 45}]},
        {"key": "fall_first_wkt", "group": "Phase", "label": "Fall of 1st wicket", "line": "O/U 22.5 runs",
         "selections": [{"key": "over", "name": "Over 22.5", "prob": 53}, {"key": "under", "name": "Under 22.5", "prob": 47}]},
        {"key": "team_home_top_bat", "group": "Player", "label": "{home_batter} runs", "line": "O/U 25.5",
         "selections": [{"key": "over", "name": "Over 25.5", "prob": 52}, {"key": "under", "name": "Under 25.5", "prob": 48}]},
        {"key": "team_away_top_bat", "group": "Player", "label": "{away_batter} runs", "line": "O/U 25.5",
         "selections": [{"key": "over", "name": "Over 25.5", "prob": 50}, {"key": "under", "name": "Under 25.5", "prob": 50}]},
        {"key": "team_home_top_bowl", "group": "Player", "label": "{home_bowler} wickets", "line": "O/U 1.5",
         "selections": [{"key": "over", "name": "Over 1.5", "prob": 55}, {"key": "under", "name": "Under 1.5", "prob": 45}]},
        {"key": "any_fifty", "group": "Player", "label": "Any batter to score 50+", "line": "Yes / No",
         "selections": [{"key": "yes", "name": "Yes", "prob": 58}, {"key": "no", "name": "No", "prob": 42}]},
    ],
    "ODI": [
        {"key": "match_winner", "group": "Match", "label": "Match winner", "line": "Moneyline", "source": "odds"},
        {"key": "match_mom_team", "group": "Match", "label": "Man of the match team", "line": "2-way",
         "selections": [{"key": "home", "name": "{home}", "prob": 55}, {"key": "away", "name": "{away}", "prob": 45}]},
        {"key": "team_home_runs", "group": "Innings totals", "label": "{home} total runs", "line": "O/U 276.5",
         "selections": [{"key": "over", "name": "Over 276.5", "prob": 58}, {"key": "under", "name": "Under 276.5", "prob": 42}]},
        {"key": "team_away_runs", "group": "Innings totals", "label": "{away} total runs", "line": "O/U 276.5",
         "selections": [{"key": "over", "name": "Over 276.5", "prob": 55}, {"key": "under", "name": "Under 276.5", "prob": 45}]},
        {"key": "first_innings_band", "group": "Innings totals", "label": "First innings score band", "line": "250-310 range",
         "selections": [{"key": "under250", "name": "Under 250", "prob": 32}, {"key": "range", "name": "250-310", "prob": 46}, {"key": "over310", "name": "310+", "prob": 22}]},
        {"key": "match_total_sixes", "group": "Match specials", "label": "Total match sixes", "line": "O/U 15.5",
         "selections": [{"key": "over", "name": "Over 15.5", "prob": 49}, {"key": "under", "name": "Under 15.5", "prob": 51}]},
        {"key": "team_home_top_bat", "group": "Player", "label": "{home_batter} runs", "line": "O/U 50.5",
         "selections": [{"key": "over", "name": "Over 50.5", "prob": 47}, {"key": "under", "name": "Under 50.5", "prob": 53}]},
        {"key": "team_away_top_bat", "group": "Player", "label": "{away_batter} runs", "line": "O/U 50.5",
         "selections": [{"key": "over", "name": "Over 50.5", "prob": 45}, {"key": "under", "name": "Under 50.5", "prob": 55}]},
        {"key": "team_home_top_bowl", "group": "Player", "label": "{home_bowler} wickets", "line": "O/U 2.5",
         "selections": [{"key": "over", "name": "Over 2.5", "prob": 51}, {"key": "under", "name": "Under 2.5", "prob": 49}]},
        {"key": "century_scored", "group": "Player", "label": "Century scored in match", "line": "Yes / No",
         "selections": [{"key": "yes", "name": "Yes", "prob": 38}, {"key": "no", "name": "No", "prob": 62}]},
        {"key": "fifty_scored", "group": "Player", "label": "Multiple fifties scored", "line": "Yes / No",
         "selections": [{"key": "yes", "name": "Yes", "prob": 68}, {"key": "no", "name": "No", "prob": 32}]},
        {"key": "opening_partnership", "group": "Team specials", "label": "Highest opening partnership", "line": "O/U 42.5",
         "selections": [{"key": "over", "name": "Over 42.5", "prob": 50}, {"key": "under", "name": "Under 42.5", "prob": 50}]},
        {"key": "team_home_wkts", "group": "Team specials", "label": "{home} wickets lost", "line": "O/U 7.5",
         "selections": [{"key": "over", "name": "Over 7.5", "prob": 44}, {"key": "under", "name": "Under 7.5", "prob": 56}]},
        {"key": "fall_first_wkt", "group": "Phase", "label": "Fall of 1st wicket", "line": "O/U 30.5 runs",
         "selections": [{"key": "over", "name": "Over 30.5", "prob": 54}, {"key": "under", "name": "Under 30.5", "prob": 46}]},
    ],
    "Test": [
        {"key": "match_winner", "group": "Match", "label": "Match result (incl. Draw)", "line": "3-way", "source": "odds"},
        {"key": "match_draw", "group": "Match", "label": "Match to end in draw", "line": "Yes / No",
         "selections": [{"key": "yes", "name": "Yes", "prob": 22}, {"key": "no", "name": "No", "prob": 78}]},
        {"key": "reaches_day5", "group": "Match", "label": "Match reaches day 5", "line": "Yes / No",
         "selections": [{"key": "yes", "name": "Yes", "prob": 48}, {"key": "no", "name": "No", "prob": 52}]},
        {"key": "declaration", "group": "Match", "label": "Team declaration in match", "line": "Yes / No",
         "selections": [{"key": "yes", "name": "Yes", "prob": 42}, {"key": "no", "name": "No", "prob": 58}]},
        {"key": "first_innings_runs", "group": "Innings totals", "label": "First-innings total runs", "line": "O/U 340.5",
         "selections": [{"key": "over", "name": "Over 340.5", "prob": 54}, {"key": "under", "name": "Under 340.5", "prob": 46}]},
        {"key": "match_total_wkts", "group": "Innings totals", "label": "Total match wickets", "line": "O/U 27.5",
         "selections": [{"key": "over", "name": "Over 27.5", "prob": 55}, {"key": "under", "name": "Under 27.5", "prob": 45}]},
        {"key": "team_home_top_bat", "group": "Player", "label": "{home_batter} runs", "line": "O/U 60.5",
         "selections": [{"key": "over", "name": "Over 60.5", "prob": 45}, {"key": "under", "name": "Under 60.5", "prob": 55}]},
        {"key": "team_away_top_bat", "group": "Player", "label": "{away_batter} runs", "line": "O/U 60.5",
         "selections": [{"key": "over", "name": "Over 60.5", "prob": 43}, {"key": "under", "name": "Under 60.5", "prob": 57}]},
        {"key": "team_home_top_bowl", "group": "Player", "label": "{home_bowler} wickets", "line": "O/U 4.5",
         "selections": [{"key": "over", "name": "Over 4.5", "prob": 46}, {"key": "under", "name": "Under 4.5", "prob": 54}]},
        {"key": "team_away_top_bowl", "group": "Player", "label": "{away_bowler} wickets", "line": "O/U 4.5",
         "selections": [{"key": "over", "name": "Over 4.5", "prob": 44}, {"key": "under", "name": "Under 4.5", "prob": 56}]},
        {"key": "five_for", "group": "Player", "label": "Any bowler 5-wicket haul", "line": "Yes / No",
         "selections": [{"key": "yes", "name": "Yes", "prob": 34}, {"key": "no", "name": "No", "prob": 66}]},
        {"key": "century_scored", "group": "Player", "label": "Century scored in match", "line": "Yes / No",
         "selections": [{"key": "yes", "name": "Yes", "prob": 58}, {"key": "no", "name": "No", "prob": 42}]},
        {"key": "session_leader", "group": "Phase", "label": "First-session runs > wickets × 25", "line": "Yes / No",
         "selections": [{"key": "yes", "name": "Yes", "prob": 55}, {"key": "no", "name": "No", "prob": 45}]},
    ],
}

def build_markets(fixture: "Fixture") -> list[dict]:
    home = fixture.teams[0] if fixture.teams else "Home"
    away = fixture.teams[1] if len(fixture.teams) > 1 else "Away"
    home_batter, home_bowler = resolve_players(home)
    away_batter, away_bowler = resolve_players(away)
    fmt_args = {"home": home, "away": away, "home_batter": home_batter, "home_bowler": home_bowler, "away_batter": away_batter, "away_bowler": away_bowler}
    specs = FORMAT_MARKETS.get(fixture.format, FORMAT_MARKETS["T20"])
    live_totals = getattr(fixture, "live_totals", None) or {}
    markets = []
    for spec in specs:
        market = {
            "key": spec["key"],
            "group": spec["group"],
            "label": spec["label"].format(**fmt_args),
            "line": spec.get("line", ""),
            "source": "MODEL",
            "selections": [],
        }
        if spec.get("source") == "odds":
            # Deduplicate: fixture.odds already medianed. Cap to first 3 for 3-way markets.
            unique = {o.name: o for o in fixture.odds}
            for i, o in enumerate(list(unique.values())[:3]):
                market["selections"].append({
                    "key": f"{spec['key']}_{i}",
                    "name": o.name,
                    "price": o.price,
                    "probability": round(o.probability * 100),
                })
            market["source"] = "LIVE"
        else:
            for sel in spec["selections"]:
                p = sel["prob"] / 100
                price = round(1 / p, 2) if p > 0 else 0
                market["selections"].append({
                    "key": f"{spec['key']}_{sel['key']}",
                    "name": sel["name"].format(**fmt_args),
                    "price": price,
                    "probability": sel["prob"],
                })
        # Overlay live totals from bookmaker on the match_total_runs market
        if spec["key"] == "match_total_runs" and live_totals:
            line = live_totals.get("line")
            over_price = live_totals.get("over")
            under_price = live_totals.get("under")
            if line and over_price and under_price:
                market["line"] = f"O/U {line}"
                market["source"] = "LIVE"
                market["selections"] = [
                    {"key": f"{spec['key']}_over", "name": f"Over {line}", "price": over_price, "probability": round(100 / over_price)},
                    {"key": f"{spec['key']}_under", "name": f"Under {line}", "price": under_price, "probability": round(100 / under_price)},
                ]
        markets.append(market)
    return markets

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
    live_totals: Optional[dict] = None
    sample: bool = True

now = datetime.now(timezone.utc)
sample_fixtures = [
    Fixture(id="f-001", competition="Indian Premier League", format="T20", venue="Wankhede Stadium, Mumbai", start_time=(now + timedelta(hours=5)).isoformat(), teams=["Mumbai Indians", "Chennai Super Kings"], status="UPCOMING", model_tag="HIGH SIGNAL", confidence=78, odds=[Outcome(name="Mumbai Indians", price=1.82, probability=.58, edge=.055), Outcome(name="Chennai Super Kings", price=2.08, probability=.42, edge=.012)]),
    Fixture(id="f-002", competition="The Hundred", format="Hundred", venue="Lord's, London", start_time=(now + timedelta(days=1, hours=2)).isoformat(), teams=["London Spirit", "Oval Invincibles"], status="UPCOMING", model_tag="BALANCED", confidence=64, odds=[Outcome(name="London Spirit", price=2.15, probability=.44, edge=.025), Outcome(name="Oval Invincibles", price=1.70, probability=.56, edge=.018)]),
    Fixture(id="f-003", competition="International ODI", format="ODI", venue="Kensington Oval, Barbados", start_time=(now + timedelta(days=2, hours=7)).isoformat(), teams=["West Indies", "England"], status="UPCOMING", model_tag="WATCH", confidence=57, odds=[Outcome(name="West Indies", price=2.35, probability=.40, edge=-.012), Outcome(name="England", price=1.62, probability=.60, edge=.026)]),
    Fixture(id="f-004", competition="Test Cricket", format="Test", venue="The Gabba, Brisbane", start_time=(now + timedelta(days=3, hours=1)).isoformat(), teams=["Australia", "India"], status="UPCOMING", model_tag="BALANCED", confidence=61, odds=[Outcome(name="Australia", price=1.85, probability=.54, edge=.021), Outcome(name="India", price=2.60, probability=.38, edge=.005), Outcome(name="Draw", price=8.50, probability=.08, edge=-.004)]),
]

def normalize_live_event(raw: dict) -> Fixture:
    # h2h prices: aggregate across bookmakers then take median for a cleaner card.
    prices: dict[str, list[float]] = {}
    totals_by_line: dict[float, dict[str, list[float]]] = {}
    for bookmaker in raw.get("bookmakers", []):
        for market in bookmaker.get("markets", []):
            key = market.get("key")
            if key == "h2h":
                for outcome in market.get("outcomes", []):
                    price = float(outcome.get("price", 0))
                    if price > 0:
                        prices.setdefault(outcome["name"], []).append(price)
            elif key == "totals":
                for outcome in market.get("outcomes", []):
                    price = float(outcome.get("price", 0))
                    line = outcome.get("point")
                    side = outcome.get("name", "").lower()  # "Over" / "Under"
                    if price > 0 and line is not None and side in ("over", "under"):
                        bucket = totals_by_line.setdefault(float(line), {})
                        bucket.setdefault(side, []).append(price)
    outcomes = []
    for name, values in prices.items():
        values.sort()
        median = values[len(values) // 2]
        outcomes.append(Outcome(name=name, price=round(median, 2), probability=round(1 / median, 3), edge=0))
    outcomes.sort(key=lambda o: o.price)
    # Pick the most-quoted line for totals and take median over/under prices.
    live_totals = None
    if totals_by_line:
        best_line = max(totals_by_line.keys(), key=lambda l: len(totals_by_line[l].get("over", [])) + len(totals_by_line[l].get("under", [])))
        bucket = totals_by_line[best_line]
        over_prices = sorted(bucket.get("over", []))
        under_prices = sorted(bucket.get("under", []))
        if over_prices and under_prices:
            live_totals = {
                "line": best_line,
                "over": round(over_prices[len(over_prices) // 2], 2),
                "under": round(under_prices[len(under_prices) // 2], 2),
            }
    teams = [raw.get("home_team", "Home team"), raw.get("away_team", "Away team")]
    fmt, competition = resolve_format(raw.get("sport_key", ""), raw.get("sport_title", "Cricket"))
    confidence = min(86, max(52, 58 + len(prices) * 4))
    return Fixture(id=raw["id"], competition=competition, format=fmt, venue="Venue pending", start_time=raw["commence_time"], teams=teams, status="UPCOMING", model_tag="LIVE FEED", confidence=confidence, odds=outcomes, live_totals=live_totals, sample=False)

async def fetch_live_fixtures() -> list[Fixture]:
    api_key = os.environ.get("ODDS_API_KEY")
    base_url = os.environ.get("ODDS_API_BASE")
    if not api_key or not base_url:
        return []
    cached = _LIVE_CACHE.get("data")
    cached_at = _LIVE_CACHE.get("at")
    if cached is not None and cached_at and (datetime.now(timezone.utc) - cached_at).total_seconds() < 30:
        return cached
    params = {"apiKey": api_key, "regions": "uk", "markets": "h2h,totals", "oddsFormat": "decimal"}
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
            {"key": fmt, "label": fmt, "count": counts.get(fmt, 0), "profile": FORMAT_PROFILES[fmt]}
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
    return {
        "fixture": fixture,
        "strategy": {"format": fixture.format, "profile": FORMAT_PROFILES.get(fixture.format, DEFAULT_PROFILE)},
        "markets": build_markets(fixture),
        "notice": "Analytical output only — not wagering advice.",
    }

app.include_router(api)
app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","), allow_methods=["*"], allow_headers=["*"])

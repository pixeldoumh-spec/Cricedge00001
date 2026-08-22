from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, APIRouter, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pydantic import BaseModel, Field
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
    

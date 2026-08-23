"""Canonical men's ODI O3: O0 plus one batting/bowling interaction term."""
from __future__ import annotations
from datetime import date
from typing import Any, Dict, Iterable, List
from .odi_o0_features import FeatureEngine as O0FeatureEngine
O3_FEATURE_NAME="team_a_minus_team_b_batting_bowling_interaction"
class O3FeatureEngine(O0FeatureEngine):
    def features_for(self,team_a:str,team_b:str)->Dict[str,float]:
        v=super().features_for(team_a,team_b); bd=v["team_a_batting_runs_per_ball"]-v["team_b_batting_runs_per_ball"]; wd=v["team_a_runs_conceded_per_ball"]-v["team_b_runs_conceded_per_ball"]; v[O3_FEATURE_NAME]=float(bd*wd); return v
def _date(match:Dict[str,Any])->date:return date.fromisoformat(str(match["info"]["dates"][0]))
def build_feature_rows(matches:Iterable[Dict[str,Any]])->List[Dict[str,Any]]:
    ordered=sorted(matches,key=lambda m:(_date(m),str(m.get("_match_id","")))); engine=O3FeatureEngine(); rows=[]
    for match in ordered:
        info=match["info"]
        if info.get("gender")!="male" or info.get("match_type")!="ODI":continue
        teams=list(info["teams"]);winner=info.get("outcome",{}).get("winner")
        if winner not in teams:engine.update(match);continue
        a,b=teams;rows.append({"match_id":str(match.get("_match_id","")),"date":str(info["dates"][0]),"team_a":a,"team_b":b,"target":int(winner==a),"features":engine.features_for(a,b)});engine.update(match)
    return rows

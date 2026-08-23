"""Canonical men's ODI O2: O0 plus wicket-preservation rate."""
from __future__ import annotations
from collections import defaultdict
from datetime import date
from typing import Any, Dict, Iterable, List
from .odi_o0_features import FeatureEngine as O0FeatureEngine
O2_FEATURE_NAME="team_a_minus_team_b_wicket_preservation_rate"
class O2FeatureEngine(O0FeatureEngine):
    def __init__(self)->None: super().__init__(); self._innings_count=defaultdict(int); self._wickets_lost=defaultdict(int)
    @staticmethod
    def _preservation(innings:int,wickets_lost:int)->float:return float((10*innings-wickets_lost)/(10*innings)) if innings else 0.0
    def features_for(self,team_a:str,team_b:str)->Dict[str,float]:
        v=super().features_for(team_a,team_b); v[O2_FEATURE_NAME]=self._preservation(self._innings_count[team_a],self._wickets_lost[team_a])-self._preservation(self._innings_count[team_b],self._wickets_lost[team_b]); return v
    def update(self,match:Dict[str,Any])->None:
        for innings in match.get("innings",[]):
            team=innings["team"]; wickets=0
            for over in innings.get("overs",[]):
                for delivery in over.get("deliveries",[]):
                    for wicket in delivery.get("wickets",[]):
                        if wicket.get("kind") not in {"retired hurt","retired not out"}:wickets+=1
            self._innings_count[team]+=1; self._wickets_lost[team]+=min(wickets,10)
        super().update(match)
def _date(match:Dict[str,Any])->date:return date.fromisoformat(str(match["info"]["dates"][0]))
def build_feature_rows(matches:Iterable[Dict[str,Any]])->List[Dict[str,Any]]:
    ordered=sorted(matches,key=lambda m:(_date(m),str(m.get("_match_id","")))); engine=O2FeatureEngine(); rows=[]
    for match in ordered:
        info=match["info"]
        if info.get("gender")!="male" or info.get("match_type")!="ODI":continue
        teams=list(info["teams"]); winner=info.get("outcome",{}).get("winner")
        if winner not in teams:engine.update(match);continue
        a,b=teams;rows.append({"match_id":str(match.get("_match_id","")),"date":str(info["dates"][0]),"team_a":a,"team_b":b,"target":int(winner==a),"features":engine.features_for(a,b)});engine.update(match)
    return rows

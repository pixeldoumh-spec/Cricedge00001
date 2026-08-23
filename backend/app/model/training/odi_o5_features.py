"""Canonical men's ODI O5 feature generation with a fixed 20-match half-life."""
from __future__ import annotations
from dataclasses import dataclass,field
from datetime import date
from typing import Dict,Iterable,List,Tuple
import math
from .odi_o0_features import FEATURE_NAMES
O5_HALF_LIFE_MATCHES=20.0; _DECAY=math.exp(-math.log(2.0)/O5_HALF_LIFE_MATCHES)
@dataclass
class TeamState:
 decisive_matches:float=0.0; wins:float=0.0; runs_scored:float=0.0; balls_batted:float=0.0; wickets_taken:float=0.0; balls_bowled:float=0.0; runs_conceded:float=0.0; chase_decisive:float=0.0; chase_wins:float=0.0; defend_decisive:float=0.0; defend_wins:float=0.0
@dataclass
class FeatureEngine:
 states:Dict[str,TeamState]=field(default_factory=dict)
 def _state(self,team):return self.states.setdefault(team,TeamState())
 def _decay(self):
  for s in self.states.values():
   for n in s.__dataclass_fields__:setattr(s,n,getattr(s,n)*_DECAY)
 @staticmethod
 def _ratio(num,den):return float(num/den) if den else 0.0
 def _metrics(self,team):
  s=self._state(team);return [self._ratio(s.wins,s.decisive_matches),self._ratio(s.runs_scored,s.balls_batted),self._ratio(s.wickets_taken,s.balls_bowled),self._ratio(s.runs_conceded,s.balls_bowled),self._ratio(s.chase_wins,s.chase_decisive),self._ratio(s.defend_wins,s.defend_decisive)]
 def features_for(self,a,b):
  x,y=self._metrics(a),self._metrics(b); strength=sum(i-j for i,j in zip(x,y))/6.0;return dict(zip(FEATURE_NAMES,[x[0],y[0],x[1],y[1],x[2],y[2],x[3],y[3],x[4],y[4],x[5],y[5],strength]))
 def update(self,match):
  info=match["info"];teams=list(info["teams"])
  if len(teams)!=2:raise ValueError("ODI O5 requires exactly two teams")
  winner=info.get("outcome",{}).get("winner");innings=match.get("innings",[]);batting={t:(0,0) for t in teams};bowling={t:(0,0,0) for t in teams}
  for inn in innings:
   bt=inn["team"];runs=balls=wickets=0
   for over in inn.get("overs",[]):
    for d in over.get("deliveries",[]):
     runs+=int(d.get("runs",{}).get("total",0));ex=d.get("extras",{})
     if "wides" not in ex and "noballs" not in ex:balls+=1
     for w in d.get("wickets",[]):
      if w.get("kind") not in {"retired hurt","retired not out"}:wickets+=1
   opp=teams[1] if bt==teams[0] else teams[0];r,b=batting[bt];batting[bt]=(r+runs,b+balls);rc,bb,w=bowling[opp];bowling[opp]=(rc+runs,bb+balls,w+wickets)
  first=innings[0]["team"] if innings else None;second=innings[1]["team"] if len(innings)>1 else None;self._decay()
  for team in teams:
   s=self._state(team);r,b=batting[team];rc,bb,wt=bowling[team];s.runs_scored+=r;s.balls_batted+=b;s.runs_conceded+=rc;s.balls_bowled+=bb;s.wickets_taken+=wt
   if winner in teams:
    s.decisive_matches+=1;s.wins+=float(winner==team)
    if team==second:s.chase_decisive+=1;s.chase_wins+=float(winner==team)
    elif team==first:s.defend_decisive+=1;s.defend_wins+=float(winner==team)
def _date(m):return date.fromisoformat(str(m["info"]["dates"][0]))
def build_feature_rows(matches:Iterable[Dict])->List[Dict]:
 ordered=sorted(matches,key=lambda m:(_date(m),str(m.get("_match_id",""))));e=FeatureEngine();rows=[]
 for m in ordered:
  i=m["info"]
  if i.get("gender")!="male" or i.get("match_type")!="ODI":continue
  teams=list(i["teams"]);w=i.get("outcome",{}).get("winner")
  if w not in teams:e.update(m);continue
  a,b=teams;rows.append({"match_id":str(m.get("_match_id","")),"date":str(i["dates"][0]),"team_a":a,"team_b":b,"target":int(w==a),"features":e.features_for(a,b)});e.update(m)
 return rows

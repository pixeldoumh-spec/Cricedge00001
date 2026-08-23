"""ODI O8 level-plus-chronological-change feature generation.

O8 keeps every frozen O0 level feature and adds change signals only for
components identified by the committed O6 drift diagnosis. The change signal
uses each team's full pre-match history split into older/newer chronological
halves; there is no tunable recency window or decay parameter.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple
import numpy as np
from .odi_o0_features import FEATURE_NAMES, FeatureEngine
O8_FEATURE_NAMES=FEATURE_NAMES+["team_a_win_rate_change","team_b_win_rate_change","team_a_batting_runs_per_ball_change","team_b_batting_runs_per_ball_change","team_a_chase_win_rate_change","team_b_chase_win_rate_change","team_a_defend_win_rate_change","team_b_defend_win_rate_change","team_a_minus_team_b_strength_change"]
@dataclass
class MatchContribution:
 decisive:int=0;wins:int=0;runs_scored:int=0;balls_batted:int=0;wickets_taken:int=0;balls_bowled:int=0;runs_conceded:int=0;chase_decisive:int=0;chase_wins:int=0;defend_decisive:int=0;defend_wins:int=0
def _ratio(num,den):return float(num/den) if den else 0.0
def _component_metrics(history):
 s=MatchContribution()
 for h in history:
  for n in s.__dataclass_fields__:setattr(s,n,getattr(s,n)+getattr(h,n))
 return np.array([_ratio(s.wins,s.decisive),_ratio(s.runs_scored,s.balls_batted),_ratio(s.wickets_taken,s.balls_bowled),_ratio(s.runs_conceded,s.balls_bowled),_ratio(s.chase_wins,s.chase_decisive),_ratio(s.defend_wins,s.defend_decisive)],dtype=float)
def _change(history):
 if len(history)<2:return np.zeros(6,dtype=float)
 mid=len(history)//2;return _component_metrics(history[mid:])-_component_metrics(history[:mid])
@dataclass
class O8FeatureEngine:
 base:FeatureEngine=field(default_factory=FeatureEngine);histories:Dict[str,List[MatchContribution]]=field(default_factory=dict)
 def _history(self,team):return self.histories.setdefault(team,[])
 def _level(self,team):return np.asarray(self.base._metrics(team),dtype=float)
 def _strength_change(self,a,b):return float(np.mean(_change(self._history(a))-_change(self._history(b))))
 def features_for(self,a,b):
  x,y=self._level(a),self._level(b);ca,cb=_change(self._history(a)),_change(self._history(b));return dict(zip(O8_FEATURE_NAMES,[x[0],y[0],x[1],y[1],x[2],y[2],x[3],y[3],x[4],y[4],x[5],y[5],float(np.mean(x-y)),ca[0],cb[0],ca[1],cb[1],ca[4],cb[4],ca[5],cb[5],self._strength_change(a,b)]))
 def update(self,match):
  info=match["info"];teams=list(info["teams"])
  if len(teams)!=2:raise ValueError("ODI O8 requires exactly two teams")
  winner=info.get("outcome",{}).get("winner");innings=match.get("innings",[]);batting={t:(0,0) for t in teams};bowling={t:(0,0,0) for t in teams}
  for inn in innings:
   bt=inn["team"];runs=balls=wickets=0
   for over in inn.get("overs",[]):
    for d in over.get("deliveries",[]):
     runs+=int(d.get("runs",{}).get("total",0));ex=d.get("extras",{})
     if "wides" not in ex and "noballs" not in ex:balls+=1
     for w in d.get("wickets",[]):
      if w.get("kind") not in {"retired hurt","retired not out"}:wickets+=1
   opp=teams[1] if bt==teams[0] else teams[0];r,b=batting[bt];batting[bt]=(r+runs,b+balls);rc,bb,wt=bowling[opp];bowling[opp]=(rc+runs,bb+balls,wt+wickets)
  first=innings[0]["team"] if innings else None;second=innings[1]["team"] if len(innings)>1 else None
  for t in teams:
   r,b=batting[t];rc,bb,wt=bowling[t];self._history(t).append(MatchContribution(int(winner in teams),int(winner==t),r,b,wt,bb,rc,int(winner in teams and t==second),int(winner in teams and t==second and winner==t),int(winner in teams and t==first),int(winner in teams and t==first and winner==t)))
  self.base.update(match)
def build_feature_rows(matches):
 ordered=sorted(matches,key=lambda m:(str(m["info"]["dates"][0]),str(m.get("_match_id",""))));e=O8FeatureEngine();rows=[]
 for m in ordered:
  i=m["info"]
  if i.get("gender")!="male" or i.get("match_type")!="ODI":continue
  teams=list(i["teams"]);w=i.get("outcome",{}).get("winner")
  if w not in teams:e.update(m);continue
  a,b=teams;rows.append({"match_id":str(m.get("_match_id","")),"date":str(i["dates"][0]),"team_a":a,"team_b":b,"target":int(w==a),"features":e.features_for(a,b)});e.update(m)
 return rows

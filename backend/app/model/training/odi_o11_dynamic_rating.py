"""Men's ODI O11: pre-match opponent-relative dynamic team rating."""
from __future__ import annotations
from dataclasses import dataclass,field
from datetime import date
from typing import Any,Dict,Iterable,List
from .odi_o0_features import FEATURE_NAMES as O0_FEATURE_NAMES,FeatureEngine as O0FeatureEngine
O11_FEATURE_NAMES=[*O0_FEATURE_NAMES,"team_a_minus_team_b_elo_rating"];INITIAL_RATING=1500.0;K_FACTOR=20.0;RATING_SCALE=400.0
@dataclass
class DynamicRatingEngine:
 ratings:Dict[str,float]=field(default_factory=dict)
 def rating(self,t):return float(self.ratings.get(t,INITIAL_RATING))
 @staticmethod
 def expected(a,b):return 1.0/(1.0+10.0**((b-a)/RATING_SCALE))
 def feature(self,a,b):return self.rating(a)-self.rating(b)
 def update(self,a,b,winner):
  if winner not in {a,b}:return
  ra,rb=self.rating(a),self.rating(b);ea=self.expected(ra,rb);sa=1.0 if winner==a else 0.0
  self.ratings[a]=ra+K_FACTOR*(sa-ea);self.ratings[b]=rb+K_FACTOR*((1.0-sa)-(1.0-ea))
def _date(m):return date.fromisoformat(str(m["info"]["dates"][0]))
def build_feature_rows(matches:Iterable[Dict[str,Any]])->List[Dict[str,Any]]:
 ordered=sorted(matches,key=lambda m:(_date(m),str(m.get("_match_id",""))));o0=O0FeatureEngine();rating=DynamicRatingEngine();rows=[]
 for m in ordered:
  i=m["info"]
  if i.get("gender")!="male" or i.get("match_type")!="ODI":continue
  teams=list(i["teams"])
  if len(teams)!=2:raise ValueError("ODI O11 requires exactly two teams")
  w=i.get("outcome",{}).get("winner")
  if w in teams:
   a,b=teams;base=o0.features_for(a,b);base["team_a_minus_team_b_elo_rating"]=rating.feature(a,b);rows.append({"match_id":str(m.get("_match_id","")),"date":str(i["dates"][0]),"team_a":a,"team_b":b,"target":int(w==a),"features":base})
  o0.update(m)
  if w in teams:rating.update(teams[0],teams[1],w)
 return rows

"""O6 component-level temporal drift diagnostic for frozen ODI O0 features."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Any,Dict,Iterable,List,Mapping,Sequence
from .odi_o0_features import FEATURE_NAMES
COMPONENTS={"recent_win_rate":("team_a_recent_win_rate","team_b_recent_win_rate"),"batting_runs_per_ball":("team_a_batting_runs_per_ball","team_b_batting_runs_per_ball"),"wickets_per_ball":("team_a_wickets_per_ball","team_b_wickets_per_ball"),"runs_conceded_per_ball":("team_a_runs_conceded_per_ball","team_b_runs_conceded_per_ball"),"chase_win_rate":("team_a_chase_win_rate","team_b_chase_win_rate"),"defend_win_rate":("team_a_defend_win_rate","team_b_defend_win_rate"),"strength":("team_a_minus_team_b_strength",None)}
@dataclass(frozen=True)
class DriftSummary: component:str;n:int;early_mean:float;late_mean:float;mean_shift:float;early_abs_mean:float;late_abs_mean:float;early_outcome_gap:float;late_outcome_gap:float;stability_ratio:float
def _component_value(f,pair):a,b=pair;return float(f[a]) if b is None else float(f[a])-float(f[b])
def _outcome_gap(values,targets):
 if not values:return 0.0
 pos=[v for v,y in zip(values,targets) if y==1];neg=[v for v,y in zip(values,targets) if y==0]
 return float(sum(pos)/len(pos)-sum(neg)/len(neg)) if pos and neg else 0.0
def diagnose(rows:Iterable[Mapping[str,Any]],early_fraction:float=0.5)->List[DriftSummary]:
 rows=list(rows)
 if len(rows)!=2440:raise ValueError(f"O6 requires the locked 2440-row ODI population, got {len(rows)}")
 dates=[date.fromisoformat(str(r["date"])) for r in rows]
 if dates!=sorted(dates):raise ValueError("O6 requires chronological row ordering")
 cut=max(1,min(len(rows)-1,int(len(rows)*early_fraction)));out=[]
 for name,pair in COMPONENTS.items():
  vals=[_component_value(r["features"],pair) for r in rows];targets=[int(r["target"]) for r in rows];early,late=vals[:cut],vals[cut:];ea=sum(abs(v) for v in early)/len(early);la=sum(abs(v) for v in late)/len(late);em=sum(early)/len(early);lm=sum(late)/len(late)
  out.append(DriftSummary(name,len(vals),em,lm,lm-em,ea,la,_outcome_gap(early,targets[:cut]),_outcome_gap(late,targets[cut:]),la/ea if ea else float("inf")))
 return out
def to_report(rows):
 s=diagnose(rows);c=[x.component for x in s if abs(x.late_outcome_gap-x.early_outcome_gap)>0.02 and (x.stability_ratio<0.85 or x.stability_ratio>1.15)]
 return {"model":"men_odi_o6","parent_control":"men_odi_o0","status":"diagnostic_only","population":2440,"feature_contract":list(FEATURE_NAMES),"components":[x.__dict__ for x in s],"targeted_decay_candidates":c,"o7_justified":bool(c)}

"""O6 component-level temporal drift diagnostic for frozen ODI O0 features."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from .odi_o0_features import FEATURE_NAMES

# O0 historical components. Each component is represented by the signed
# matchup difference A-B so age/regime comparisons are directionally consistent.
COMPONENTS = {
    "recent_win_rate": ("team_a_recent_win_rate", "team_b_recent_win_rate"),
    "batting_runs_per_ball": ("team_a_batting_runs_per_ball", "team_b_batting_runs_per_ball"),
    "wickets_per_ball": ("team_a_wickets_per_ball", "team_b_wickets_per_ball"),
    "runs_conceded_per_ball": ("team_a_runs_conceded_per_ball", "team_b_runs_conceded_per_ball"),
    "chase_win_rate": ("team_a_chase_win_rate", "team_b_chase_win_rate"),
    "defend_win_rate": ("team_a_defend_win_rate", "team_b_defend_win_rate"),
    "strength": ("team_a_minus_team_b_strength", None),
}

@dataclass(frozen=True)
class DriftSummary:
    component: str
    n: int
    early_mean: float
    late_mean: float
    mean_shift: float
    early_abs_mean: float
    late_abs_mean: float
    early_outcome_gap: float
    late_outcome_gap: float
    stability_ratio: float


def _component_value(features: Mapping[str, float], pair: tuple[str, str | None]) -> float:
    a, b = pair
    if b is None:
        return float(features[a])
    return float(features[a]) - float(features[b])


def _outcome_gap(values: Sequence[float], targets: Sequence[int]) -> float:
    if not values:
        return 0.0
    pos = [v for v, y in zip(values, targets) if y == 1]
    neg = [v for v, y in zip(values, targets) if y == 0]
    if not pos or not neg:
        return 0.0
    return float(sum(pos) / len(pos) - sum(neg) / len(neg))


def diagnose(rows: Iterable[Mapping[str, Any]], early_fraction: float = 0.5) -> List[DriftSummary]:
    """Diagnose component drift without fitting, tuning, or modifying O0.

    Rows must be the frozen chronological O0 population. The diagnostic is
    descriptive only and never uses future observations to construct features.
    """
    rows = list(rows)
    if len(rows) != 2440:
        raise ValueError(f"O6 requires the locked 2440-row ODI population, got {len(rows)}")
    dates = [date.fromisoformat(str(r["date"])) for r in rows]
    if dates != sorted(dates):
        raise ValueError("O6 requires chronological row ordering")
    for row in rows:
        features = row["features"]
        missing = set(FEATURE_NAMES) - set(features)
        if missing:
            raise ValueError(f"O0 feature contract missing: {sorted(missing)}")

    cut = max(1, min(len(rows) - 1, int(len(rows) * early_fraction)))
    summaries: List[DriftSummary] = []
    for name, pair in COMPONENTS.items():
        vals = [_component_value(r["features"], pair) for r in rows]
        targets = [int(r["target"]) for r in rows]
        early, late = vals[:cut], vals[cut:]
        early_abs = sum(abs(v) for v in early) / len(early)
        late_abs = sum(abs(v) for v in late) / len(late)
        early_mean = sum(early) / len(early)
        late_mean = sum(late) / len(late)
        shift = late_mean - early_mean
        # Ratio near 1 means stable magnitude; >1 means larger late magnitude.
        stability = late_abs / early_abs if early_abs else float("inf")
        summaries.append(DriftSummary(
            component=name,
            n=len(vals),
            early_mean=early_mean,
            late_mean=late_mean,
            mean_shift=shift,
            early_abs_mean=early_abs,
            late_abs_mean=late_abs,
            early_outcome_gap=_outcome_gap(early, targets[:cut]),
            late_outcome_gap=_outcome_gap(late, targets[cut:]),
            stability_ratio=stability,
        ))
    return summaries


def to_report(rows: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    summaries = diagnose(rows)
    # A component is only a targeted-decay candidate if its outcome separation
    # changes materially and its magnitude shifts materially; this is a gate,
    # not a model-selection rule.
    candidates = [
        s.component for s in summaries
        if abs(s.late_outcome_gap - s.early_outcome_gap) > 0.02
        and (s.stability_ratio < 0.85 or s.stability_ratio > 1.15)
    ]
    return {
        "model": "men_odi_o6",
        "parent_control": "men_odi_o0",
        "status": "diagnostic_only",
        "population": 2440,
        "feature_contract": list(FEATURE_NAMES),
        "components": [s.__dict__ for s in summaries],
        "targeted_decay_candidates": candidates,
        "o7_justified": bool(candidates),
        "decision_rule": "O7 is justified only when at least one component shows both meaningful temporal magnitude drift and meaningful change in outcome separation; otherwise pursue a different structural hypothesis.",
    }

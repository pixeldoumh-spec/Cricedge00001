"""Low-complexity dual-timescale team-strength representation.

This diagnostic asks whether T20 strength is better represented by a stable
long-run state plus a faster-moving recent state, rather than choosing one
single Elo K. It is deliberately small and interpretable.

Leakage rule: both states are computed strictly before each match and updated
only after its result is known. No calibration is performed here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.model.data.normalizer import CanonicalMatch


@dataclass(frozen=True)
class DualTeamState:
    slow: float = 1500.0
    fast: float = 1500.0


@dataclass(frozen=True)
class DualStrengthFeatures:
    slow_team_elo: float
    slow_opponent_elo: float
    slow_difference: float
    fast_team_elo: float
    fast_opponent_elo: float
    fast_difference: float


class DualTimescaleStrengthEngine:
    """Maintain slow and fast Elo states with fixed, predeclared K values."""

    def __init__(self, slow_k: float = 20.0, fast_k: float = 80.0, initial: float = 1500.0) -> None:
        if slow_k <= 0 or fast_k <= 0:
            raise ValueError("K values must be positive")
        self.slow_k = float(slow_k)
        self.fast_k = float(fast_k)
        self.initial = float(initial)
        self._states: dict[str, DualTeamState] = {}

    def _state(self, team: str) -> DualTeamState:
        return self._states.get(team, DualTeamState(self.initial, self.initial))

    def features_before(self, team: str, opponent: str) -> DualStrengthFeatures:
        a = self._state(team)
        b = self._state(opponent)
        return DualStrengthFeatures(
            slow_team_elo=a.slow,
            slow_opponent_elo=b.slow,
            slow_difference=a.slow - b.slow,
            fast_team_elo=a.fast,
            fast_opponent_elo=b.fast,
            fast_difference=a.fast - b.fast,
        )

    def update_after_match(self, match: CanonicalMatch) -> None:
        if len(match.teams) != 2 or match.winner not in match.teams:
            return
        team, opponent = match.teams
        a = self._state(team)
        b = self._state(opponent)
        score_a = 1.0 if match.winner == team else 0.0

        def update(a_elo: float, b_elo: float, k: float) -> tuple[float, float]:
            expected = 1.0 / (1.0 + 10 ** ((b_elo - a_elo) / 400.0))
            delta = k * (score_a - expected)
            return a_elo + delta, b_elo - delta

        slow_a, slow_b = update(a.slow, b.slow, self.slow_k)
        fast_a, fast_b = update(a.fast, b.fast, self.fast_k)
        self._states[team] = DualTeamState(slow_a, fast_a)
        self._states[opponent] = DualTeamState(slow_b, fast_b)


def build_dual_strength_features(
    matches: Iterable[CanonicalMatch],
    slow_k: float = 20.0,
    fast_k: float = 80.0,
    initial: float = 1500.0,
) -> list[tuple[CanonicalMatch, DualStrengthFeatures]]:
    engine = DualTimescaleStrengthEngine(slow_k=slow_k, fast_k=fast_k, initial=initial)
    rows: list[tuple[CanonicalMatch, DualStrengthFeatures]] = []
    ordered = sorted(matches, key=lambda m: (m.dates[0] if m.dates else "", str(m.teams)))
    for match in ordered:
        if len(match.teams) != 2:
            continue
        team, opponent = match.teams
        rows.append((match, engine.features_before(team, opponent)))
        engine.update_after_match(match)
    return rows

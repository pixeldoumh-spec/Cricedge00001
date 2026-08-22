"""Leakage-safe rolling team form and Elo features."""

from __future__ import annotations

from dataclasses import dataclass

from app.model.data.normalizer import CanonicalMatch


@dataclass(frozen=True)
class TeamState:
    elo: float = 1500.0
    results: tuple[int, ...] = ()


@dataclass(frozen=True)
class TeamPreMatchFeatures:
    team_elo: float
    opponent_elo: float
    elo_difference: float
    team_form_3: float
    team_form_5: float
    team_form_10: float


class TeamFormEngine:
    """Build pre-match team features using only prior matches."""

    def __init__(self, initial_elo: float = 1500.0, k_factor: float = 20.0) -> None:
        self.initial_elo = initial_elo
        self.k_factor = k_factor
        self._states: dict[str, TeamState] = {}

    def _state(self, team: str) -> TeamState:
        return self._states.get(team, TeamState(elo=self.initial_elo))

    @staticmethod
    def _form(results: tuple[int, ...], window: int) -> float:
        recent = results[-window:]
        return sum(recent) / len(recent) if recent else 0.5

    def features_before(self, team: str, opponent: str) -> TeamPreMatchFeatures:
        """Return features from state accumulated strictly before a match."""
        a = self._state(team)
        b = self._state(opponent)
        return TeamPreMatchFeatures(
            team_elo=a.elo,
            opponent_elo=b.elo,
            elo_difference=a.elo - b.elo,
            team_form_3=self._form(a.results, 3),
            team_form_5=self._form(a.results, 5),
            team_form_10=self._form(a.results, 10),
        )

    def update_after_match(self, match: CanonicalMatch) -> None:
        """Update Elo and form only after the match result is known."""
        if len(match.teams) != 2 or match.winner not in match.teams:
            return

        team, opponent = match.teams
        a = self._state(team)
        b = self._state(opponent)
        expected_a = 1.0 / (1.0 + 10 ** ((b.elo - a.elo) / 400.0))
        score_a = 1.0 if match.winner == team else 0.0
        new_a = a.elo + self.k_factor * (score_a - expected_a)
        new_b = b.elo + self.k_factor * ((1.0 - score_a) - (1.0 - expected_a))
        self._states[team] = TeamState(new_a, (*a.results, int(score_a)))
        self._states[opponent] = TeamState(new_b, (*b.results, int(1.0 - score_a)))


def build_team_features(
    matches: list[CanonicalMatch],
    initial_elo: float = 1500.0,
    k_factor: float = 20.0,
) -> list[tuple[CanonicalMatch, TeamPreMatchFeatures]]:
    """Generate leakage-safe features for each trainable two-team match."""
    engine = TeamFormEngine(initial_elo=initial_elo, k_factor=k_factor)
    rows: list[tuple[CanonicalMatch, TeamPreMatchFeatures]] = []
    for match in sorted(matches, key=lambda m: m.dates[0] if m.dates else ""):
        if len(match.teams) != 2:
            continue
        team, opponent = match.teams
        rows.append((match, engine.features_before(team, opponent)))
        engine.update_after_match(match)
    return rows

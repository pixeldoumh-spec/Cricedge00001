"""Leakage-safe venue and head-to-head features."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from app.model.data.normalizer import CanonicalMatch


@dataclass(frozen=True)
class ContextFeatures:
    venue_team_win_rate: float
    venue_bat_first_win_rate: float
    head_to_head_win_rate: float


@dataclass
class VenueState:
    team_wins: int = 0
    team_matches: int = 0
    bat_first_wins: int = 0
    completed_bat_first_matches: int = 0


class ContextFeatureEngine:
    """Accumulate venue/H2H statistics only after each result is known."""

    def __init__(self) -> None:
        self._venues: dict[tuple[str, str], VenueState] = defaultdict(VenueState)
        self._h2h: dict[tuple[str, str], list[int]] = defaultdict(list)

    @staticmethod
    def _rate(wins: int, matches: int, prior: float = 0.5) -> float:
        return wins / matches if matches else prior

    def features_before(self, match: CanonicalMatch) -> ContextFeatures:
        if len(match.teams) != 2:
            return ContextFeatures(0.5, 0.5, 0.5)
        team, opponent = match.teams
        venue_key = (match.venue or "<unknown>", team)
        venue = self._venues[venue_key]
        h2h = self._h2h[(team, opponent)]
        return ContextFeatures(
            venue_team_win_rate=self._rate(venue.team_wins, venue.team_matches),
            venue_bat_first_win_rate=self._rate(
                venue.bat_first_wins, venue.completed_bat_first_matches
            ),
            head_to_head_win_rate=self._rate(sum(h2h), len(h2h)),
        )

    def update_after_match(self, match: CanonicalMatch) -> None:
        if len(match.teams) != 2 or match.winner not in match.teams:
            return
        team, opponent = match.teams
        team_won = int(match.winner == team)
        venue = self._venues[(match.venue or "<unknown>", team)]
        venue.team_matches += 1
        venue.team_wins += team_won
        self._h2h[(team, opponent)].append(team_won)

        # Bat-first outcome requires the toss to have been recorded. We only
        # count completed matches where the toss decision is known and the
        # winning side can be determined from the match outcome.
        if match.toss_winner and match.toss_decision == "bat":
            venue.completed_bat_first_matches += 1
            venue.bat_first_wins += int(match.winner == match.toss_winner)


def build_context_features(
    matches: list[CanonicalMatch],
) -> list[tuple[CanonicalMatch, ContextFeatures]]:
    """Generate chronological, leakage-safe context features."""
    engine = ContextFeatureEngine()
    rows: list[tuple[CanonicalMatch, ContextFeatures]] = []
    for match in sorted(matches, key=lambda m: m.dates[0] if m.dates else ""):
        if len(match.teams) != 2:
            continue
        rows.append((match, engine.features_before(match)))
        engine.update_after_match(match)
    return rows

"""Canonical pre-match feature vector.

This module defines the stable feature contract used by the future CricEdge
pre-match model. It intentionally contains no feature calculation or model
training logic yet.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PreMatchFeatures:
    """Point-in-time features available before a match prediction."""

    # Team strength
    team_elo: float
    opponent_elo: float
    elo_difference: float

    # Recent team form
    team_form_3: float
    team_form_5: float
    team_form_10: float

    # Aggregate batting / bowling strength
    batting_strength: float
    bowling_strength: float
    opponent_batting_strength: float
    opponent_bowling_strength: float

    # Venue/context
    venue_team_win_rate: float
    venue_bat_first_win_rate: float
    home_advantage: float

    # Historical matchup
    head_to_head_win_rate: float

    # Optional pre-match context. These are deliberately nullable because
    # some historical datasets do not contain the information.
    toss_winner_is_team: Optional[float] = None
    toss_bat_first: Optional[float] = None

    def as_dict(self) -> dict[str, Optional[float]]:
        """Return a model-ready mapping without changing feature names."""
        return {
            name: getattr(self, name)
            for name in self.__dataclass_fields__
        }

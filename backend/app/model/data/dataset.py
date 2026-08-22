"""Dataset-facing helpers built on the canonical Cricsheet representation."""

from __future__ import annotations

from .normalizer import CanonicalMatch


def is_trainable_t20(match: CanonicalMatch) -> bool:
    """Return whether a canonical match is suitable for the first T20 dataset."""
    return (
        match.match_type == "T20"
        and len(match.teams) == 2
        and match.winner in match.teams
        and match.gender == "male"
    )


def match_date(match: CanonicalMatch) -> str:
    """Return the earliest recorded match date for chronological ordering."""
    return min(match.dates) if match.dates else ""

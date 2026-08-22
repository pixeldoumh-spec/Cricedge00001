"""Leakage-safe chronological dataset splitting."""

from __future__ import annotations

from collections.abc import Sequence

from app.model.data.normalizer import CanonicalMatch


def chronological_split(
    matches: Sequence[CanonicalMatch],
    train_ratio: float = 0.70,
    validation_ratio: float = 0.15,
) -> tuple[list[CanonicalMatch], list[CanonicalMatch], list[CanonicalMatch]]:
    """Split matches chronologically into train, validation and test sets."""
    if not 0 < train_ratio < 1 or not 0 <= validation_ratio < 1:
        raise ValueError("split ratios must be between 0 and 1")
    if train_ratio + validation_ratio >= 1:
        raise ValueError("train_ratio + validation_ratio must be less than 1")

    ordered = sorted(matches, key=lambda match: match.dates[0] if match.dates else "")
    n = len(ordered)
    train_end = int(n * train_ratio)
    validation_end = train_end + int(n * validation_ratio)
    return ordered[:train_end], ordered[train_end:validation_end], ordered[validation_end:]

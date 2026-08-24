"""Focused tests for T20 Challenger A's isolated denominator change."""

from __future__ import annotations

from app.model.data.normalizer import normalize_match
from app.model.training.challenger_a import LegalBallStrengthEngine


def _match_with_extras() -> object:
    raw = {
        "info": {
            "dates": ["2024-01-01"],
            "teams": ["A", "B"],
            "gender": "male",
            "match_type": "T20",
            "outcome": {"winner": "A"},
        },
        "innings": [
            {
                "team": "A",
                "overs": [
                    {"over": 0, "deliveries": [
                        {"batter": "a", "bowler": "b", "non_striker": "c", "runs": {"batter": 1, "total": 1}},
                        {"batter": "a", "bowler": "b", "non_striker": "c", "runs": {"batter": 0, "total": 1}, "extras": {"wides": 1}},
                        {"batter": "a", "bowler": "b", "non_striker": "c", "runs": {"batter": 0, "total": 1}, "extras": {"noballs": 1}},
                        {"batter": "a", "bowler": "b", "non_striker": "c", "runs": {"batter": 2, "total": 2}, "extras": {"byes": 0}},
                    ]}
                ],
            }
        ],
    }
    return normalize_match("m1", raw)


def test_normalizer_preserves_delivery_extra_types():
    match = _match_with_extras()
    deliveries = match.deliveries
    assert deliveries[0].legal_ball is True
    assert deliveries[1].wides == 1
    assert deliveries[1].legal_ball is False
    assert deliveries[2].no_balls == 1
    assert deliveries[2].legal_ball is False
    assert deliveries[3].legal_ball is True


def test_challenger_uses_only_legal_deliveries_as_denominator():
    match = _match_with_extras()
    engine = LegalBallStrengthEngine()
    engine.update_after_match(match)
    features = engine.features_before("A", "B")
    # Four recorded deliveries, but only two legal deliveries.
    assert features.batting_run_rate == 9.0
    assert engine._state["A"].balls == 2
    assert engine._state["B"].balls_bowled == 2

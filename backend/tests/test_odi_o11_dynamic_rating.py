import numpy as np

from backend.app.model.training.odi_o11_dynamic_rating import (
    INITIAL_RATING,
    K_FACTOR,
    DynamicRatingEngine,
    O11_FEATURE_NAMES,
)


def test_initial_ratings_are_equal_and_difference_is_zero():
    engine = DynamicRatingEngine()
    assert engine.rating("A") == INITIAL_RATING
    assert engine.rating("B") == INITIAL_RATING
    assert engine.feature("A", "B") == 0.0


def test_winner_rating_increases_and_loser_decreases():
    engine = DynamicRatingEngine()
    before_a = engine.rating("A")
    before_b = engine.rating("B")
    engine.update("A", "B", "A")
    assert engine.rating("A") > before_a
    assert engine.rating("B") < before_b
    assert np.isclose(
        (engine.rating("A") - before_a) + (engine.rating("B") - before_b),
        0.0,
    )


def test_tie_or_no_result_does_not_change_ratings():
    engine = DynamicRatingEngine()
    before = dict(engine.ratings)
    engine.update("A", "B", "Tie")
    assert engine.ratings == before
    engine.update("A", "B", "No result")
    assert engine.ratings == before


def test_rating_feature_is_pre_match_state():
    engine = DynamicRatingEngine()
    assert engine.feature("A", "B") == 0.0
    engine.update("A", "B", "A")
    assert engine.feature("A", "B") > 0.0


def test_o11_adds_exactly_one_feature_to_o0():
    assert len(O11_FEATURE_NAMES) == 14
    assert O11_FEATURE_NAMES[-1] == "team_a_minus_team_b_elo_rating"
    assert O11_FEATURE_NAMES[:13] == [
        "team_a_recent_win_rate", "team_b_recent_win_rate",
        "team_a_batting_runs_per_ball", "team_b_batting_runs_per_ball",
        "team_a_wickets_per_ball", "team_b_wickets_per_ball",
        "team_a_runs_conceded_per_ball", "team_b_runs_conceded_per_ball",
        "team_a_chase_win_rate", "team_b_chase_win_rate",
        "team_a_defend_win_rate", "team_b_defend_win_rate",
        "team_a_minus_team_b_strength",
    ]

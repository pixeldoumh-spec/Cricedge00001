import numpy as np

from app.model.training.odi_o14_model import augment_o14, training_anchored_time
from app.model.training.odi_o0_features import FEATURE_NAMES


def test_o14_has_exactly_three_temporal_interactions():
    X = np.arange(13 * 4, dtype=float).reshape(4, 13)
    t = np.array([0.0, 0.25, 0.5, 0.75])
    Z = augment_o14(X, t)
    assert Z.shape == (4, 16)


def test_o14_interactions_are_semantic_signed_differences():
    X = np.zeros((1, 13), dtype=float)
    pairs = [
        (FEATURE_NAMES.index("team_a_recent_win_rate"), FEATURE_NAMES.index("team_b_recent_win_rate")),
        (FEATURE_NAMES.index("team_a_runs_conceded_per_ball"), FEATURE_NAMES.index("team_b_runs_conceded_per_ball")),
        (FEATURE_NAMES.index("team_a_defend_win_rate"), FEATURE_NAMES.index("team_b_defend_win_rate")),
    ]
    for i, (a, b) in enumerate(pairs):
        X[0, a] = 0.8
        X[0, b] = 0.3
    Z = augment_o14(X, np.array([2.0]))
    assert np.allclose(Z[0, -3:], [1.0, 1.0, 1.0])


def test_training_time_is_training_anchored_and_allows_future_extrapolation():
    t = training_anchored_time(10, 0, 4)
    assert t[0] == 0.0
    assert t[4] == 1.0
    assert t[9] > 1.0

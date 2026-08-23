import numpy as np

from app.model.training.odi_o0_features import FEATURE_NAMES
from app.model.training.odi_o13_model import augment_o13, training_anchored_time


def test_o13_has_one_temporal_interaction_per_o0_feature():
    X = np.arange(26, dtype=float).reshape(2, len(FEATURE_NAMES))
    t = np.array([0.0, 1.0])
    out = augment_o13(X, t)
    assert out.shape == (2, 26)
    np.testing.assert_allclose(out[:, :13], X)
    np.testing.assert_allclose(out[:, 13:], X * t[:, None])


def test_training_anchored_time_extrapolates_future_rows():
    t = training_anchored_time(5, 0, 2)
    np.testing.assert_allclose(t, [0.0, 0.5, 1.0, 1.5, 2.0])


def test_o13_requires_exact_frozen_o0_width():
    X = np.zeros((3, 12), dtype=float)
    t = np.zeros(3)
    try:
        augment_o13(X, t)
    except ValueError as exc:
        assert "13-feature" in str(exc)
    else:
        raise AssertionError("expected exact O0 feature-width validation")

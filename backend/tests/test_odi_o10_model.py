import numpy as np
import pytest

from app.model.training.odi_o10_model import (
    CANDIDATE_C,
    fit_o10,
    predict_raw,
    select_C_by_validation_log_loss,
)


def test_o10_contract_uses_exact_13_features():
    X = np.zeros((8, 13))
    y = np.array([0, 1] * 4)
    bundle = fit_o10(X, y, 1.0)
    assert bundle.C == 1.0
    assert predict_raw(bundle, X).shape == (8,)


def test_o10_rejects_wrong_feature_width():
    with pytest.raises(ValueError):
        fit_o10(np.zeros((8, 12)), np.array([0, 1] * 4), 1.0)


def test_o10_rejects_uncatalogued_regularization():
    with pytest.raises(ValueError):
        fit_o10(np.zeros((8, 13)), np.array([0, 1] * 4), 0.1)


def test_o10_candidates_are_frozen():
    assert CANDIDATE_C == (0.25, 0.5, 1.0, 2.0, 4.0)


def test_o10_selection_uses_only_validation_data():
    rng = np.random.default_rng(7)
    X_train = rng.normal(size=(80, 13))
    y_train = np.array([0, 1] * 40)
    X_val = rng.normal(size=(20, 13))
    y_val = np.array([0, 1] * 10)
    C, scores = select_C_by_validation_log_loss(X_train, y_train, X_val, y_val)
    assert C in CANDIDATE_C
    assert len(scores) == len(CANDIDATE_C)


def test_o10_does_not_mutate_inputs():
    rng = np.random.default_rng(11)
    X = rng.normal(size=(20, 13))
    y = np.array([0, 1] * 10)
    X_before = X.copy()
    y_before = y.copy()
    fit_o10(X, y, 1.0)
    np.testing.assert_array_equal(X, X_before)
    np.testing.assert_array_equal(y, y_before)

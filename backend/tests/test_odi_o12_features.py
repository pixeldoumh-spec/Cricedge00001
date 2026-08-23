from backend.app.model.training.odi_o12_features import FEATURE_NAME, add_o12_feature, history_context


def test_history_context_uses_minimum_pre_match_history():
    assert history_context(0, 10) == 0.0
    assert history_context(10, 10) > 0.0
    assert history_context(50, 100) == history_context(50, 50)


def test_negative_history_rejected():
    try:
        history_context(-1, 10)
    except ValueError:
        return
    assert False, "negative pre-match history must be rejected"


def test_o12_adds_exactly_one_feature_and_preserves_o0():
    o0 = {"team_a_minus_team_b_strength": 0.2, "team_a_recent_win_rate": 0.6}
    out = add_o12_feature(o0, 50, 100)
    assert set(out) == set(o0) | {FEATURE_NAME}
    assert out["team_a_minus_team_b_strength"] == o0["team_a_minus_team_b_strength"]
    assert o0.get(FEATURE_NAME) is None


def test_zero_history_creates_zero_interaction_without_outcome_access():
    o0 = {"team_a_minus_team_b_strength": -0.3}
    out = add_o12_feature(o0, 0, 20)
    assert out[FEATURE_NAME] == 0.0


def test_current_match_outcome_is_not_an_input():
    # The function accepts only frozen O0 features and pre-match history counts.
    # No outcome/innings/current-match argument exists in the API.
    assert "outcome" not in add_o12_feature.__code__.co_varnames
    assert "innings" not in add_o12_feature.__code__.co_varnames

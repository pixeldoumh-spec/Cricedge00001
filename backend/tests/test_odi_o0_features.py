from backend.app.model.training.odi_o0_features import FEATURE_NAMES, FeatureEngine

def test_o0_feature_contract_exactly_13():
    assert len(FEATURE_NAMES) == 13

def test_o0_strength_is_mean_pairwise_difference():
    e=FeatureEngine(); f=e.features_for('A','B')
    assert f['team_a_minus_team_b_strength']==0.0

def test_o0_requires_two_teams():
    e=FeatureEngine()
    try: e.update({'info': {'teams':['A']}, 'innings':[]})
    except ValueError: return
    assert False

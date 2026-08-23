from backend.app.model.training.odi_feature_fingerprint import (
    LEGACY_V0_EXPECTED,
    fingerprint_legacy_v0,
    fingerprint_v1,
)


def test_legacy_v0_is_deterministic_and_key_order_independent():
    rows_a = [{"target": 1, "features": {"b": 2, "a": 1}}]
    rows_b = [{"features": {"a": 1, "b": 2}, "target": 1}]
    assert fingerprint_legacy_v0(rows_a) == fingerprint_legacy_v0(rows_b)


def test_v1_is_explicitly_versioned_from_legacy_v0():
    rows = [{"target": 0, "features": {"x": 0.25}}]
    assert fingerprint_v1(rows) == fingerprint_legacy_v0(rows)


def test_locked_legacy_value_is_pinned():
    assert LEGACY_V0_EXPECTED == "a64c5b01d338b08e018c92bf34c30355e41a380ba0209f190fad457bccc60d42"

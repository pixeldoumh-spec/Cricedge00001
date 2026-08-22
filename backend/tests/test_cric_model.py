import pytest
import numpy as np
from cric_model import (
    norm_sf,
    predict_fixture,
    _mean_std,
)


class TestNormSF:
    """Test norm_sf (normal survival function)"""

    def test_norm_sf_at_mean(self):
        """At the mean, probability should be ~0.5"""
        result = norm_sf(100, 100, 10)
        assert 0.48 < result < 0.52

    def test_norm_sf_invalid_sd(self):
        """With sd <= 0, should return 0.5"""
        result = norm_sf(100, 100, 0)
        assert result == 0.5

    def test_norm_sf_bounds(self):
        """Result should be between 0.02 and 0.98"""
        result = norm_sf(200, 100, 10)
        assert 0.02 <= result <= 0.98


class TestMeanStd:
    """Test _mean_std utility"""

    def test_mean_std_with_insufficient_data(self):
        """With < 3 values, should return fallback"""
        result = _mean_std([1, 2], 100, 25)
        assert result == (100, 25)

    def test_mean_std_with_sufficient_data(self):
        """With >= 3 values, should compute actual mean/std"""
        values = [100, 110, 105, 95, 120]
        mean, std = _mean_std(values, 50, 10)
        assert mean != 50  # Should be actual mean
        assert std != 10  # Should be actual std


class TestPredictFixture:
    """Test predict_fixture function"""

    def test_predict_fixture_no_artifact(self):
        """Without artifact, should return LOW quality prediction"""
        result = predict_fixture(None, "T20", "India", "Australia")
        assert result["data_quality"] == "LOW"
        assert result["win"] is None

    def test_predict_fixture_returns_required_fields(self):
        """Result should have required structure"""
        result = predict_fixture(None, "T20", "India", "Australia")
        required_fields = [
            "bucket",
            "data_quality",
            "matches",
            "win",
            "draw_rate",
            "teams",
        ]
        for field in required_fields:
            assert field in result

    def test_predict_fixture_format_mapping(self):
        """Should correctly map formats to buckets"""
        # Test that different formats map correctly
        for fmt, expected_bucket in [
            ("T20", "T20"),
            ("Hundred", "T20"),
            ("ODI", "ODI"),
            ("Test", "Test"),
        ]:
            result = predict_fixture(None, fmt, "India", "Australia")
            assert result["bucket"] == expected_bucket

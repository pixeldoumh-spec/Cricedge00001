import pytest
from fastapi.testclient import TestClient
from server import app

client = TestClient(app)

class TestFixturesEndpoint:
    """Test /api/fixtures endpoint"""

    def test_get_fixtures_returns_list(self):
        """GET /fixtures should return a list of fixtures"""
        response = client.get("/api/fixtures")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_fixtures_with_format_filter(self):
        """GET /fixtures?format=T20 should filter by format"""
        response = client.get("/api/fixtures?format=T20")
        assert response.status_code == 200
        fixtures = response.json()
        assert isinstance(fixtures, list)
        # All returned fixtures should be T20 format
        for fixture in fixtures:
            assert fixture["format"] == "T20"

    def test_get_fixtures_invalid_format(self):
        """GET /fixtures?format=INVALID should still return all fixtures or error gracefully"""
        response = client.get("/api/fixtures?format=INVALID")
        # Should either return empty list or status 200 with filtered results
        assert response.status_code in [200, 400]


class TestFixtureFormatsEndpoint:
    """Test /api/fixtures/formats endpoint"""

    def test_get_formats_returns_structure(self):
        """GET /fixtures/formats should return formats and total count"""
        response = client.get("/api/fixtures/formats")
        assert response.status_code == 200
        data = response.json()
        assert "formats" in data
        assert "total" in data
        assert isinstance(data["formats"], list)

    def test_formats_have_required_fields(self):
        """Each format should have key, label, count, and profile"""
        response = client.get("/api/fixtures/formats")
        data = response.json()
        for fmt in data["formats"]:
            assert "key" in fmt
            assert "label" in fmt
            assert "count" in fmt
            assert "profile" in fmt


class TestFixtureDetailEndpoint:
    """Test /api/fixtures/{fixture_id} endpoint"""

    def test_get_fixture_by_id(self):
        """GET /fixtures/f-001 should return a single fixture"""
        response = client.get("/api/fixtures/f-001")
        assert response.status_code == 200
        fixture = response.json()
        assert fixture["id"] == "f-001"
        assert "competition" in fixture
        assert "format" in fixture
        assert "teams" in fixture

    def test_get_invalid_fixture_id(self):
        """GET /fixtures/invalid-id should return 404"""
        response = client.get("/api/fixtures/invalid-id-xyz")
        assert response.status_code == 404


class TestPredictionsEndpoint:
    """Test /api/fixtures/{fixture_id}/predictions endpoint"""

    def test_get_predictions_returns_markets(self):
        """GET /fixtures/f-001/predictions should return fixture + markets + strategy"""
        response = client.get("/api/fixtures/f-001/predictions")
        assert response.status_code == 200
        data = response.json()
        assert "fixture" in data
        assert "markets" in data
        assert "strategy" in data
        assert "notice" in data
        assert isinstance(data["markets"], list)

    def test_predictions_markets_have_structure(self):
        """Each market should have required fields"""
        response = client.get("/api/fixtures/f-001/predictions")
        data = response.json()
        for market in data["markets"]:
            assert "key" in market
            assert "label" in market
            assert "group" in market
            assert "selections" in market
            assert isinstance(market["selections"], list)

    def test_predictions_selections_valid(self):
        """Each selection should have key, name, price, probability"""
        response = client.get("/api/fixtures/f-001/predictions")
        data = response.json()
        for market in data["markets"]:
            for selection in market["selections"]:
                assert "key" in selection
                assert "name" in selection
                assert "price" in selection
                assert "probability" in selection
                assert isinstance(selection["price"], (int, float))
                assert isinstance(selection["probability"], (int, float))

import pytest

from app.core.config import cors_origins, get_settings


def test_cors_origins_parses_comma_separated_values(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("MONGO_URL", "mongodb://localhost:27017")
    monkeypatch.setenv("DB_NAME", "cricedge")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000, https://example.com")

    assert cors_origins() == ["http://localhost:3000", "https://example.com"]


def test_required_database_configuration(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.delenv("MONGO_URL", raising=False)
    monkeypatch.setenv("DB_NAME", "cricedge")

    with pytest.raises(RuntimeError, match="MONGO_URL"):
        get_settings()

    get_settings.cache_clear()

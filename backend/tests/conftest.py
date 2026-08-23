# pytest configuration for backend tests

import os
import sys

import pytest

# Configure required environment before test modules import the FastAPI app.
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "cricedge_test")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
os.environ.setdefault("ENVIRONMENT", "test")

# Add backend directory to path (conftest.py lives in backend/tests).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def mock_db():
    """Mock MongoDB connection for isolated unit tests."""
    from unittest.mock import MagicMock
    return MagicMock()


@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """Keep required test configuration deterministic."""
    monkeypatch.setenv("MONGO_URL", "mongodb://localhost:27017")
    monkeypatch.setenv("DB_NAME", "cricedge_test")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000")
    monkeypatch.setenv("ENVIRONMENT", "test")

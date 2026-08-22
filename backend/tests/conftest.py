# pytest configuration for backend tests

import pytest
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="session")
def mock_db():
    """Mock MongoDB connection for testing"""
    from unittest.mock import MagicMock
    return MagicMock()


@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """Mock environment variables for all tests"""
    monkeypatch.setenv("MONGO_URL", "mongodb://localhost:27017")
    monkeypatch.setenv("DB_NAME", "cricedge_test")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000")

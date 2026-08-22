from functools import lru_cache
from pathlib import Path
import os

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


@lru_cache(maxsize=1)
def get_settings() -> dict[str, str]:
    """Return application settings from environment variables.

    Keeping environment access in one module makes configuration explicit and
    gives the rest of the backend a single dependency boundary.
    """
    return {
        "mongo_url": _required("MONGO_URL"),
        "db_name": _required("DB_NAME"),
        "odds_api_key": os.getenv("ODDS_API_KEY", ""),
        "cors_origins": os.getenv("CORS_ORIGINS", "http://localhost:3000"),
        "environment": os.getenv("ENVIRONMENT", "development"),
    }


def cors_origins() -> list[str]:
    """Parse the comma-separated CORS_ORIGINS environment variable."""
    return [origin.strip() for origin in get_settings()["cors_origins"].split(",") if origin.strip()]

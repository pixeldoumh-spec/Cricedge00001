from functools import lru_cache
from pathlib import Path
import os

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")


class Settings:
    """Validated runtime configuration loaded from environment variables."""

    def __init__(self) -> None:
        self.mongo_url = self._required("MONGO_URL")
        self.db_name = self._required("DB_NAME")
        self.odds_api_key = os.getenv("ODDS_API_KEY", "")
        self.cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000")
        self.environment = os.getenv("ENVIRONMENT", "development").lower()

        if self.environment not in {"development", "test", "staging", "production"}:
            raise RuntimeError("ENVIRONMENT must be development, test, staging, or production")
        if self.environment == "production" and self.cors_origins.strip() == "*":
            raise RuntimeError("Wildcard CORS is not allowed in production")

    @staticmethod
    def _required(name: str) -> str:
        value = os.getenv(name)
        if not value:
            raise RuntimeError(f"Missing required environment variable: {name}")
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


def cors_origins() -> list[str]:
    """Parse the comma-separated CORS_ORIGINS environment variable."""
    return [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]

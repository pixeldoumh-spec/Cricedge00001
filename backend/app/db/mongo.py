from pymongo import MongoClient

from app.core.config import settings


MONGO_SERVER_SELECTION_TIMEOUT_MS = 3000

mongo = MongoClient(
    settings.mongo_url,
    serverSelectionTimeoutMS=MONGO_SERVER_SELECTION_TIMEOUT_MS,
)
db = mongo[settings.db_name]


def get_mongo_client() -> MongoClient:
    """Return the shared MongoDB client used by the application."""
    return mongo


def get_database():
    """Return the configured CricEdge MongoDB database."""
    return db

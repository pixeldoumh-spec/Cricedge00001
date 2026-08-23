from pymongo import MongoClient

from app.core.config import settings


MONGO_SERVER_SELECTION_TIMEOUT_MS = 3000
MONGO_CONNECT_TIMEOUT_MS = 5000
MONGO_SOCKET_TIMEOUT_MS = 10000

mongo = MongoClient(
    settings.mongo_url,
    maxPoolSize=50,
    minPoolSize=5,
    serverSelectionTimeoutMS=MONGO_SERVER_SELECTION_TIMEOUT_MS,
    connectTimeoutMS=MONGO_CONNECT_TIMEOUT_MS,
    socketTimeoutMS=MONGO_SOCKET_TIMEOUT_MS,
    retryWrites=True,
)
db = mongo[settings.db_name]


def get_mongo_client() -> MongoClient:
    """Return the shared pooled MongoDB client used by the application."""
    return mongo


def get_database():
    """Return the configured CricEdge MongoDB database."""
    return db

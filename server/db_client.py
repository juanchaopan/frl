import os

from pymongo import MongoClient
from pymongo.collection import Collection

_client: MongoClient | None = None


def _get_client() -> MongoClient:
    global _client
    if _client is None:
        missing = [k for k in ("MONGO_URI", "MONGO_DB_USERNAME", "MONGO_DB_PASSWORD")
                   if not os.environ.get(k)]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

        _client = MongoClient(
            os.environ["MONGO_URI"],
            username=os.environ["MONGO_DB_USERNAME"],
            password=os.environ["MONGO_DB_PASSWORD"],
            authSource=os.environ.get("MONGO_AUTH_SOURCE", os.environ.get("MONGO_DB", "admin")),
        )
    return _client


def get_conversations() -> Collection:
    db_name = os.environ.get("MONGO_DB")
    if not db_name:
        raise ValueError("Missing required environment variable: MONGO_DB")
    return _get_client()[db_name]["conversations"]

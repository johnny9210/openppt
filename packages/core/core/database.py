"""
MongoDB connection - Singleton async client (motor).
Pattern from aidx/ai_apis.
"""

import os
from datetime import timezone

from bson.codec_options import CodecOptions
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_USER = os.getenv("MONGO_USER", "pptgen")
MONGO_PASS = os.getenv("MONGO_PASS", "pptgen")
MONGO_HOST = os.getenv("MONGO_HOST", "mongo")
MONGO_PORT = os.getenv("MONGO_PORT", "27017")
MONGO_DB = os.getenv("MONGO_DB", "ppt_codegen")

MONGO_URI = f"mongodb://{MONGO_USER}:{MONGO_PASS}@{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB}?authSource=admin"

_client: AsyncIOMotorClient | None = None
_codec_options = CodecOptions(tz_aware=True, tzinfo=timezone.utc)


def get_mongo_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(MONGO_URI)
    return _client


def get_database(name: str | None = None):
    db_name = name or MONGO_DB
    return get_mongo_client().get_database(db_name, codec_options=_codec_options)


def get_sessions_collection():
    return get_database()["sessions"]

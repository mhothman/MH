"""
MongoDB connection and monitored access layer (single-file, production-ready)
"""

from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorDatabase,
    AsyncIOMotorCollection,
)
from typing import Optional, Dict, List
import logging
import time

from .config import settings

logger = logging.getLogger(__name__)

# ============================================================
# Optional monitoring hook (loaded once, safe)
# ============================================================

try:
    from .db_monitor import record_query
except ImportError:
    record_query = None


def _record(operation: str, collection: str, duration_ms: float, meta: Dict | None = None):
    """Safely record query metrics if monitoring is enabled."""
    if record_query:
        try:
            record_query(operation, collection, duration_ms, meta)
        except Exception:
            logger.exception("DB monitoring failed")


# ============================================================
# Mongo client & database (lazy initialization)
# ============================================================

_client: Optional[AsyncIOMotorClient] = None
_db: Optional["MonitoredDatabase"] = None


def get_client() -> AsyncIOMotorClient:
    global _client

    if _client is None:
        _client = AsyncIOMotorClient(
            settings.MONGO_URL,
            maxPoolSize=50,
            minPoolSize=5,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
        )
        logger.info("MongoDB client initialized")

    return _client


def get_database() -> "MonitoredDatabase":
    global _db

    if _db is None:
        client = get_client()
        raw_db = client[settings.DB_NAME]
        _db = MonitoredDatabase(raw_db)
        logger.info("Using database '%s' with monitoring", settings.DB_NAME)

    return _db


async def close_connection():
    """Gracefully close MongoDB connection."""
    global _client, _db

    if _client:
        _client.close()
        _client = None
        _db = None
        logger.info("MongoDB connection closed")


# ============================================================
# Monitored Collection
# ============================================================

class MonitoredCollection:
    """AsyncIOMotorCollection wrapper with performance monitoring."""

    def __init__(self, collection: AsyncIOMotorCollection):
        self._collection = collection
        self._name = collection.name

    async def find_one(self, filter: Dict | None = None, projection: Dict | None = None, **kwargs):
        start = time.perf_counter()
        if projection is not None:
            kwargs['projection'] = projection
        result = await self._collection.find_one(filter, **kwargs)
        _record("find_one", self._name, (time.perf_counter() - start) * 1000, filter)
        return result

    def find(self, filter: Dict | None = None, projection: Dict | None = None, **kwargs):
        if projection is not None:
            kwargs['projection'] = projection
        return MonitoredCursor(
            self._collection.find(filter or {}, **kwargs),
            self._name,
            "find",
            filter,
        )

    async def count_documents(self, filter: Dict | None = None, **kwargs):
        start = time.perf_counter()
        result = await self._collection.count_documents(filter or {}, **kwargs)
        _record(
            "count_documents",
            self._name,
            (time.perf_counter() - start) * 1000,
            filter,
        )
        return result

    async def insert_one(self, document: Dict, **kwargs):
        start = time.perf_counter()
        result = await self._collection.insert_one(document, **kwargs)
        _record("insert_one", self._name, (time.perf_counter() - start) * 1000)
        return result

    async def insert_many(self, documents: List[Dict], **kwargs):
        start = time.perf_counter()
        result = await self._collection.insert_many(documents, **kwargs)
        _record(
            "insert_many",
            self._name,
            (time.perf_counter() - start) * 1000,
            {"count": len(documents)},
        )
        return result

    async def update_one(self, filter: Dict, update: Dict, **kwargs):
        start = time.perf_counter()
        result = await self._collection.update_one(filter, update, **kwargs)
        _record("update_one", self._name, (time.perf_counter() - start) * 1000, filter)
        return result

    async def update_many(self, filter: Dict, update: Dict, **kwargs):
        start = time.perf_counter()
        result = await self._collection.update_many(filter, update, **kwargs)
        _record("update_many", self._name, (time.perf_counter() - start) * 1000, filter)
        return result

    async def delete_one(self, filter: Dict, **kwargs):
        start = time.perf_counter()
        result = await self._collection.delete_one(filter, **kwargs)
        _record("delete_one", self._name, (time.perf_counter() - start) * 1000, filter)
        return result

    async def delete_many(self, filter: Dict, **kwargs):
        start = time.perf_counter()
        result = await self._collection.delete_many(filter, **kwargs)
        _record("delete_many", self._name, (time.perf_counter() - start) * 1000, filter)
        return result

    def aggregate(self, pipeline: List[Dict], **kwargs):
        return MonitoredCursor(
            self._collection.aggregate(pipeline, **kwargs),
            self._name,
            "aggregate",
            {"stages": len(pipeline)},
        )

    async def find_one_and_update(self, filter: Dict, update: Dict, **kwargs):
        start = time.perf_counter()
        result = await self._collection.find_one_and_update(filter, update, **kwargs)
        _record("find_one_and_update", self._name, (time.perf_counter() - start) * 1000, filter)
        return result

    async def find_one_and_delete(self, filter: Dict, **kwargs):
        start = time.perf_counter()
        result = await self._collection.find_one_and_delete(filter, **kwargs)
        _record("find_one_and_delete", self._name, (time.perf_counter() - start) * 1000, filter)
        return result

    async def create_index(self, *args, **kwargs):
        return await self._collection.create_index(*args, **kwargs)

    async def index_information(self, *args, **kwargs):
        return await self._collection.index_information(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._collection, name)


# ============================================================
# Monitored Cursor
# ============================================================

class MonitoredCursor:
    """Cursor wrapper that records execution time when consumed."""

    def __init__(self, cursor, collection: str, operation: str, meta: Dict | None):
        self._cursor = cursor
        self._collection = collection
        self._operation = operation
        self._meta = meta
        self._start = time.perf_counter()

    async def to_list(self, length: int | None = None):
        result = await self._cursor.to_list(length)
        _record(
            f"{self._operation}.to_list",
            self._collection,
            (time.perf_counter() - self._start) * 1000,
            self._meta,
        )
        return result

    def sort(self, *args, **kwargs):
        self._cursor = self._cursor.sort(*args, **kwargs)
        return self

    def skip(self, *args, **kwargs):
        self._cursor = self._cursor.skip(*args, **kwargs)
        return self

    def limit(self, *args, **kwargs):
        self._cursor = self._cursor.limit(*args, **kwargs)
        return self

    def __aiter__(self):
        return self._cursor.__aiter__()

    async def __anext__(self):
        return await self._cursor.__anext__()


# ============================================================
# Monitored Database
# ============================================================

class MonitoredDatabase:
    """Database wrapper providing monitored collections."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self._db = db
        self._collections: Dict[str, MonitoredCollection] = {}

    def collection(self, name: str) -> MonitoredCollection:
        if name not in self._collections:
            self._collections[name] = MonitoredCollection(self._db[name])
        return self._collections[name]

    def __getitem__(self, name: str) -> MonitoredCollection:
        return self.collection(name)

    def __getattr__(self, name: str):
        if name.startswith("_"):
            return object.__getattribute__(self, name)
        return self.collection(name)

    async def command(self, *args, **kwargs):
        return await self._db.command(*args, **kwargs)

    @property
    def name(self) -> str:
        return self._db.name


# Convenience alias
db = get_database

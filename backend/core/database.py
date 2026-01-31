"""Database connection and management with performance monitoring"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from typing import Optional, Any, Dict, List
import logging
import time
from functools import wraps

from .config import settings

logger = logging.getLogger(__name__)

# Global database client and instance
_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


def get_client() -> AsyncIOMotorClient:
    """Get MongoDB client (lazy initialization)"""
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.MONGO_URL)
        logger.info(f"Connected to MongoDB: {settings.MONGO_URL}")
    return _client


class MonitoredCollection:
    """Wrapper around AsyncIOMotorCollection that monitors query performance"""
    
    def __init__(self, collection: AsyncIOMotorCollection):
        self._collection = collection
        self._name = collection.name
    
    async def _track_query(self, operation: str, query_filter: Optional[Dict] = None):
        """Record query execution time"""
        try:
            from .db_monitor import record_query
            return record_query
        except ImportError:
            return None
    
    async def find_one(self, filter: Dict = None, *args, **kwargs):
        start = time.perf_counter()
        result = await self._collection.find_one(filter, *args, **kwargs)
        duration_ms = (time.perf_counter() - start) * 1000
        try:
            from .db_monitor import record_query
            record_query("find_one", self._name, duration_ms, filter)
        except Exception:
            pass
        return result
    
    def find(self, filter: Dict = None, *args, **kwargs):
        """Return a monitored cursor"""
        return MonitoredCursor(self._collection.find(filter, *args, **kwargs), self._name, "find", filter)
    
    async def count_documents(self, filter: Dict = None, *args, **kwargs):
        start = time.perf_counter()
        result = await self._collection.count_documents(filter or {}, *args, **kwargs)
        duration_ms = (time.perf_counter() - start) * 1000
        try:
            from .db_monitor import record_query
            record_query("count_documents", self._name, duration_ms, filter)
        except Exception:
            pass
        return result
    
    async def insert_one(self, document: Dict, *args, **kwargs):
        start = time.perf_counter()
        result = await self._collection.insert_one(document, *args, **kwargs)
        duration_ms = (time.perf_counter() - start) * 1000
        try:
            from .db_monitor import record_query
            record_query("insert_one", self._name, duration_ms)
        except Exception:
            pass
        return result
    
    async def insert_many(self, documents: List[Dict], *args, **kwargs):
        start = time.perf_counter()
        result = await self._collection.insert_many(documents, *args, **kwargs)
        duration_ms = (time.perf_counter() - start) * 1000
        try:
            from .db_monitor import record_query
            record_query("insert_many", self._name, duration_ms, {"count": len(documents)})
        except Exception:
            pass
        return result
    
    async def update_one(self, filter: Dict, update: Dict, *args, **kwargs):
        start = time.perf_counter()
        result = await self._collection.update_one(filter, update, *args, **kwargs)
        duration_ms = (time.perf_counter() - start) * 1000
        try:
            from .db_monitor import record_query
            record_query("update_one", self._name, duration_ms, filter)
        except Exception:
            pass
        return result
    
    async def update_many(self, filter: Dict, update: Dict, *args, **kwargs):
        start = time.perf_counter()
        result = await self._collection.update_many(filter, update, *args, **kwargs)
        duration_ms = (time.perf_counter() - start) * 1000
        try:
            from .db_monitor import record_query
            record_query("update_many", self._name, duration_ms, filter)
        except Exception:
            pass
        return result
    
    async def delete_one(self, filter: Dict, *args, **kwargs):
        start = time.perf_counter()
        result = await self._collection.delete_one(filter, *args, **kwargs)
        duration_ms = (time.perf_counter() - start) * 1000
        try:
            from .db_monitor import record_query
            record_query("delete_one", self._name, duration_ms, filter)
        except Exception:
            pass
        return result
    
    async def delete_many(self, filter: Dict, *args, **kwargs):
        start = time.perf_counter()
        result = await self._collection.delete_many(filter, *args, **kwargs)
        duration_ms = (time.perf_counter() - start) * 1000
        try:
            from .db_monitor import record_query
            record_query("delete_many", self._name, duration_ms, filter)
        except Exception:
            pass
        return result
    
    def aggregate(self, pipeline: List[Dict], *args, **kwargs):
        """Return a monitored cursor for aggregation"""
        return MonitoredCursor(self._collection.aggregate(pipeline, *args, **kwargs), self._name, "aggregate", {"pipeline_stages": len(pipeline)})
    
    async def find_one_and_update(self, filter: Dict, update: Dict, *args, **kwargs):
        start = time.perf_counter()
        result = await self._collection.find_one_and_update(filter, update, *args, **kwargs)
        duration_ms = (time.perf_counter() - start) * 1000
        try:
            from .db_monitor import record_query
            record_query("find_one_and_update", self._name, duration_ms, filter)
        except Exception:
            pass
        return result
    
    async def find_one_and_delete(self, filter: Dict, *args, **kwargs):
        start = time.perf_counter()
        result = await self._collection.find_one_and_delete(filter, *args, **kwargs)
        duration_ms = (time.perf_counter() - start) * 1000
        try:
            from .db_monitor import record_query
            record_query("find_one_and_delete", self._name, duration_ms, filter)
        except Exception:
            pass
        return result
    
    async def create_index(self, *args, **kwargs):
        return await self._collection.create_index(*args, **kwargs)
    
    async def index_information(self, *args, **kwargs):
        return await self._collection.index_information(*args, **kwargs)
    
    # Delegate other methods to the underlying collection
    def __getattr__(self, name):
        return getattr(self._collection, name)


class MonitoredCursor:
    """Wrapper around cursor that monitors query performance"""
    
    def __init__(self, cursor, collection_name: str, operation: str, query_filter: Optional[Dict] = None):
        self._cursor = cursor
        self._collection_name = collection_name
        self._operation = operation
        self._query_filter = query_filter
        self._start_time = time.perf_counter()
    
    async def to_list(self, length: Optional[int] = None):
        result = await self._cursor.to_list(length)
        duration_ms = (time.perf_counter() - self._start_time) * 1000
        try:
            from .db_monitor import record_query
            record_query(f"{self._operation}.to_list", self._collection_name, duration_ms, self._query_filter)
        except Exception:
            pass
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


class MonitoredDatabase:
    """Wrapper around AsyncIOMotorDatabase that provides monitored collections"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self._db = db
        self._monitored_collections: Dict[str, MonitoredCollection] = {}
    
    def __getitem__(self, name: str) -> MonitoredCollection:
        if name not in self._monitored_collections:
            self._monitored_collections[name] = MonitoredCollection(self._db[name])
        return self._monitored_collections[name]
    
    def __getattr__(self, name: str):
        # For collection access via attribute (db.users, db.tasks, etc.)
        if name.startswith('_'):
            return object.__getattribute__(self, name)
        return self[name]
    
    async def command(self, *args, **kwargs):
        return await self._db.command(*args, **kwargs)
    
    @property
    def name(self):
        return self._db.name


def get_database() -> MonitoredDatabase:
    """Get monitored database instance (lazy initialization)"""
    global _db
    if _db is None:
        client = get_client()
        raw_db = client[settings.DB_NAME]
        _db = MonitoredDatabase(raw_db)
        logger.info(f"Using database: {settings.DB_NAME} (with monitoring)")
    return _db


# Convenience alias
db = get_database()


async def close_connection():
    """Close database connection"""
    global _client, _db
    if _client is not None:
        _client.close()
        _client = None
        _db = None
        logger.info("MongoDB connection closed")

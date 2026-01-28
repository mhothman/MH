"""
Simple in-memory cache for frequently accessed, rarely changing data.
Uses TTL (time-to-live) to automatically expire cached values.
"""
import time
from typing import Any, Optional, Callable
from functools import wraps
import asyncio

class TTLCache:
    """Thread-safe TTL cache for async functions"""
    
    def __init__(self):
        self._cache = {}
        self._timestamps = {}
    
    def get(self, key: str, ttl_seconds: int = 300) -> Optional[Any]:
        """Get value if exists and not expired"""
        if key not in self._cache:
            return None
        
        if time.time() - self._timestamps.get(key, 0) > ttl_seconds:
            # Expired
            del self._cache[key]
            del self._timestamps[key]
            return None
        
        return self._cache[key]
    
    def set(self, key: str, value: Any) -> None:
        """Set value with current timestamp"""
        self._cache[key] = value
        self._timestamps[key] = time.time()
    
    def invalidate(self, key: str) -> None:
        """Remove a specific key"""
        self._cache.pop(key, None)
        self._timestamps.pop(key, None)
    
    def invalidate_pattern(self, pattern: str) -> None:
        """Remove all keys matching pattern"""
        keys_to_remove = [k for k in self._cache.keys() if pattern in k]
        for key in keys_to_remove:
            self.invalidate(key)
    
    def clear(self) -> None:
        """Clear all cached values"""
        self._cache.clear()
        self._timestamps.clear()

# Global cache instance
cache = TTLCache()

def cached(ttl_seconds: int = 300, key_prefix: str = ""):
    """
    Decorator for caching async function results.
    
    Usage:
        @cached(ttl_seconds=300, key_prefix="user_perms")
        async def get_user_permissions(user_id: str, org_id: str):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key from function name and arguments
            cache_key = f"{key_prefix}:{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            
            # Try to get from cache
            cached_value = cache.get(cache_key, ttl_seconds)
            if cached_value is not None:
                return cached_value
            
            # Call function and cache result
            result = await func(*args, **kwargs)
            cache.set(cache_key, result)
            return result
        
        return wrapper
    return decorator

# Cache keys for common data
class CacheKeys:
    PERMISSIONS = "permissions"
    ROLES = "roles"
    PRESET_THEMES = "themes"
    ORG_MEMBERS = "org_members"
    USER_ORGS = "user_orgs"

"""
Redis Cache Service
Provides caching functionality for API responses and expensive computations
"""

import redis
import json
import logging
from typing import Optional, Any, Callable
from functools import wraps
import hashlib
from datetime import timedelta

from core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Redis-based caching service"""

    def __init__(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            logger.info("Redis cache service initialized successfully")
            self.enabled = True
        except Exception as e:
            logger.warning(f"Redis connection failed: {str(e)}. Caching disabled.")
            self.redis_client = None
            self.enabled = False

    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """
        Generate a unique cache key

        Args:
            prefix: Key prefix (e.g., "query", "rag", "agent")
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Unique cache key
        """
        # Create a string representation of arguments
        key_data = f"{prefix}:{str(args)}:{str(sorted(kwargs.items()))}"

        # Hash for consistent key length
        key_hash = hashlib.md5(key_data.encode()).hexdigest()

        return f"aicfo:{prefix}:{key_hash}"

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        if not self.enabled or not self.redis_client:
            return None

        try:
            value = self.redis_client.get(key)
            if value:
                logger.debug(f"Cache HIT: {key}")
                return json.loads(value)
            else:
                logger.debug(f"Cache MISS: {key}")
                return None
        except Exception as e:
            logger.error(f"Cache get error: {str(e)}")
            return None

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (default: settings.CACHE_TTL)

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.redis_client:
            return False

        try:
            ttl = ttl or settings.CACHE_TTL
            serialized = json.dumps(value, default=str)

            if ttl:
                self.redis_client.setex(key, ttl, serialized)
            else:
                self.redis_client.set(key, serialized)

            logger.debug(f"Cache SET: {key} (ttl={ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Cache set error: {str(e)}")
            return False

    def delete(self, key: str) -> bool:
        """
        Delete value from cache

        Args:
            key: Cache key

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.redis_client:
            return False

        try:
            self.redis_client.delete(key)
            logger.debug(f"Cache DELETE: {key}")
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {str(e)}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern

        Args:
            pattern: Key pattern (e.g., "aicfo:query:*")

        Returns:
            Number of keys deleted
        """
        if not self.enabled or not self.redis_client:
            return 0

        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                deleted = self.redis_client.delete(*keys)
                logger.info(f"Cache DELETE pattern '{pattern}': {deleted} keys")
                return deleted
            return 0
        except Exception as e:
            logger.error(f"Cache delete pattern error: {str(e)}")
            return 0

    def flush_all(self) -> bool:
        """
        Flush entire cache

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.redis_client:
            return False

        try:
            self.redis_client.flushdb()
            logger.warning("Cache FLUSHED: All keys deleted")
            return True
        except Exception as e:
            logger.error(f"Cache flush error: {str(e)}")
            return False

    def get_stats(self) -> dict:
        """
        Get cache statistics

        Returns:
            Dictionary with cache stats
        """
        if not self.enabled or not self.redis_client:
            return {
                "enabled": False,
                "connected": False
            }

        try:
            info = self.redis_client.info()
            return {
                "enabled": True,
                "connected": True,
                "used_memory": info.get("used_memory_human"),
                "total_keys": self.redis_client.dbsize(),
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(
                    info.get("keyspace_hits", 0),
                    info.get("keyspace_misses", 0)
                )
            }
        except Exception as e:
            logger.error(f"Cache stats error: {str(e)}")
            return {
                "enabled": True,
                "connected": False,
                "error": str(e)
            }

    def _calculate_hit_rate(self, hits: int, misses: int) -> float:
        """Calculate cache hit rate percentage"""
        total = hits + misses
        if total == 0:
            return 0.0
        return round((hits / total) * 100, 2)


# Global cache service instance
cache_service = CacheService()


# ============================================================================
# DECORATORS
# ============================================================================

def cached(
    prefix: str,
    ttl: Optional[int] = None,
    key_builder: Optional[Callable] = None
):
    """
    Decorator to cache function results

    Args:
        prefix: Cache key prefix
        ttl: Time to live in seconds
        key_builder: Optional custom key builder function

    Example:
        @cached(prefix="agent_query", ttl=3600)
        def query_agent(query: str, agent_id: str):
            # Expensive operation
            return result
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                cache_key = cache_service._generate_key(prefix, *args, **kwargs)

            # Try to get from cache
            cached_result = cache_service.get(cache_key)
            if cached_result is not None:
                logger.info(f"Returning cached result for {func.__name__}")
                return cached_result

            # Execute function
            result = func(*args, **kwargs)

            # Cache result
            cache_service.set(cache_key, result, ttl)

            return result

        return wrapper
    return decorator


def cache_invalidate(prefix: str):
    """
    Decorator to invalidate cache after function execution

    Args:
        prefix: Cache key prefix to invalidate

    Example:
        @cache_invalidate(prefix="agent_query")
        def update_agent(agent_id: str):
            # Update operation
            return result
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Execute function
            result = func(*args, **kwargs)

            # Invalidate cache
            pattern = f"aicfo:{prefix}:*"
            deleted = cache_service.delete_pattern(pattern)
            logger.info(f"Invalidated {deleted} cache entries with prefix '{prefix}'")

            return result

        return wrapper
    return decorator


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

"""
Example 1: Cache agent query results

from services.cache_service import cached

@cached(prefix="agent_query", ttl=3600)
def process_agent_query(query: str, agent_id: str, model: str):
    # Expensive RAG + LLM call
    result = agent.process(query)
    return result

# First call: Executes and caches
result1 = process_agent_query("What is my tax obligation?", "TaxAgent", "gpt-4")

# Second call: Returns cached result (instant)
result2 = process_agent_query("What is my tax obligation?", "TaxAgent", "gpt-4")


Example 2: Invalidate cache when data changes

from services.cache_service import cache_invalidate

@cache_invalidate(prefix="agent_query")
def update_agent_config(agent_id: str, config: dict):
    # Update agent configuration
    db.update(agent_id, config)
    # Cache automatically invalidated after this


Example 3: Manual cache operations

from services.cache_service import cache_service

# Set value
cache_service.set("custom:key", {"data": "value"}, ttl=1800)

# Get value
value = cache_service.get("custom:key")

# Delete specific key
cache_service.delete("custom:key")

# Delete by pattern
cache_service.delete_pattern("aicfo:agent:*")

# Get stats
stats = cache_service.get_stats()
print(f"Hit rate: {stats['hit_rate']}%")
"""

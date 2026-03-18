"""
Redis cache adapter implementation.
This module implements the CachePort interface using Redis.
"""

import logging
import pickle
from typing import Any, Protocol

import redis.asyncio as redis

from application.ports.cache import CachePort
from infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


class CacheException(Exception):
    """Custom exception for cache errors."""

    pass


class _RedisIntrospectionContext(Protocol):
    redis_client: redis.Redis | None

    async def connect(self) -> None: ...


class _RedisIntrospectionMixin:
    async def get_stats(self: _RedisIntrospectionContext) -> dict[str, Any]:
        """Get cache statistics."""
        if not self.redis_client:
            await self.connect()

        try:
            if self.redis_client:
                info: dict[str, Any] = dict(await self.redis_client.info())
                hits: int = info.get("keyspace_hits", 0)
                misses: int = info.get("keyspace_misses", 0)
                total: int = hits + misses
                hit_rate_percentage: float = round((hits / total) * 100, 2) if total > 0 else 0.0
                return {
                    "connected_clients": info.get("connected_clients", 0),
                    "used_memory": info.get("used_memory", 0),
                    "used_memory_human": info.get("used_memory_human", "0B"),
                    "used_memory_peak": info.get("used_memory_peak", 0),
                    "used_memory_peak_human": info.get("used_memory_peak_human", "0B"),
                    "total_connections_received": info.get("total_connections_received", 0),
                    "total_commands_processed": info.get("total_commands_processed", 0),
                    "keyspace_hits": hits,
                    "keyspace_misses": misses,
                    "expired_keys": info.get("expired_keys", 0),
                    "evicted_keys": info.get("evicted_keys", 0),
                    "uptime_in_seconds": info.get("uptime_in_seconds", 0),
                    "redis_version": info.get("redis_version", "unknown"),
                    "hit_rate_percentage": hit_rate_percentage,
                }
            return {}
        except Exception as e:
            logger.error(f"Error getting cache statistics: {e}")
            return {"error": str(e)}

    async def count_keys(self: _RedisIntrospectionContext) -> int | None:
        """Return total amount of keys in the selected Redis database."""
        if not self.redis_client:
            await self.connect()

        try:
            if not self.redis_client:
                return None
            return int(await self.redis_client.dbsize())
        except Exception as e:
            logger.error(f"Error counting keys in cache: {e}")
            return None

    async def list_keys(self: _RedisIntrospectionContext, pattern: str = "*", limit: int = 100) -> list[str]:
        """Return up to `limit` keys matching `pattern` using SCAN to avoid blocking."""
        if not self.redis_client:
            await self.connect()

        keys: list[str] = []
        try:
            if not self.redis_client:
                return keys

            async for key in self.redis_client.scan_iter(match=pattern, count=min(limit, 1000)):
                try:
                    normalized_key = key.decode("utf-8") if isinstance(key, (bytes, bytearray)) else str(key)
                except Exception:
                    normalized_key = str(key)
                keys.append(normalized_key)
                if len(keys) >= limit:
                    break
            return keys
        except Exception as e:
            logger.error(f"Error listing keys with pattern {pattern}: {e}")
            return keys


class RedisAdapter(_RedisIntrospectionMixin, CachePort):
    """Implementation of the CachePort interface using Redis."""

    def __init__(self) -> None:
        self.redis_client: redis.Redis | None = None
        self.connection_pool: redis.ConnectionPool | None = None

    async def connect(self) -> None:
        """Establish connection to Redis with connection pool."""
        try:
            self.connection_pool = redis.ConnectionPool.from_url(
                settings.REDIS_URL,
                max_connections=settings.DB_POOL_SIZE,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={},
                password=settings.REDIS_PASSWORD,
                socket_timeout=settings.REDIS_TIMEOUT,
            )

            self.redis_client = redis.Redis(
                connection_pool=self.connection_pool,
                decode_responses=False,  # To use pickle
            )

            # Verify connection
            if self.redis_client:
                await self.redis_client.ping()
            # Use debug to avoid noisy logs on frequent health checks
            logger.debug("Redis connection established successfully")

        except Exception as e:
            logger.error(f"Error connecting to Redis: {e}")
            raise CacheException(f"Redis connection error: {e}")

    async def disconnect(self) -> None:
        """Close connection to Redis."""
        if self.redis_client:
            # Use aclose if available, otherwise fall back to close
            if hasattr(self.redis_client, "aclose"):
                await self.redis_client.aclose()  # type: ignore
            elif hasattr(self.redis_client, "close"):
                await self.redis_client.close()  # type: ignore
        if self.connection_pool:
            await self.connection_pool.disconnect()

    async def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the cache by key."""
        if not self.redis_client:
            await self.connect()

        try:
            if self.redis_client:
                value: bytes | None = await self.redis_client.get(key)
            else:
                value = None

            if value is None:
                logger.debug(f"Cache miss: {key}")
                return default

            # Deserialize
            return pickle.loads(value)

        except Exception as e:
            logger.error(f"Error retrieving from cache {key}: {e}")
            return default

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Set a value in the cache with an optional time-to-live in seconds."""
        if not self.redis_client:
            await self.connect()

        try:
            # Serialize value
            serialized_value: bytes = pickle.dumps(value)

            # Use default TTL if not specified
            if ttl is None:
                ttl = settings.CACHE_DEFAULT_TTL

            # Store in Redis
            if self.redis_client:
                result: bool | None = await self.redis_client.setex(key, ttl, serialized_value)
            else:
                result = False

            logger.debug(f"Value stored in cache: {key} (TTL: {ttl}s)")
            return bool(result)

        except Exception as e:
            logger.error(f"Error storing in cache {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete a value from the cache by key."""
        if not self.redis_client:
            await self.connect()

        try:
            if self.redis_client:
                result: int = await self.redis_client.delete(key)
            else:
                result = 0
            logger.debug(f"Key deleted from cache: {key}")
            return bool(result)
        except Exception as e:
            logger.error(f"Error deleting from cache {key}: {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """Delete values matching a pattern. Returns number of deleted keys."""
        if not self.redis_client:
            await self.connect()

        try:
            if not self.redis_client:
                return 0

            keys: list[str] = [key async for key in self.redis_client.scan_iter(match=pattern)]

            if not keys:
                return 0

            deleted: int = await self.redis_client.delete(*keys)
            logger.debug(f"Deleted {deleted} keys matching pattern: {pattern}")
            return deleted

        except Exception as e:
            logger.error(f"Error deleting pattern {pattern}: {e}")
            return 0

    async def exists(self, key: str) -> bool:
        """Check if a key exists in the cache."""
        if not self.redis_client:
            await self.connect()

        try:
            if self.redis_client:
                result: int = await self.redis_client.exists(key)
            else:
                result = 0
            return bool(result)
        except Exception as e:
            logger.error(f"Error checking existence in cache {key}: {e}")
            return False

    async def clear(self, pattern: str | None = None) -> int:
        """Clear the cache, optionally by pattern. Returns the number of keys deleted."""
        if not self.redis_client:
            await self.connect()

        try:
            if self.redis_client:
                if pattern:
                    keys: list[str] = await self.redis_client.keys(pattern)
                    if keys:
                        deleted: int = await self.redis_client.delete(*keys)
                        logger.info(f"Cleared {deleted} keys with pattern: {pattern}")
                        return deleted
                    return 0
                else:
                    # Clear all keys (dangerous, use with caution)
                    result: bool | None = await self.redis_client.flushdb()
                    logger.warning("Cleared entire cache")
                    return 1 if result else 0
            return 0

        except Exception as e:
            logger.error(f"Error clearing cache with pattern {pattern}: {e}")
            return 0

    async def get_many(self, keys: list[str]) -> dict[str, Any]:
        """Get multiple values from the cache by keys."""
        if not self.redis_client:
            await self.connect()

        try:
            if self.redis_client:
                values: list[bytes | None] = await self.redis_client.mget(keys)
            else:
                values = [None] * len(keys)
            result: dict[str, Any] = {}

            for key, value in zip(keys, values, strict=False):
                if value is not None:
                    try:
                        result[key] = pickle.loads(value)
                    except Exception as e:
                        logger.warning(f"Error deserializing {key}: {e}")
                        result[key] = None
                else:
                    result[key] = None

            return result

        except Exception as e:
            logger.error(f"Error retrieving multiple elements: {e}")
            return {key: None for key in keys}

    async def set_many(self, mapping: dict[str, Any], ttl: int | None = None) -> bool:
        """Set multiple values in the cache with an optional time-to-live in seconds."""
        if not self.redis_client:
            await self.connect()

        try:
            if self.redis_client:
                pipe = self.redis_client.pipeline()
            else:
                return False

            # Use default TTL if not specified
            if ttl is None:
                ttl = settings.CACHE_DEFAULT_TTL

            for key, value in mapping.items():
                serialized_value: bytes = pickle.dumps(value)
                await pipe.setex(key, ttl, serialized_value)

            results: list[Any] = await pipe.execute()
            success: bool = all(results)

            if success:
                logger.debug(f"Stored {len(mapping)} elements in cache")

            return success

        except Exception as e:
            logger.error(f"Error storing multiple elements: {e}")
            return False

    async def delete_many(self, keys: list[str]) -> int:
        """Delete multiple values from the cache by keys. Returns the number of keys deleted."""
        if not self.redis_client:
            await self.connect()

        try:
            if self.redis_client and keys:
                deleted: int = await self.redis_client.delete(*keys)
                logger.debug(f"Deleted {deleted} keys from cache")
                return deleted
            return 0

        except Exception as e:
            logger.error(f"Error deleting multiple keys: {e}")
            return 0

    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment a numeric value in the cache. Returns the new value."""
        if not self.redis_client:
            await self.connect()

        try:
            if self.redis_client:
                result: int = await self.redis_client.incrby(key, amount)
                logger.debug(f"Incremented {key} by {amount}, new value: {result}")
                return result
            return 0

        except Exception as e:
            logger.error(f"Error incrementing {key}: {e}")
            return 0

    async def decrement(self, key: str, amount: int = 1) -> int:
        """Decrement a numeric value in the cache. Returns the new value."""
        if not self.redis_client:
            await self.connect()

        try:
            if self.redis_client:
                result: int = await self.redis_client.decrby(key, amount)
                logger.debug(f"Decremented {key} by {amount}, new value: {result}")
                return result
            return 0

        except Exception as e:
            logger.error(f"Error decrementing {key}: {e}")
            return 0

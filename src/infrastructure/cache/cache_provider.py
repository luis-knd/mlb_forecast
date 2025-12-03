"""
Centralized Redis cache provider (singleton).

Provides a single RedisAdapter instance for the entire application lifecycle
to avoid reconnecting on every request and spamming logs.
"""

import logging
from typing import Optional

from src.infrastructure.cache.redis_adapter import RedisAdapter

_cache_adapter: Optional[RedisAdapter] = None
logger = logging.getLogger(__name__)


def get_cache_adapter() -> RedisAdapter:
    global _cache_adapter
    if _cache_adapter is None:
        _cache_adapter = RedisAdapter()
    return _cache_adapter


async def connect_cache() -> None:
    try:
        adapter = get_cache_adapter()
        if adapter.redis_client is None:
            await adapter.connect()
    except Exception as e:
        logger.warning(f"Skipping Redis connection at startup: {e}")


async def disconnect_cache() -> None:
    try:
        adapter = get_cache_adapter()
        if adapter.redis_client is not None:
            await adapter.disconnect()
    except Exception as e:
        logger.warning(f"Error disconnecting Redis at shutdown: {e}")

"""
System use cases for cache management, health checks, and application info.
This module implements the business logic for system-related operations.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol, cast

from sqlalchemy import text
from sqlalchemy.orm import Session

from application.ports.cache import CachePort

logger = logging.getLogger(__name__)


class CacheIntrospectionPort(Protocol):
    """Protocol for cache adapters that support diagnostics operations."""

    async def get_stats(self) -> dict[str, Any]: ...

    async def list_keys(self, pattern: str = "*", limit: int = 100) -> list[str]: ...

    async def count_keys(self) -> int | None: ...


@dataclass(frozen=True, slots=True)
class SystemRuntimeConfig:
    """Application metadata required by system use cases."""

    app_name: str
    api_version: str
    environment: str
    debug: bool
    api_prefix: str
    cache_default_ttl: int
    mlb_api_base_url: str
    mlb_api_version: str


class SystemException(Exception):
    """Custom exception for system operations."""


class GetCacheStatsUseCase:
    """Use cases for retrieving cache statistics."""

    def __init__(self, cache_adapter: CachePort):
        self.cache_adapter = cache_adapter

    async def execute(
        self,
        include_keys: bool = False,
        pattern: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Get cache statistics."""
        try:
            introspection = self._get_introspection_port()
            raw_stats = await introspection.get_stats()
            stats = self._normalize_stats(raw_stats)
            stats["total_keys"] = await self._safe_total_keys(introspection)
            if include_keys:
                await self._append_keys_stats(introspection, stats, pattern, limit)
            logger.info("Cache statistics retrieved successfully")
            return stats
        except Exception as error:
            logger.error(f"Error getting cache statistics: {error}")
            raise SystemException(f"Failed to get cache statistics: {error}")

    def _get_introspection_port(self) -> CacheIntrospectionPort:
        candidate: Any = self.cache_adapter
        supports_stats = callable(getattr(candidate, "get_stats", None))
        supports_list_keys = callable(getattr(candidate, "list_keys", None))
        supports_count_keys = callable(getattr(candidate, "count_keys", None))
        if supports_stats and supports_list_keys and supports_count_keys:
            return cast(CacheIntrospectionPort, candidate)
        raise SystemException("Cache adapter does not support cache diagnostics")

    @staticmethod
    def _normalize_stats(stats: dict[str, Any]) -> dict[str, Any]:
        normalized = {
            "connected_clients": stats.get("connected_clients", 0),
            "used_memory": stats.get("used_memory", 0),
            "used_memory_human": stats.get("used_memory_human", "0B"),
            "used_memory_peak": stats.get("used_memory_peak", 0),
            "used_memory_peak_human": stats.get("used_memory_peak_human", "0B"),
            "total_connections_received": stats.get("total_connections_received", 0),
            "total_commands_processed": stats.get("total_commands_processed", 0),
            "keyspace_hits": stats.get("keyspace_hits", 0),
            "keyspace_misses": stats.get("keyspace_misses", 0),
            "expired_keys": stats.get("expired_keys", 0),
            "evicted_keys": stats.get("evicted_keys", 0),
            "uptime_in_seconds": stats.get("uptime_in_seconds", 0),
            "redis_version": stats.get("redis_version", "unknown"),
        }
        hits = int(normalized["keyspace_hits"] or 0)
        misses = int(normalized["keyspace_misses"] or 0)
        total_requests = hits + misses
        provided_hit_rate = stats.get("hit_rate_percentage")
        if provided_hit_rate is None:
            hit_rate = (hits / total_requests * 100) if total_requests > 0 else 0
        else:
            hit_rate = float(provided_hit_rate)
        normalized["hit_rate_percentage"] = round(hit_rate, 2)
        normalized["total_requests"] = total_requests
        return normalized

    @staticmethod
    async def _safe_total_keys(cache_introspection: CacheIntrospectionPort) -> int | None:
        try:
            return await cache_introspection.count_keys()
        except Exception:
            return None

    async def _append_keys_stats(
        self,
        cache_introspection: CacheIntrospectionPort,
        stats: dict[str, Any],
        pattern: str | None,
        limit: int,
    ) -> None:
        bounded_limit = min(max(limit, 1), 10000)
        match = pattern or "*"
        keys = await cache_introspection.list_keys(match, bounded_limit)
        stats["keys_pattern"] = match
        stats["keys_returned"] = len(keys)
        stats["keys"] = keys


class ClearCacheUseCase:
    """Use cases for clearing cache entries."""

    def __init__(self, cache_adapter: CachePort):
        self.cache_adapter = cache_adapter

    async def execute(self, pattern: str | None = None) -> dict[str, Any]:
        """Clear cache entries by pattern or all entries."""
        try:
            total_deleted = 0
            if pattern:
                total_deleted = await self.cache_adapter.clear(pattern)
                message = f"Deleted {total_deleted} keys matching pattern: {pattern}"
            else:
                patterns = ["mlb:*", "teams:*", "games:*", "stats:*", "predictions:*"]
                for pattern_value in patterns:
                    total_deleted += await self.cache_adapter.clear(pattern_value)
                message = f"Cache cleared successfully: {total_deleted} keys deleted"

            logger.info(message)
            return {
                "success": True,
                "message": message,
                "deleted_keys": total_deleted,
                "pattern": pattern,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as error:
            logger.error(f"Error clearing cache: {error}")
            raise SystemException(f"Failed to clear cache: {error}")


class HealthCheckUseCase:
    """Use cases for performing system health checks."""

    def __init__(self, cache_adapter: CachePort, runtime_config: SystemRuntimeConfig):
        self.cache_adapter = cache_adapter
        self.runtime_config = runtime_config

    async def execute(self, db: Session) -> dict[str, Any]:
        """Perform a comprehensive health check."""
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": self.runtime_config.api_version,
            "database": "unknown",
            "cache": "unknown",
            "ml_model": "unknown",
        }
        try:
            self._check_database_health(db, health_status)
            await self._check_cache_health(health_status)
            health_status["ml_model"] = "not_implemented"
            return health_status
        except Exception as error:
            logger.error(f"Error during health check: {error}")
            health_status["status"] = "error"
            health_status["error"] = str(error)
            return health_status

    @staticmethod
    def _check_database_health(db: Session, health_status: dict[str, Any]) -> None:
        try:
            db.execute(text("SELECT 1"))
            health_status["database"] = "connected"
            logger.debug("Database health check: OK")
        except Exception as error:
            health_status["database"] = "disconnected"
            health_status["status"] = "unhealthy"
            logger.error(f"Database health check failed: {error}")

    async def _check_cache_health(self, health_status: dict[str, Any]) -> None:
        try:
            test_key = "health_check_test"
            await self.cache_adapter.set(test_key, "test_value", 10)
            await self.cache_adapter.delete(test_key)
            health_status["cache"] = "connected"
            logger.debug("Cache health check: OK")
        except Exception as error:
            health_status["cache"] = "disconnected"
            health_status["status"] = "unhealthy"
            logger.error(f"Cache health check failed: {error}")


class GetAppInfoUseCase:
    """Use case for retrieving application information."""

    def __init__(self, cache_adapter: CachePort, runtime_config: SystemRuntimeConfig):
        self.cache_adapter = cache_adapter
        self.runtime_config = runtime_config

    async def execute(self, db: Session) -> dict[str, Any]:
        """Get detailed application information."""
        try:
            database_connected = self._is_database_connected(db)
            cache_connected = await self._is_cache_connected()
            app_info = {
                "app_name": self.runtime_config.app_name,
                "version": self.runtime_config.api_version,
                "environment": self.runtime_config.environment,
                "debug_mode": self.runtime_config.debug,
                "api_prefix": self.runtime_config.api_prefix,
                "database_connected": database_connected,
                "cache_connected": cache_connected,
                "ml_model_ready": False,
                "features": {
                    "data_ingestion": True,
                    "caching": True,
                    "predictions": False,
                    "continuous_learning": False,
                    "rest_api": True,
                    "health_monitoring": True,
                },
                "configuration": {
                    "cache_default_ttl": self.runtime_config.cache_default_ttl,
                    "mlb_api_base_url": self.runtime_config.mlb_api_base_url,
                    "mlb_api_version": self.runtime_config.mlb_api_version,
                },
                "timestamp": datetime.now().isoformat(),
            }
            logger.info("Application info retrieved successfully")
            return app_info
        except Exception as error:
            logger.error(f"Error getting application info: {error}")
            raise SystemException(f"Failed to get application info: {error}")

    @staticmethod
    def _is_database_connected(db: Session) -> bool:
        try:
            db.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    async def _is_cache_connected(self) -> bool:
        try:
            test_key = "app_info_test"
            await self.cache_adapter.set(test_key, "test", 5)
            await self.cache_adapter.delete(test_key)
            return True
        except Exception:
            return False

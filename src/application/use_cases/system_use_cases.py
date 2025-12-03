"""
System use cases for cache management, health checks, and application info.
This module implements the business logic for system-related operations.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.application.ports.cache import CachePort
from src.infrastructure.cache.redis_adapter import RedisAdapter
from src.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


class SystemException(Exception):
    """Custom exception for system operations."""

    pass


class GetCacheStatsUseCase:
    """Use cases for retrieving cache statistics."""

    def __init__(self, cache_adapter: CachePort):
        self.cache_adapter = cache_adapter

    async def execute(
        self, include_keys: bool = False, pattern: Optional[str] = None, limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        try:
            # This use case requires Redis-specific functionality
            if not isinstance(self.cache_adapter, RedisAdapter):
                raise SystemException("Cache statistics require Redis adapter")

            # Connect if not already connected
            if not self.cache_adapter.redis_client:
                await self.cache_adapter.connect()

            if not self.cache_adapter.redis_client:
                raise SystemException("Cache adapter not available")

            # Get Redis info
            info = await self.cache_adapter.redis_client.info()

            # Extract relevant statistics
            stats = {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "used_memory_peak": info.get("used_memory_peak", 0),
                "used_memory_peak_human": info.get("used_memory_peak_human", "0B"),
                "total_connections_received": info.get("total_connections_received", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "expired_keys": info.get("expired_keys", 0),
                "evicted_keys": info.get("evicted_keys", 0),
                "uptime_in_seconds": info.get("uptime_in_seconds", 0),
                "redis_version": info.get("redis_version", "unknown"),
            }

            # Calculate hit rate
            hits = stats["keyspace_hits"]
            misses = stats["keyspace_misses"]
            total_requests = hits + misses
            hit_rate = (hits / total_requests * 100) if total_requests > 0 else 0

            stats["hit_rate_percentage"] = round(hit_rate, 2)
            stats["total_requests"] = total_requests

            # Total keys in current DB
            try:
                stats["total_keys"] = await self.cache_adapter.redis_client.dbsize()
            except Exception:
                stats["total_keys"] = None

            # Optionally include keys (sampled via SCAN)
            if include_keys:
                if limit < 1:
                    limit = 1
                if limit > 10000:
                    limit = 10000
                match = pattern or "*"
                keys = await self.cache_adapter.list_keys(match, limit)
                stats["keys_pattern"] = match
                stats["keys_returned"] = len(keys)
                stats["keys"] = keys

            logger.info("Cache statistics retrieved successfully")
            return stats

        except Exception as e:
            logger.error(f"Error getting cache statistics: {e}")
            raise SystemException(f"Failed to get cache statistics: {str(e)}")


class ClearCacheUseCase:
    """Use cases for clearing cache entries."""

    def __init__(self, cache_adapter: CachePort):
        self.cache_adapter = cache_adapter

    async def execute(self, pattern: Optional[str] = None) -> Dict[str, Any]:
        """
        Clear cache entries by pattern or all entries.

        Args:
            pattern: Optional pattern to match keys (e.g., "mlb:teams:*")

        Returns:
            Dictionary with operation result
        """
        try:
            total_deleted = 0

            if pattern:
                deleted_count = await self.cache_adapter.clear(pattern)
                message = f"Deleted {deleted_count} keys matching pattern: {pattern}"
                total_deleted = deleted_count
            else:
                # Clear all MLB-related cache entries
                patterns = ["mlb:*", "teams:*", "games:*", "stats:*", "predictions:*"]

                for p in patterns:
                    deleted = await self.cache_adapter.clear(p)
                    total_deleted += deleted

                message = f"Cache cleared successfully: {total_deleted} keys deleted"

            logger.info(message)
            return {
                "success": True,
                "message": message,
                "deleted_keys": total_deleted,
                "pattern": pattern,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            raise SystemException(f"Failed to clear cache: {str(e)}")


class HealthCheckUseCase:
    """Use cases for performing system health checks."""

    def __init__(self, cache_adapter: CachePort):
        self.cache_adapter = cache_adapter

    async def execute(self, db: Session) -> Dict[str, Any]:
        """
        Perform a comprehensive health check.

        Args:
            db: Database session

        Returns:
            Dictionary with health status
        """
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": settings.API_VERSION,
            "database": "unknown",
            "cache": "unknown",
            "ml_model": "unknown",
        }

        try:
            # Check database connection
            try:
                db.execute(text("SELECT 1"))
                health_status["database"] = "connected"
                logger.debug("Database health check: OK")
            except Exception as e:
                health_status["database"] = "disconnected"
                health_status["status"] = "unhealthy"
                logger.error(f"Database health check failed: {e}")

            # Check cache connection
            try:
                # Use a simple cache operation to test connectivity
                test_key = "health_check_test"
                await self.cache_adapter.set(test_key, "test_value", 10)
                await self.cache_adapter.delete(test_key)
                health_status["cache"] = "connected"
                logger.debug("Cache health check: OK")
            except Exception as e:
                health_status["cache"] = "disconnected"
                health_status["status"] = "unhealthy"
                logger.error(f"Cache health check failed: {e}")

            # Check ML model status (placeholder for now)
            try:
                # TODO: Implement actual ML model health check when ML module is available
                health_status["ml_model"] = "not_implemented"
                logger.debug("ML model health check: Not implemented")
            except Exception as e:
                health_status["ml_model"] = "error"
                logger.error(f"ML model health check failed: {e}")

            return health_status

        except Exception as e:
            logger.error(f"Error during health check: {e}")
            health_status["status"] = "error"
            health_status["error"] = str(e)
            return health_status


class GetAppInfoUseCase:
    """Use case for retrieving application information."""

    def __init__(self, cache_adapter: CachePort):
        self.cache_adapter = cache_adapter

    async def execute(self, db: Session) -> Dict[str, Any]:
        """
        Get detailed application information.

        Args:
            db: Database session

        Returns:
            Dictionary with application information
        """
        try:
            # Check actual service statuses
            database_connected = False
            cache_connected = False

            try:
                db.execute(text("SELECT 1"))
                database_connected = True
            except Exception:
                pass

            try:
                # Test cache connectivity using simple operations
                test_key = "app_info_test"
                await self.cache_adapter.set(test_key, "test", 5)
                await self.cache_adapter.delete(test_key)
                cache_connected = True
            except Exception:
                pass

            app_info = {
                "app_name": settings.APP_NAME,
                "version": settings.API_VERSION,
                "environment": settings.ENVIRONMENT,
                "debug_mode": settings.DEBUG,
                "api_prefix": settings.API_V1_STR,
                "database_connected": database_connected,
                "cache_connected": cache_connected,
                "ml_model_ready": False,  # TODO: Implement when ML module is available
                "features": {
                    "data_ingestion": True,
                    "caching": True,
                    "predictions": False,  # TODO: Enable when ML module is implemented
                    "continuous_learning": False,  # TODO: Enable when ML module is implemented
                    "rest_api": True,
                    "health_monitoring": True,
                },
                "configuration": {
                    "cache_default_ttl": settings.CACHE_DEFAULT_TTL,
                    "mlb_api_base_url": settings.MLB_API_BASE_URL,
                    "mlb_api_version": settings.MLB_API_VERSION,
                },
                "timestamp": datetime.now().isoformat(),
            }

            logger.info("Application info retrieved successfully")
            return app_info

        except Exception as e:
            logger.error(f"Error getting application info: {e}")
            raise SystemException(f"Failed to get application info: {str(e)}")

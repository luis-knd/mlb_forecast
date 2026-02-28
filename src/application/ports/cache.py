"""
Cache port (interface) for the application layer.
This defines how the application interacts with the cache system.
"""

from abc import ABC, abstractmethod
from typing import Any


class CachePort(ABC):
    """Interface for cache operations."""

    @abstractmethod
    async def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the cache by key."""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Set a value in the cache with an optional time-to-live in seconds."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a value from the cache by key."""
        pass

    @abstractmethod
    async def delete_pattern(self, pattern: str) -> int:
        """Delete values matching a pattern. Returns number of deleted keys."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a key exists in the cache."""
        pass

    @abstractmethod
    async def clear(self, pattern: str | None = None) -> int:
        """Clear the cache, optionally by pattern. Returns the number of keys deleted."""
        pass

    @abstractmethod
    async def get_many(self, keys: list[str]) -> dict[str, Any]:
        """Get multiple values from the cache by keys."""
        pass

    @abstractmethod
    async def set_many(self, mapping: dict[str, Any], ttl: int | None = None) -> bool:
        """Set multiple values in the cache with an optional time-to-live in seconds."""
        pass

    @abstractmethod
    async def delete_many(self, keys: list[str]) -> int:
        """Delete multiple values from the cache by keys. Returns the number of keys deleted."""
        pass

    @abstractmethod
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment a numeric value in the cache. Returns the new value."""
        pass

    @abstractmethod
    async def decrement(self, key: str, amount: int = 1) -> int:
        """Decrement a numeric value in the cache. Returns the new value."""
        pass

    @abstractmethod
    async def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        pass

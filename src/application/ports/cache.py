"""
Cache port (interface) for the application layer.
This defines how the application interacts with the cache system.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class CachePort(ABC):
    """Interface for cache operations."""

    @abstractmethod
    async def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the cache by key."""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value in the cache with an optional time-to-live in seconds."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a value from the cache by key."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a key exists in the cache."""
        pass

    @abstractmethod
    async def clear(self, pattern: Optional[str] = None) -> int:
        """Clear the cache, optionally by pattern. Returns the number of keys deleted."""
        pass

    @abstractmethod
    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from the cache by keys."""
        pass

    @abstractmethod
    async def set_many(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set multiple values in the cache with an optional time-to-live in seconds."""
        pass

    @abstractmethod
    async def delete_many(self, keys: List[str]) -> int:
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
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        pass

"""
Cached TeamStats repository implementation.
This module implements the CachedTeamStatsRepository decorator for Caching Strategy.
"""

from typing import Any

from src.application.ports.cache import CachePort
from src.application.ports.team_stats_repository import TeamStatsRepositoryPort
from src.domain.entities.team_stats import TeamStats


class CachedTeamStatsRepository(TeamStatsRepositoryPort):
    """
    Decorator for TeamStatsRepositoryPort that adds caching capabilities.
    """

    CACHE_TTL = 3600  # 1 hour
    CACHE_PREFIX = "team_stats"

    def __init__(self, repository: TeamStatsRepositoryPort, cache: CachePort):
        self.repository = repository
        self.cache = cache

    async def get_by_id(self, stats_id: int) -> TeamStats | None:
        """Get team statistics by its ID with caching."""
        cache_key = f"{self.CACHE_PREFIX}:id:{stats_id}"
        cached_value = await self.cache.get(cache_key)

        if cached_value:
            return cached_value

        result = await self.repository.get_by_id(stats_id)
        if result:
            await self.cache.set(cache_key, result, ttl=self.CACHE_TTL)

        return result

    async def get_by_team_and_season(self, team_id: int, season: int) -> dict | None:
        """Get team statistics by team ID and season with caching."""
        cache_key = f"{self.CACHE_PREFIX}:{team_id}:{season}"
        cached_value = await self.cache.get(cache_key)

        if cached_value:
            return cached_value

        result = await self.repository.get_by_team_and_season(team_id, season)
        if result:
            await self.cache.set(cache_key, result, ttl=self.CACHE_TTL)

        return result

    async def list_by_team(self, team_id: int) -> list[TeamStats]:
        """List all statistics for a specific team across seasons with caching."""
        cache_key = f"{self.CACHE_PREFIX}:team:{team_id}"
        cached_value = await self.cache.get(cache_key)

        if cached_value:
            return cached_value

        result = await self.repository.list_by_team(team_id)
        if result:
            await self.cache.set(cache_key, result, ttl=self.CACHE_TTL)

        return result

    async def list_by_season(self, season: int) -> list[TeamStats]:
        """List statistics for all teams in a specific season with caching."""
        cache_key = f"{self.CACHE_PREFIX}:season:{season}"
        cached_value = await self.cache.get(cache_key)

        if cached_value:
            return cached_value

        result = await self.repository.list_by_season(season)
        if result:
            await self.cache.set(cache_key, result, ttl=self.CACHE_TTL)

        return result

    async def list_top_teams_by_stat(
        self, season: int, stat_name: str, limit: int = 10, descending: bool = True
    ) -> list[TeamStats]:
        """List top teams by a specific statistic with caching."""
        # Include all parameters in cache key
        cache_key = f"{self.CACHE_PREFIX}:top:{season}:{stat_name}:{limit}:{descending}"
        cached_value = await self.cache.get(cache_key)

        if cached_value:
            return cached_value

        result = await self.repository.list_top_teams_by_stat(season, stat_name, limit, descending)
        if result:
            await self.cache.set(cache_key, result, ttl=self.CACHE_TTL)

        return result

    async def save(self, team_stats: TeamStats) -> TeamStats:
        """Save team statistics and invalidate relevant caches."""
        result = await self.repository.save(team_stats)

        # Invalidate related caches
        await self._invalidate_caches(result.team_id, result.season, result.id)

        return result

    async def update_stats(self, stats_id: int, updated_stats: dict[str, Any]) -> TeamStats | None:
        """Update specific statistics and invalidate relevant caches."""
        result = await self.repository.update_stats(stats_id, updated_stats)

        if result:
            await self._invalidate_caches(result.team_id, result.season, result.id)

        return result

    async def delete(self, stats_id: int) -> bool:
        """Delete team statistics and invalidate relevant caches."""
        # We need to know team_id and season to invalidate correctly.
        # Attempt to get it from cache or repo first.
        existing = await self.get_by_id(stats_id)

        deleted = await self.repository.delete(stats_id)

        if deleted and existing:
            await self._invalidate_caches(existing.team_id, existing.season, stats_id)

        return deleted

    async def _invalidate_caches(self, team_id: int, season: int, stats_id: int) -> None:
        """Helper to invalidate caches when data changes."""
        # Direct keys
        await self.cache.delete(f"{self.CACHE_PREFIX}:id:{stats_id}")
        await self.cache.delete(f"{self.CACHE_PREFIX}:{team_id}:{season}")
        await self.cache.delete(f"{self.CACHE_PREFIX}:team:{team_id}")
        await self.cache.delete(f"{self.CACHE_PREFIX}:season:{season}")

        # Pattern invalidation for lists/queries
        # Invalidate top teams lists for this season
        await self.cache.clear(pattern=f"{self.CACHE_PREFIX}:top:{season}:*")

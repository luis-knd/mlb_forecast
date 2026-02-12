from typing import List, Optional

from src.application.ports.cache import CachePort
from src.application.ports.team_repository import TeamRepositoryPort
from src.domain.entities.team import Team


class CachedTeamRepository(TeamRepositoryPort):
    """
    Decorator for TeamRepository that adds caching.
    """

    def __init__(self, repository: TeamRepositoryPort, cache: CachePort, ttl_seconds: int = 3600):
        self.repository = repository
        self.cache = cache
        self.ttl_seconds = ttl_seconds

    async def save(self, team: Team) -> Team:
        """Save a team and invalidate relevant cache entries."""
        saved_team = await self.repository.save(team)
        # Invalidate specific team cache
        await self.cache.delete(f"teams:id:{saved_team.id}")
        await self.cache.delete(f"teams:mlb_id:{saved_team.mlb_id}")
        # Invalidate lists
        # Since we don't know exactly which lists are affected without parsing everything,
        # we might need a broader invalidation or just let them expire.
        # For simplicity/safety in this refactor, we can invalidate all team lists or specific patterns if supported.
        # Assuming the cache port supports pattern based deletion or we accept eventual consistency for lists.
        # Strategy: Invalidate all list queries.
        await self.cache.delete_pattern("teams:list:*")

        return saved_team

    async def get_by_id(self, team_id: int) -> Optional[Team]:
        """Get team by ID with caching."""
        cache_key = f"teams:id:{team_id}"
        cached_data = await self.cache.get(cache_key)

        if cached_data:
            # check if cached_data is a dict (serialized) or object
            # Assuming CachePort returns the object if using internal memory or dict if redis
            # The previous implementation in use case seemed to expect the object or handle it.
            # If strictly using a serialization cache, we'd need to deserialize.
            # For now assuming basic pickling or object storage as per previous use case code which just returned it.
            return cached_data

        team = await self.repository.get_by_id(team_id)
        if team:
            await self.cache.set(cache_key, team, ttl=self.ttl_seconds)

        return team

    async def get_by_mlb_id(self, mlb_id: int) -> Optional[Team]:
        """Get team by MLB ID with caching."""
        cache_key = f"teams:mlb_id:{mlb_id}"
        cached_data = await self.cache.get(cache_key)

        if cached_data:
            return cached_data

        team = await self.repository.get_by_mlb_id(mlb_id)
        if team:
            await self.cache.set(cache_key, team, ttl=self.ttl_seconds)

        return team

    async def list_all(self) -> List[Team]:
        """List all teams with caching."""
        cache_key = "teams:list:all:all"
        cached_data = await self.cache.get(cache_key)

        if cached_data:
            return cached_data

        teams = await self.repository.list_all()
        if teams:
            await self.cache.set(cache_key, teams, ttl=self.ttl_seconds)

        return teams

    async def list_by_league(self, league: str) -> List[Team]:
        """List teams by league with caching."""
        cache_key = f"teams:list:{league}:all"
        cached_data = await self.cache.get(cache_key)

        if cached_data:
            return cached_data

        teams = await self.repository.list_by_league(league)
        if teams:
            await self.cache.set(cache_key, teams, ttl=self.ttl_seconds)

        return teams

    async def list_by_division(self, division: str) -> List[Team]:
        """List teams by division with caching."""
        cache_key = f"teams:list:all:{division}"
        cached_data = await self.cache.get(cache_key)

        if cached_data:
            return cached_data

        teams = await self.repository.list_by_division(division)
        if teams:
            await self.cache.set(cache_key, teams, ttl=self.ttl_seconds)

        return teams

    async def list_by_league_and_division(self, league: str, division: str) -> List[Team]:
        """List teams by league and division with caching."""
        cache_key = f"teams:list:{league}:{division}"
        cached_data = await self.cache.get(cache_key)

        if cached_data:
            return cached_data

        teams = await self.repository.list_by_league_and_division(league, division)
        if teams:
            await self.cache.set(cache_key, teams, ttl=self.ttl_seconds)

        return teams

    async def delete(self, team_id: int) -> bool:
        """Delete a team by its ID and invalidate cache."""
        existing_team = await self.repository.get_by_id(team_id)
        success = await self.repository.delete(team_id)
        if success:
            await self.cache.delete(f"teams:id:{team_id}")
            if existing_team and existing_team.mlb_id is not None:
                await self.cache.delete(f"teams:mlb_id:{existing_team.mlb_id}")
            await self.cache.delete_pattern("teams:list:*")
        return success

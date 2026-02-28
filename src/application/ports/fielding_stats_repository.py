"""
FieldingStats repository port (interface) for the application layer.
This defines how the application interacts with fielding statistics data storage.
"""

from abc import ABC, abstractmethod

from src.domain.entities.fielding_stats import FieldingStats


class FieldingStatsRepositoryPort(ABC):
    """Interface for fielding statistics repository operations."""

    @abstractmethod
    async def get_by_id(self, stats_id: int) -> FieldingStats | None:
        """Get fielding statistics by its ID."""
        pass

    @abstractmethod
    async def get_by_team_and_season(self, team_id: int, season: int) -> FieldingStats | None:
        """Get fielding statistics by team ID and season."""
        pass

    @abstractmethod
    async def list_by_team(self, team_id: int) -> list[FieldingStats]:
        """List all fielding statistics for a specific team across seasons."""
        pass

    @abstractmethod
    async def list_by_season(self, season: int) -> list[FieldingStats]:
        """List fielding statistics for all teams in a specific season."""
        pass

    @abstractmethod
    async def list_top_teams_by_stat(
        self, season: int, stat_name: str, limit: int = 10, descending: bool = True
    ) -> list[FieldingStats]:
        """List top teams by a specific fielding statistic."""
        pass

    @abstractmethod
    async def save(self, fielding_stats: FieldingStats) -> FieldingStats:
        """Save fielding statistics (create or update)."""
        pass

    @abstractmethod
    async def update_stats(self, stats_id: int, updated_stats: dict) -> FieldingStats | None:
        """Update specific fielding statistics for a team."""
        pass

    @abstractmethod
    async def delete(self, stats_id: int) -> bool:
        """Delete fielding statistics by its ID."""
        pass

"""
CatchingStats repository port (interface) for the application layer.
This defines how the application interacts with catching statistics data storage.
"""

from abc import ABC, abstractmethod

from src.domain.entities.catching_stats import CatchingStats


class CatchingStatsRepositoryPort(ABC):
    """Interface for catching statistics repository operations."""

    @abstractmethod
    async def get_by_id(self, stats_id: int) -> CatchingStats | None:
        """Get catching statistics by its ID."""
        pass

    @abstractmethod
    async def get_by_team_and_season(self, team_id: int, season: int) -> CatchingStats | None:
        """Get catching statistics by team ID and season."""
        pass

    @abstractmethod
    async def list_by_team(self, team_id: int) -> list[CatchingStats]:
        """List all catching statistics for a specific team across seasons."""
        pass

    @abstractmethod
    async def list_by_season(self, season: int) -> list[CatchingStats]:
        """List catching statistics for all teams in a specific season."""
        pass

    @abstractmethod
    async def list_top_teams_by_stat(
        self, season: int, stat_name: str, limit: int = 10, descending: bool = True
    ) -> list[CatchingStats]:
        """List top teams by a specific catching statistic."""
        pass

    @abstractmethod
    async def save(self, catching_stats: CatchingStats) -> CatchingStats:
        """Save catching statistics (create or update)."""
        pass

    @abstractmethod
    async def update_stats(self, stats_id: int, updated_stats: dict) -> CatchingStats | None:
        """Update specific catching statistics for a team."""
        pass

    @abstractmethod
    async def delete(self, stats_id: int) -> bool:
        """Delete catching statistics by its ID."""
        pass

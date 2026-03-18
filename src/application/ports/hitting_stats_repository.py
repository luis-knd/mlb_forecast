"""
HittingStats repository port (interface) for the application layer.
This defines how the application interacts with hitting statistics data storage.
"""

from abc import ABC, abstractmethod

from domain.entities.hitting_stats import HittingStats


class HittingStatsRepositoryPort(ABC):
    """Interface for hitting statistics repository operations."""

    @abstractmethod
    async def get_by_id(self, stats_id: int) -> HittingStats | None:
        """Get hitting statistics by its ID."""
        pass

    @abstractmethod
    async def get_by_team_and_season(self, team_id: int, season: int) -> HittingStats | None:
        """Get hitting statistics by team ID and season."""
        pass

    @abstractmethod
    async def list_by_team(self, team_id: int) -> list[HittingStats]:
        """List all hitting statistics for a specific team across seasons."""
        pass

    @abstractmethod
    async def list_by_season(self, season: int) -> list[HittingStats]:
        """List hitting statistics for all teams in a specific season."""
        pass

    @abstractmethod
    async def list_top_teams_by_stat(
        self, season: int, stat_name: str, limit: int = 10, descending: bool = True
    ) -> list[HittingStats]:
        """List top teams by a specific hitting statistic."""
        pass

    @abstractmethod
    async def save(self, hitting_stats: HittingStats) -> HittingStats:
        """Save hitting statistics (create or update)."""
        pass

    @abstractmethod
    async def update_stats(self, stats_id: int, updated_stats: dict) -> HittingStats | None:
        """Update specific hitting statistics for a team."""
        pass

    @abstractmethod
    async def delete(self, stats_id: int) -> bool:
        """Delete hitting statistics by its ID."""
        pass

"""
PitchingStats repository port (interface) for the application layer.
This defines how the application interacts with pitching statistics data storage.
"""

from abc import ABC, abstractmethod

from src.domain.entities.pitching_stats import PitchingStats


class PitchingStatsRepositoryPort(ABC):
    """Interface for pitching statistics repository operations."""

    @abstractmethod
    async def get_by_id(self, stats_id: int) -> PitchingStats | None:
        """Get pitching statistics by its ID."""
        pass

    @abstractmethod
    async def get_by_team_and_season(self, team_id: int, season: int) -> PitchingStats | None:
        """Get pitching statistics by team ID and season."""
        pass

    @abstractmethod
    async def list_by_team(self, team_id: int) -> list[PitchingStats]:
        """List all pitching statistics for a specific team across seasons."""
        pass

    @abstractmethod
    async def list_by_season(self, season: int) -> list[PitchingStats]:
        """List pitching statistics for all teams in a specific season."""
        pass

    @abstractmethod
    async def list_top_teams_by_stat(
        self, season: int, stat_name: str, limit: int = 10, descending: bool = True
    ) -> list[PitchingStats]:
        """List top teams by a specific pitching statistic."""
        pass

    @abstractmethod
    async def save(self, pitching_stats: PitchingStats) -> PitchingStats:
        """Save pitching statistics (create or update)."""
        pass

    @abstractmethod
    async def update_stats(self, stats_id: int, updated_stats: dict) -> PitchingStats | None:
        """Update specific pitching statistics for a team."""
        pass

    @abstractmethod
    async def delete(self, stats_id: int) -> bool:
        """Delete pitching statistics by its ID."""
        pass

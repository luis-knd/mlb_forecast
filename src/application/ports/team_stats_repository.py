"""
TeamStats repository port (interface) for the application layer.
This defines how the application interacts with team statistics data storage.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.entities.team_stats import TeamStats


class TeamStatsRepositoryPort(ABC):
    """Interface for team statistics repository operations."""

    @abstractmethod
    async def get_by_id(self, stats_id: int) -> Optional[TeamStats]:
        """Get team statistics by its ID."""
        pass

    @abstractmethod
    async def get_by_team_and_season(self, team_id: int, season: int) -> Optional[dict]:
        """Get team statistics by team ID and season."""
        pass

    @abstractmethod
    async def list_by_team(self, team_id: int) -> List[TeamStats]:
        """List all statistics for a specific team across seasons."""
        pass

    @abstractmethod
    async def list_by_season(self, season: int) -> List[TeamStats]:
        """List statistics for all teams in a specific season."""
        pass

    @abstractmethod
    async def list_top_teams_by_stat(
        self, season: int, stat_name: str, limit: int = 10, descending: bool = True
    ) -> List[TeamStats]:
        """List top teams by a specific statistic."""
        pass

    @abstractmethod
    async def save(self, team_stats: TeamStats) -> TeamStats:
        """Save team statistics (create or update)."""
        pass

    @abstractmethod
    async def update_stats(self, stats_id: int, updated_stats: dict) -> Optional[TeamStats]:
        """Update specific statistics for a team."""
        pass

    @abstractmethod
    async def delete(self, stats_id: int) -> bool:
        """Delete team statistics by its ID."""
        pass

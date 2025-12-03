"""
Team repository port (interface) for the application layer.
This defines how the application interacts with team data storage.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.entities.team import Team


class TeamRepositoryPort(ABC):
    """Interface for team repository operations."""

    @abstractmethod
    async def get_by_id(self, team_id: int) -> Optional[Team]:
        """Get a team by its ID."""
        pass

    @abstractmethod
    async def get_by_mlb_id(self, mlb_id: int) -> Optional[Team]:
        """Get a team by its MLB ID."""
        pass

    @abstractmethod
    async def list_all(self) -> List[Team]:
        """List all teams."""
        pass

    @abstractmethod
    async def list_by_league(self, league: str) -> List[Team]:
        """List teams by league."""
        pass

    @abstractmethod
    async def list_by_division(self, division: str) -> List[Team]:
        """List teams by division."""
        pass

    @abstractmethod
    async def list_by_league_and_division(self, league: str, division: str) -> List[Team]:
        """List teams by league and division."""
        pass

    @abstractmethod
    async def save(self, team: Team) -> Team:
        """Save a team (create or update)."""
        pass

    @abstractmethod
    async def delete(self, team_id: int) -> bool:
        """Delete a team by its ID."""
        pass

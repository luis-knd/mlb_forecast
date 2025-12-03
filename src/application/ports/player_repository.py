"""
Player repository port (interface) for the application layer.
This defines how the application interacts with player data storage.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.entities.player import Player


class PlayerRepositoryPort(ABC):
    """Interface for player repository operations."""

    @abstractmethod
    async def get_by_id(self, player_id: int) -> Optional[Player]:
        """Get a player by its ID."""
        pass

    @abstractmethod
    async def get_by_mlb_id(self, mlb_id: int) -> Optional[Player]:
        """Get a player by its MLB ID."""
        pass

    @abstractmethod
    async def list_by_team(self, team_id: int) -> List[Player]:
        """List players by team."""
        pass

    @abstractmethod
    async def list_by_position(self, position: str) -> List[Player]:
        """List players by position."""
        pass

    @abstractmethod
    async def list_active_players(self) -> List[Player]:
        """List all active players."""
        pass

    @abstractmethod
    async def search_by_name(self, name: str) -> List[Player]:
        """Search players by name."""
        pass

    @abstractmethod
    async def save(self, player: Player) -> Player:
        """Save a player (create or update)."""
        pass

    @abstractmethod
    async def update_team(self, player_id: int, team_id: Optional[int]) -> Optional[Player]:
        """Update a player's team."""
        pass

    @abstractmethod
    async def delete(self, player_id: int) -> bool:
        """Delete a player by its ID."""
        pass

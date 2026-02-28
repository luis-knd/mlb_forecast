"""
Player repository port (interface) for the application layer.
This defines how the application interacts with player data storage.
"""

from abc import ABC, abstractmethod

from src.domain.entities.player import Player


class PlayerRepositoryPort(ABC):
    """Interface for player repository operations."""

    @abstractmethod
    async def get_by_id(self, player_id: int) -> Player | None:
        """Get a player by its ID."""
        pass

    @abstractmethod
    async def get_by_mlb_id(self, mlb_id: int) -> Player | None:
        """Get a player by its MLB ID."""
        pass

    @abstractmethod
    async def list_by_team(self, team_id: int) -> list[Player]:
        """List players by team."""
        pass

    @abstractmethod
    async def list_by_position(self, position: str) -> list[Player]:
        """List players by position."""
        pass

    @abstractmethod
    async def list_active_players(self) -> list[Player]:
        """List all active players."""
        pass

    @abstractmethod
    async def list_players(
        self,
        team_id: int | None = None,
        position: str | None = None,
        name: str | None = None,
        active: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Player]:
        """List players with optional filters and pagination."""
        pass

    @abstractmethod
    async def search_by_name(self, name: str) -> list[Player]:
        """Search players by name."""
        pass

    @abstractmethod
    async def save(self, player: Player) -> Player:
        """Save a player (create or update)."""
        pass

    @abstractmethod
    async def update_team(self, player_id: int, team_id: int | None) -> Player | None:
        """Update a player's team."""
        pass

    @abstractmethod
    async def delete(self, player_id: int) -> bool:
        """Delete a player by its ID."""
        pass

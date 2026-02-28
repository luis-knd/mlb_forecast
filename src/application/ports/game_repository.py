"""
Game repository port (interface) for the application layer.
This defines how the application interacts with game data storage.
"""

from abc import ABC, abstractmethod
from datetime import date

from src.domain.entities.game import Game


class GameRepositoryPort(ABC):
    """Interface for game repository operations."""

    @abstractmethod
    async def get_by_id(self, game_id: int) -> Game | None:
        """Get a game by its ID."""
        pass

    @abstractmethod
    async def get_by_mlb_id(self, mlb_game_id: int) -> Game | None:
        """Get a game by its MLB ID."""
        pass

    @abstractmethod
    async def list_by_date(self, game_date: date) -> list[Game]:
        """List games by date."""
        pass

    @abstractmethod
    async def list_by_team(self, team_id: int, limit: int = 50) -> list[Game]:
        """List games by team."""
        pass

    @abstractmethod
    async def list_by_status(self, status: str, limit: int = 50) -> list[Game]:
        """List games by status."""
        pass

    @abstractmethod
    async def list_upcoming_games(self, days_ahead: int = 7, limit: int = 50) -> list[Game]:
        """List upcoming games."""
        pass

    @abstractmethod
    async def list_historical_matchups(self, home_team_id: int, away_team_id: int, limit: int = 10) -> list[Game]:
        """List historical matchups between two teams."""
        pass

    @abstractmethod
    async def save(self, game: Game) -> Game:
        """Save a game (create or update)."""
        pass

    @abstractmethod
    async def update_game_result(
        self, game_id: int, home_score: int, away_score: int, status: str = "completed"
    ) -> Game | None:
        """Update a game's result."""
        pass

    @abstractmethod
    async def delete(self, game_id: int) -> bool:
        """Delete a game by its ID."""
        pass

from abc import ABC, abstractmethod
from datetime import date
from typing import Any

from application.dto.mlb_api_response import MLBGameDTO, MLBPlayerDTO, MLBTeamDTO


class MLBApiPort(ABC):
    """Interface for MLB API operations."""

    @abstractmethod
    async def get_teams(self) -> list[MLBTeamDTO]:
        """Get all MLB teams from the API."""
        pass

    @abstractmethod
    async def get_team_by_id(self, mlb_team_id: int) -> MLBTeamDTO | None:
        """Get a specific team by its MLB ID."""
        pass

    @abstractmethod
    async def get_games_by_date(self, game_date: date) -> list[MLBGameDTO]:
        """Get all games for a specific date."""
        pass

    @abstractmethod
    async def get_game_by_id(self, mlb_game_id: int) -> MLBGameDTO | None:
        """Get a specific game by its MLB ID."""
        pass

    @abstractmethod
    async def get_team_stats(self, season: int, group: str, mlb_team_id: int | None = None) -> dict[str, Any] | None:
        """Get statistics for a specific team and season, or all teams if mlb_team_id is None."""
        pass

    @abstractmethod
    async def get_player_by_id(self, mlb_player_id: int) -> MLBPlayerDTO | None:
        """Get a specific player by its MLB ID."""
        pass

    @abstractmethod
    async def get_players_by_team(
        self,
        mlb_team_id: int,
        season: int | None = None,
        roster_type: str = "active",
    ) -> list[MLBPlayerDTO]:
        """Get players for a specific team, season and roster type."""
        pass

    @abstractmethod
    async def get_players_by_sport(
        self,
        sport_id: int = 1,
        season: int | None = None,
        team_mlb_id: int | None = None,
    ) -> list[MLBPlayerDTO]:
        """Get players by sport with optional season and optional team filter."""
        pass

    @abstractmethod
    async def get_player_stats(
        self,
        mlb_player_id: int,
        stats: str,
        group: str,
        season: int | None = None,
        game_type: str | None = None,
        days_back: int | None = None,
    ) -> dict[str, Any] | None:
        """Get statistics for a specific player and filters."""
        pass

    @abstractmethod
    async def search_players(self, query: str) -> list[MLBPlayerDTO]:
        """Search for players by name or other criteria."""
        pass

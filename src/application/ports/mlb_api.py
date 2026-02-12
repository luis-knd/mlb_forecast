from abc import ABC, abstractmethod
from datetime import date
from typing import Any, Dict, List, Optional

from src.application.dto.mlb_api_response import MLBGameDTO, MLBPlayerDTO, MLBTeamDTO


class MLBApiPort(ABC):
    """Interface for MLB API operations."""

    @abstractmethod
    async def get_teams(self) -> List[MLBTeamDTO]:
        """Get all MLB teams from the API."""
        pass

    @abstractmethod
    async def get_team_by_id(self, mlb_team_id: int) -> Optional[MLBTeamDTO]:
        """Get a specific team by its MLB ID."""
        pass

    @abstractmethod
    async def get_games_by_date(self, game_date: date) -> List[MLBGameDTO]:
        """Get all games for a specific date."""
        pass

    @abstractmethod
    async def get_game_by_id(self, mlb_game_id: int) -> Optional[MLBGameDTO]:
        """Get a specific game by its MLB ID."""
        pass

    @abstractmethod
    async def get_team_stats(
        self, season: int, group: str, mlb_team_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific team and season, or all teams if mlb_team_id is None."""
        pass

    @abstractmethod
    async def get_player_by_id(self, mlb_player_id: int) -> Optional[MLBPlayerDTO]:
        """Get a specific player by its MLB ID."""
        pass

    @abstractmethod
    async def get_players_by_team(self, mlb_team_id: int) -> List[MLBPlayerDTO]:
        """Get all players for a specific team."""
        pass

    @abstractmethod
    async def get_player_stats(self, mlb_player_id: int, season: int) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific player and season."""
        pass

    @abstractmethod
    async def search_players(self, query: str) -> List[MLBPlayerDTO]:
        """Search for players by name or other criteria."""
        pass

"""
Use cases for game operations.
These define the application's business logic for game operations.
"""

from datetime import date, datetime, timedelta
from typing import List, Optional

from src.application.dto.mlb_api_response import MLBGameDTO
from src.application.ports.cache import CachePort
from src.application.ports.game_repository import GameRepositoryPort
from src.application.ports.mlb_api import MLBApiPort
from src.application.ports.team_repository import TeamRepositoryPort
from src.domain.entities.game import Game


class ListGamesUseCase:
    """Use case for listing games."""

    def __init__(self, game_repository: GameRepositoryPort, cache: CachePort):
        self.game_repository = game_repository
        self.cache = cache

    async def execute(
        self,
        game_date: Optional[date] = None,
        team_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Game]:
        """
        List games, optionally filtered by date, team, or status.

        Args:
            game_date: Optional filter by date
            team_id: Optional filter by team ID
            status: Optional filter by game status
            limit: Maximum number of games to return

        Returns:
            List of Game entities
        """
        cache_key = f"games:list:{game_date or 'all'}:{team_id or 'all'}:{status or 'all'}:{limit}"

        # Try to get from cache first
        cached_games = await self.cache.get(cache_key)
        if cached_games:
            return cached_games

        # Get from repository
        if game_date:
            games = await self.game_repository.list_by_date(game_date)
        elif team_id:
            games = await self.game_repository.list_by_team(team_id, limit)
        elif status:
            games = await self.game_repository.list_by_status(status, limit)
        else:
            # Default to upcoming games if no filters are provided
            games = await self.game_repository.list_upcoming_games(days_ahead=7, limit=limit)

        # Cache the result
        await self.cache.set(cache_key, games, ttl=1800)  # Cache for 30 minutes

        return games


class GetGameUseCase:
    """Use case for getting a game by ID."""

    def __init__(self, game_repository: GameRepositoryPort, cache: CachePort):
        self.game_repository = game_repository
        self.cache = cache

    async def execute(self, game_id: int) -> Optional[Game]:
        """
        Get a game by its ID.

        Args:
            game_id: The ID of the game to get

        Returns:
            Game entity or None if not found
        """
        cache_key = f"games:id:{game_id}"

        # Try to get from cache first
        cached_game = await self.cache.get(cache_key)
        if cached_game:
            return cached_game

        # Get from repository
        game = await self.game_repository.get_by_id(game_id)

        # Cache the result if found
        if game:
            await self.cache.set(cache_key, game, ttl=1800)  # Cache for 30 minutes

        return game


class IngestGamesUseCase:
    """Use case for ingesting games from the MLB API."""

    def __init__(
        self,
        game_repository: GameRepositoryPort,
        team_repository: TeamRepositoryPort,
        mlb_api: MLBApiPort,
        cache: CachePort,
    ):
        self.game_repository = game_repository
        self.team_repository = team_repository
        self.mlb_api = mlb_api
        self.cache = cache

    async def execute(self, game_date: Optional[date] = None, days_back: int = 7) -> List[Game]:
        """
        Ingest games from the MLB API and save them to the repository.

        Args:
            game_date: Optional specific date to ingest games for
            days_back: Number of days back to ingest games for if no specific date is provided

        Returns:
            List of ingested Game entities
        """
        ingested_games = []

        if game_date:
            # Ingest games for a specific date
            games_data = await self.mlb_api.get_games_by_date(game_date)
            ingested_games.extend(await self._process_games_data(games_data))
        else:
            # Ingest games for the last N days
            today = datetime.now().date()
            for i in range(days_back):
                date_to_ingest = today - timedelta(days=i)
                games_data = await self.mlb_api.get_games_by_date(date_to_ingest)
                ingested_games.extend(await self._process_games_data(games_data))

        # Clear cache for games
        await self.cache.clear(pattern="games:*")

        return ingested_games

    async def _process_games_data(self, games_data: List["MLBGameDTO"]) -> List[Game]:
        """Process games data from the MLB API and save to repository."""
        processed_games = []

        for game_data in games_data:
            # Get team IDs from repository
            home_team = await self.team_repository.get_by_mlb_id(game_data.home_team_id)
            away_team = await self.team_repository.get_by_mlb_id(game_data.away_team_id)

            if not home_team or not away_team:
                # Skip games with unknown teams
                continue

            # Validate team IDs are not None before creating game
            if home_team.id is None or away_team.id is None or game_data.game_date is None:
                continue

            # Map winning team ID from MLB ID to internal ID if present
            winning_team_id = None
            if game_data.winning_team_id is not None:
                mlb_winning_team_id = game_data.winning_team_id
                if mlb_winning_team_id == game_data.home_team_id:
                    winning_team_id = home_team.id
                elif mlb_winning_team_id == game_data.away_team_id:
                    winning_team_id = away_team.id

            # Create game entity with all data from the adapter
            game = Game.create(
                mlb_game_id=game_data.id,
                home_team_id=home_team.id,
                away_team_id=away_team.id,
                game_date=game_data.game_date,
                status=game_data.status,
                scheduled_innings=game_data.scheduled_innings,
                home_score=game_data.home_score,
                away_score=game_data.away_score,
            )

            # Set the mapped winning team ID
            if winning_team_id is not None:
                game.winning_team_id = winning_team_id

            # Save to repository
            saved_game = await self.game_repository.save(game)
            processed_games.append(saved_game)

        return processed_games


class ListUpcomingGamesUseCase:
    """Use case for listing upcoming games."""

    def __init__(self, game_repository: GameRepositoryPort, cache: CachePort):
        self.game_repository = game_repository
        self.cache = cache

    async def execute(self, days_ahead: int = 7, limit: int = 20) -> List[Game]:
        """
        List upcoming games for the next N days.

        Args:
            days_ahead: Number of days ahead to look for games
            limit: Maximum number of games to return

        Returns:
            List of Game entities
        """
        cache_key = f"games:upcoming:{days_ahead}:{limit}"

        # Try to get from cache first
        cached_games = await self.cache.get(cache_key)
        if cached_games:
            return cached_games

        # Get from repository
        games = await self.game_repository.list_upcoming_games(days_ahead, limit)

        # Cache the result
        await self.cache.set(cache_key, games, ttl=1800)  # Cache for 30 minutes

        return games

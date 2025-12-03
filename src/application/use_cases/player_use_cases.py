"""
Use cases for player operations.
These define the application's business logic for player operations.
"""

from typing import List, Optional

from src.application.ports.cache import CachePort
from src.application.ports.mlb_api import MLBApiPort
from src.application.ports.player_repository import PlayerRepositoryPort
from src.application.ports.team_repository import TeamRepositoryPort
from src.domain.entities.player import Player


class GetPlayerUseCase:
    """Use case for getting a player by ID."""

    def __init__(self, player_repository: PlayerRepositoryPort, cache: CachePort):
        self.player_repository = player_repository
        self.cache = cache

    async def execute(self, player_id: int) -> Optional[Player]:
        """
        Get a player by its ID.

        Args:
            player_id: The ID of the player to get

        Returns:
            Player entity or None if not found
        """
        cache_key = f"players:id:{player_id}"

        # Try to get from cache first
        cached_player = await self.cache.get(cache_key)
        if cached_player:
            return cached_player

        # Get from repository
        player = await self.player_repository.get_by_id(player_id)

        # Cache the result if found
        if player:
            await self.cache.set(cache_key, player, ttl=3600)  # Cache for 1 hour

        return player


class ListPlayersByTeamUseCase:
    """Use case for listing players by team."""

    def __init__(self, player_repository: PlayerRepositoryPort, cache: CachePort):
        self.player_repository = player_repository
        self.cache = cache

    async def execute(self, team_id: int) -> List[Player]:
        """
        List players by team.

        Args:
            team_id: The ID of the team

        Returns:
            List of Player entities
        """
        cache_key = f"players:team:{team_id}"

        # Try to get from cache first
        cached_players = await self.cache.get(cache_key)
        if cached_players:
            return cached_players

        # Get from repository
        players = await self.player_repository.list_by_team(team_id)

        # Cache the result
        await self.cache.set(cache_key, players, ttl=3600)  # Cache for 1 hour

        return players


class ListPlayersByPositionUseCase:
    """Use case for listing players by position."""

    def __init__(self, player_repository: PlayerRepositoryPort, cache: CachePort):
        self.player_repository = player_repository
        self.cache = cache

    async def execute(self, position: str) -> List[Player]:
        """
        List players by position.

        Args:
            position: The position to filter by

        Returns:
            List of Player entities
        """
        cache_key = f"players:position:{position}"

        # Try to get from cache first
        cached_players = await self.cache.get(cache_key)
        if cached_players:
            return cached_players

        # Get from repository
        players = await self.player_repository.list_by_position(position)

        # Cache the result
        await self.cache.set(cache_key, players, ttl=3600)  # Cache for 1 hour

        return players


class SearchPlayersUseCase:
    """Use case for searching players by name."""

    def __init__(self, player_repository: PlayerRepositoryPort, cache: CachePort):
        self.player_repository = player_repository
        self.cache = cache

    async def execute(self, name: str) -> List[Player]:
        """
        Search players by name.

        Args:
            name: The name to search for

        Returns:
            List of Player entities
        """
        cache_key = f"players:search:{name}"

        # Try to get from cache first
        cached_players = await self.cache.get(cache_key)
        if cached_players:
            return cached_players

        # Get from repository
        players = await self.player_repository.search_by_name(name)

        # Cache the result
        await self.cache.set(cache_key, players, ttl=3600)  # Cache for 1 hour

        return players


class IngestPlayersUseCase:
    """Use case for ingesting players from the MLB API."""

    def __init__(
        self,
        player_repository: PlayerRepositoryPort,
        team_repository: TeamRepositoryPort,
        mlb_api: MLBApiPort,
        cache: CachePort,
    ):
        self.player_repository = player_repository
        self.team_repository = team_repository
        self.mlb_api = mlb_api
        self.cache = cache

    async def execute(self) -> List[Player]:
        """
        Ingest players from the MLB API.

        Returns:
            List of ingested Player entities
        """
        # Get all teams
        teams = await self.team_repository.list_all()

        # Ingest players for each team
        ingested_players = []
        for team in teams:
            # Get players from MLB API
            players_data = await self.mlb_api.get_players_by_team(team.mlb_id)

            for player_data in players_data:
                # Create Player entity
                player = Player.create(
                    mlb_id=player_data["id"],
                    first_name=player_data["first_name"],
                    last_name=player_data["last_name"],
                    position=player_data["position"],
                    bats=player_data.get("bats"),
                    throws=player_data.get("throws"),
                    birth_date=player_data.get("birth_date"),
                    active=player_data.get("active", True),
                    current_team_id=team.id,
                )

                # Save to repository
                saved_player = await self.player_repository.save(player)
                ingested_players.append(saved_player)

        # Clear cache for players
        await self.cache.clear(pattern="players:*")

        return ingested_players


class UpdatePlayerTeamUseCase:
    """Use case for updating a player's team."""

    def __init__(self, player_repository: PlayerRepositoryPort, cache: CachePort):
        self.player_repository = player_repository
        self.cache = cache

    async def execute(self, player_id: int, team_id: Optional[int]) -> Optional[Player]:
        """
        Update a player's team.

        Args:
            player_id: The ID of the player to update
            team_id: The new team ID, or None if the player is a free agent

        Returns:
            Updated Player entity or None if update failed
        """
        # Update in repository
        updated_player = await self.player_repository.update_team(player_id, team_id)

        if updated_player:
            # Clear cache for this player
            await self.cache.clear(pattern=f"players:id:{player_id}")

            # Clear cache for team players
            if updated_player.current_team_id:
                await self.cache.clear(pattern=f"players:team:{updated_player.current_team_id}")

            # If team_id is provided and different from current, clear cache for that team too
            if team_id and team_id != updated_player.current_team_id:
                await self.cache.clear(pattern=f"players:team:{team_id}")

        return updated_player

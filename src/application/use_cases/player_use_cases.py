"""
Use cases for player operations.
These define the application's business logic for player operations.
"""

from src.application.ports.cache import CachePort
from src.application.ports.mlb_api import MLBApiPort
from src.application.ports.player_repository import PlayerRepositoryPort
from src.application.ports.team_repository import TeamRepositoryPort
from src.domain.entities.player import Player

CACHE_TTL_SECONDS = 3600
PLAYER_STATS_TTL_SECONDS = 900
ALLOWED_INGEST_SOURCES = {"team_roster", "sport_players", "search"}
ALLOWED_PLAYER_STATS = {"season", "career", "yearByYear", "gameLog", "statSplits", "seasonAdvanced"}
ALLOWED_PLAYER_GROUPS = {"hitting", "pitching", "fielding", "catching", "running"}
ALLOWED_GAME_TYPES = {"R", "S", "P", "W", "A"}


def _cache_token(value: str | None) -> str:
    if value is None:
        return "none"
    normalized = value.strip().lower()
    return normalized if normalized else "none"


class GetPlayerUseCase:
    """Use case for getting a player by ID."""

    def __init__(self, player_repository: PlayerRepositoryPort, cache: CachePort):
        self.player_repository = player_repository
        self.cache = cache

    async def execute(self, player_id: int) -> Player | None:
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
            await self.cache.set(cache_key, player, ttl=CACHE_TTL_SECONDS)

        return player


class GetPlayerByMlbIdUseCase:
    """Use case for getting a player by MLB person ID."""

    def __init__(self, player_repository: PlayerRepositoryPort, cache: CachePort):
        self.player_repository = player_repository
        self.cache = cache

    async def execute(self, mlb_player_id: int) -> Player | None:
        cache_key = f"players:mlb_id:{mlb_player_id}"

        cached_player = await self.cache.get(cache_key)
        if cached_player:
            return cached_player

        player = await self.player_repository.get_by_mlb_id(mlb_player_id)
        if player:
            await self.cache.set(cache_key, player, ttl=CACHE_TTL_SECONDS)

        return player


class ListPlayersByTeamUseCase:
    """Use case for listing players by team."""

    def __init__(self, player_repository: PlayerRepositoryPort, cache: CachePort):
        self.player_repository = player_repository
        self.cache = cache

    async def execute(self, team_id: int) -> list[Player]:
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
        await self.cache.set(cache_key, players, ttl=CACHE_TTL_SECONDS)

        return players


class ListPlayersByPositionUseCase:
    """Use case for listing players by position."""

    def __init__(self, player_repository: PlayerRepositoryPort, cache: CachePort):
        self.player_repository = player_repository
        self.cache = cache

    async def execute(self, position: str) -> list[Player]:
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
        await self.cache.set(cache_key, players, ttl=CACHE_TTL_SECONDS)

        return players


class SearchPlayersUseCase:
    """Use case for searching players by name."""

    def __init__(self, player_repository: PlayerRepositoryPort, cache: CachePort):
        self.player_repository = player_repository
        self.cache = cache

    async def execute(self, name: str) -> list[Player]:
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
        await self.cache.set(cache_key, players, ttl=CACHE_TTL_SECONDS)

        return players


class ListPlayersUseCase:
    """Use case for listing players with optional filters and pagination."""

    def __init__(self, player_repository: PlayerRepositoryPort, cache: CachePort):
        self.player_repository = player_repository
        self.cache = cache

    async def execute(
        self,
        team_id: int | None = None,
        position: str | None = None,
        name: str | None = None,
        active: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Player]:
        cache_key = (
            "players:list:"
            f"team={team_id if team_id is not None else 'none'}:"
            f"position={_cache_token(position)}:"
            f"name={_cache_token(name)}:"
            f"active={active if active is not None else 'none'}:"
            f"limit={limit}:offset={offset}"
        )

        cached_players = await self.cache.get(cache_key)
        if cached_players:
            return cached_players

        players = await self.player_repository.list_players(
            team_id=team_id,
            position=position,
            name=name,
            active=active,
            limit=limit,
            offset=offset,
        )

        await self.cache.set(cache_key, players, ttl=CACHE_TTL_SECONDS)
        return players


class GetPlayerStatsUseCase:
    """Use case for retrieving player stats from MLB API with validation and cache."""

    def __init__(self, mlb_api: MLBApiPort, cache: CachePort):
        self.mlb_api = mlb_api
        self.cache = cache

    async def execute(
        self,
        mlb_player_id: int,
        stats: str,
        group: str,
        season: int | None = None,
        game_type: str | None = None,
        days_back: int | None = None,
    ) -> dict | None:
        normalized_stats = stats.strip()
        normalized_group = group.strip().lower()
        normalized_game_type = game_type.strip().upper() if game_type else None

        self._validate_query(
            normalized_stats=normalized_stats,
            normalized_group=normalized_group,
            season=season,
            normalized_game_type=normalized_game_type,
            days_back=days_back,
        )
        cache_key = self._build_cache_key(
            mlb_player_id=mlb_player_id,
            normalized_stats=normalized_stats,
            normalized_group=normalized_group,
            season=season,
            normalized_game_type=normalized_game_type,
            days_back=days_back,
        )

        cached_stats = await self.cache.get(cache_key)
        if cached_stats:
            return cached_stats

        player_stats = await self.mlb_api.get_player_stats(
            mlb_player_id=mlb_player_id,
            stats=normalized_stats,
            group=normalized_group,
            season=season,
            game_type=normalized_game_type,
            days_back=days_back,
        )

        if player_stats:
            await self.cache.set(cache_key, player_stats, ttl=PLAYER_STATS_TTL_SECONDS)

        return player_stats

    def _validate_query(
        self,
        normalized_stats: str,
        normalized_group: str,
        season: int | None,
        normalized_game_type: str | None,
        days_back: int | None,
    ) -> None:
        if normalized_stats not in ALLOWED_PLAYER_STATS:
            raise ValueError(f"stats must be one of: {', '.join(sorted(ALLOWED_PLAYER_STATS))}")
        if normalized_group not in ALLOWED_PLAYER_GROUPS:
            raise ValueError(f"group must be one of: {', '.join(sorted(ALLOWED_PLAYER_GROUPS))}")
        if season is not None and season < 1876:
            raise ValueError("season must be greater than or equal to 1876")
        if normalized_game_type and normalized_game_type not in ALLOWED_GAME_TYPES:
            raise ValueError(f"gameType must be one of: {', '.join(sorted(ALLOWED_GAME_TYPES))}")
        if days_back is not None and not 1 <= days_back <= 366:
            raise ValueError("daysBack must be between 1 and 366")

    def _build_cache_key(
        self,
        mlb_player_id: int,
        normalized_stats: str,
        normalized_group: str,
        season: int | None,
        normalized_game_type: str | None,
        days_back: int | None,
    ) -> str:
        return (
            "player_stats:"
            f"player={mlb_player_id}:stats={normalized_stats}:group={normalized_group}:"
            f"season={season if season is not None else 'none'}:"
            f"gameType={normalized_game_type if normalized_game_type else 'none'}:"
            f"daysBack={days_back if days_back is not None else 'none'}"
        )


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

    async def execute(self) -> list[Player]:
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
                    mlb_id=player_data.id,
                    first_name=player_data.first_name,
                    last_name=player_data.last_name,
                    position=player_data.position,
                    bats=player_data.bats or None,
                    throws=player_data.throws or None,
                    birth_date=player_data.birth_date,
                    active=player_data.active,
                    current_team_id=team.id,
                )

                # Save to repository
                saved_player = await self.player_repository.save(player)
                ingested_players.append(saved_player)

        # Clear cache for players and player stats
        await self.cache.clear(pattern="players:*")
        await self.cache.clear(pattern="player_stats:*")

        return ingested_players


class IngestPlayersBySourceUseCase:
    """Ingest players using supported StatsAPI source modes."""

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

    async def execute(
        self,
        source: str,
        season: int | None = None,
        team_mlb_id: int | None = None,
        roster_type: str = "active",
        sport_id: int = 1,
        query: str | None = None,
    ) -> list[Player]:
        normalized_source = source.strip().lower()
        if normalized_source not in ALLOWED_INGEST_SOURCES:
            raise ValueError(f"source must be one of: {', '.join(sorted(ALLOWED_INGEST_SOURCES))}")
        if season is not None and season < 1876:
            raise ValueError("season must be greater than or equal to 1876")
        players_dto, default_team_mlb_id = await self._get_players_by_source(
            normalized_source=normalized_source,
            season=season,
            team_mlb_id=team_mlb_id,
            roster_type=roster_type,
            sport_id=sport_id,
            query=query,
        )
        team_id_cache: dict[int, int | None] = {}
        ingested_players: list[Player] = []

        for player_dto in players_dto:
            candidate_team_mlb_id = player_dto.current_team_id or default_team_mlb_id
            internal_team_id = await self._resolve_internal_team_id(candidate_team_mlb_id, team_id_cache)

            player = Player.create(
                mlb_id=player_dto.id,
                first_name=player_dto.first_name,
                last_name=player_dto.last_name,
                position=player_dto.position,
                bats=player_dto.bats or None,
                throws=player_dto.throws or None,
                birth_date=player_dto.birth_date,
                active=player_dto.active,
                current_team_id=internal_team_id,
            )

            saved_player = await self.player_repository.save(player)
            ingested_players.append(saved_player)

        await self.cache.clear(pattern="players:*")
        await self.cache.clear(pattern="player_stats:*")
        return ingested_players

    async def _get_players_by_source(
        self,
        normalized_source: str,
        season: int | None,
        team_mlb_id: int | None,
        roster_type: str,
        sport_id: int,
        query: str | None,
    ) -> tuple[list, int | None]:
        if normalized_source == "team_roster":
            if team_mlb_id is None:
                raise ValueError("teamId is required when source=team_roster")
            players_dto = await self.mlb_api.get_players_by_team(
                mlb_team_id=team_mlb_id,
                season=season,
                roster_type=roster_type,
            )
            return players_dto, team_mlb_id
        if normalized_source == "sport_players":
            players_dto = await self.mlb_api.get_players_by_sport(
                sport_id=sport_id,
                season=season,
                team_mlb_id=team_mlb_id,
            )
            if team_mlb_id is None:
                return players_dto, None
            filtered_players_dto = [player for player in players_dto if player.current_team_id == team_mlb_id]
            return filtered_players_dto, team_mlb_id

        normalized_query = query.strip() if query else ""
        if not normalized_query:
            raise ValueError("q is required when source=search")
        players_dto = await self.mlb_api.search_players(query=normalized_query)
        return players_dto, None

    async def _resolve_internal_team_id(
        self,
        mlb_team_id: int | None,
        team_id_cache: dict[int, int | None],
    ) -> int | None:
        if mlb_team_id is None:
            return None

        if mlb_team_id in team_id_cache:
            return team_id_cache[mlb_team_id]

        team = await self.team_repository.get_by_mlb_id(mlb_team_id)
        team_id_cache[mlb_team_id] = team.id if team else None
        return team_id_cache[mlb_team_id]


class UpdatePlayerTeamUseCase:
    """Use case for updating a player's team."""

    def __init__(self, player_repository: PlayerRepositoryPort, cache: CachePort):
        self.player_repository = player_repository
        self.cache = cache

    async def execute(self, player_id: int, team_id: int | None) -> Player | None:
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
            await self.cache.clear(pattern="players:list:*")
            await self.cache.clear(pattern=f"players:mlb_id:{updated_player.mlb_id}")

            # Clear cache for team players
            if updated_player.current_team_id:
                await self.cache.clear(pattern=f"players:team:{updated_player.current_team_id}")

            # If team_id is provided and different from current, clear cache for that team too
            if team_id and team_id != updated_player.current_team_id:
                await self.cache.clear(pattern=f"players:team:{team_id}")

        return updated_player

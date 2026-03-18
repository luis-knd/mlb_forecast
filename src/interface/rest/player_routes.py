from datetime import datetime

from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from application.ports.cache import CachePort
from application.use_cases.player_use_cases import (
    GetPlayerByMlbIdUseCase,
    GetPlayerStatsUseCase,
    GetPlayerUseCase,
    IngestPlayersBySourceUseCase,
    ListPlayersUseCase,
)
from application.use_cases.team_use_cases import GetTeamUseCase
from infrastructure.cache.cache_provider import get_cache_adapter
from infrastructure.config.settings import settings
from infrastructure.db.database import get_db
from infrastructure.db.repositories.cached_team_repository import CachedTeamRepository
from infrastructure.db.repositories.player_repository import PlayerRepository
from infrastructure.db.repositories.team_repository import TeamRepository
from infrastructure.mlb_api.adapter import MLBApiAdapter
from interface.rest.adapters.mappers import to_player_payload, to_player_payload_list
from interface.rest.exception_handlers import DomainExceptions
from interface.rest.generated.models.models import (
    BadRequest,
    DataIngestionResponse,
    DataIngestionResultDTO,
    InternalServerError,
    NotFound,
    PlayerDetailResponse,
    PlayerListResponse,
    PlayerStatsResponse,
    ServiceUnavailable,
    UnprocessableEntity,
)
from interface.rest.response_handler import ResponseHandler

router = APIRouter()


def get_player_use_cases(
    db: Session = Depends(get_db),
    cache: CachePort = Depends(get_cache_adapter),
):
    player_repository = PlayerRepository(db)
    team_repository = TeamRepository(db)
    cached_team_repository = CachedTeamRepository(team_repository, cache)
    mlb_api_adapter = MLBApiAdapter()

    return {
        "list_players": ListPlayersUseCase(player_repository, cache),
        "get_player": GetPlayerUseCase(player_repository, cache),
        "get_team": GetTeamUseCase(cached_team_repository),
        "get_player_by_mlb_id": GetPlayerByMlbIdUseCase(player_repository, cache),
        "ingest_players_by_source": IngestPlayersBySourceUseCase(
            player_repository,
            cached_team_repository,
            mlb_api_adapter,
            cache,
        ),
        "get_player_stats": GetPlayerStatsUseCase(
            mlb_api_adapter,
            cache,
            all_groups_concurrency=settings.MLB_PLAYER_STATS_ALL_GROUPS_CONCURRENCY,
        ),
    }


@router.get(
    "/players",
    tags=["Players"],
    response_model=PlayerListResponse,
    responses={
        "400": {"model": BadRequest},
        "404": {"model": NotFound},
        "422": {"model": UnprocessableEntity},
        "500": {"model": InternalServerError},
        "503": {"model": ServiceUnavailable},
    },
)
async def list_players(
    team_id: int | None = Query(None, description="Filter by internal team ID"),
    position: str | None = Query(None, description="Filter by position abbreviation"),
    name: str | None = Query(None, description="Filter by player name"),
    active: bool | None = Query(None, description="Filter by active status"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of players to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    use_cases: dict = Depends(get_player_use_cases),
) -> JSONResponse:
    if team_id is not None and team_id <= 0:
        raise DomainExceptions.InvalidDataError("team_id must be a positive integer")

    players = await use_cases["list_players"].execute(
        team_id=team_id,
        position=position,
        name=name,
        active=active,
        limit=limit,
        offset=offset,
    )

    players_payload = to_player_payload_list(players)
    return ResponseHandler.success(
        data=players_payload,
        message=f"Retrieved {len(players_payload)} players successfully",
    )


@router.get(
    "/players/{player_id}",
    tags=["Players"],
    response_model=PlayerDetailResponse,
    responses={
        "400": {"model": BadRequest},
        "404": {"model": NotFound},
        "422": {"model": UnprocessableEntity},
        "500": {"model": InternalServerError},
        "503": {"model": ServiceUnavailable},
    },
)
async def get_player(
    player_id: int = Path(..., description="MLB personId"),
    use_cases: dict = Depends(get_player_use_cases),
) -> JSONResponse:
    if player_id <= 0:
        raise DomainExceptions.InvalidDataError("player_id must be a positive integer")

    player = await use_cases["get_player_by_mlb_id"].execute(mlb_player_id=player_id)
    if not player:
        raise DomainExceptions.PlayerNotFoundError(player_id)

    return ResponseHandler.success(
        data=to_player_payload(player),
        message=f"Player {player.full_name()} retrieved successfully",
    )


@router.get(
    "/players/{player_id}/stats",
    tags=["Players", "Stats"],
    response_model=PlayerStatsResponse,
    responses={
        "400": {"model": BadRequest},
        "404": {"model": NotFound},
        "422": {"model": UnprocessableEntity},
        "500": {"model": InternalServerError},
        "503": {"model": ServiceUnavailable},
    },
)
async def get_player_stats(
    player_id: int = Path(..., description="Internal player ID"),
    stats: str = Query(..., description="Stats type (season, career, yearByYear, gameLog, statSplits, seasonAdvanced)"),
    group: str = Query(..., description="Stats group (hitting, pitching, fielding, catching, running, all)"),
    season: int | None = Query(None, description="Season year"),
    game_type: str | None = Query(
        None,
        alias="gameType",
        description="Game type code: R=Regular Season, S=Spring Training, P=Postseason, W=World Series, A=All-Star",
    ),
    days_back: int | None = Query(None, alias="daysBack", description="Rolling days back"),
    use_cases: dict = Depends(get_player_use_cases),
) -> JSONResponse:
    if player_id <= 0:
        raise DomainExceptions.InvalidDataError("player_id must be a positive integer")

    player = await use_cases["get_player"].execute(player_id=player_id)
    if not player:
        raise DomainExceptions.PlayerNotFoundError(player_id)

    try:
        player_stats = await use_cases["get_player_stats"].execute(
            mlb_player_id=player.mlb_id,
            stats=stats,
            group=group,
            season=season,
            game_type=game_type,
            days_back=days_back,
        )
    except ValueError as error:
        raise DomainExceptions.InvalidDataError(str(error)) from error

    if not player_stats:
        return ResponseHandler.not_found("Player stats", player_id)

    response_payload = {**player_stats, "player_id": player_id}
    return ResponseHandler.success(
        data=response_payload,
        message=(f"Player stats retrieved successfully for player {player_id} (stats={stats}, group={group})"),
    )


@router.post(
    "/data/ingest/players",
    tags=["Players", "Data Ingestion"],
    response_model=DataIngestionResponse,
    status_code=201,
    responses={
        "201": {"model": DataIngestionResponse},
        "400": {"model": BadRequest},
        "404": {"model": NotFound},
        "422": {"model": UnprocessableEntity},
        "500": {"model": InternalServerError},
        "503": {"model": ServiceUnavailable},
    },
)
async def ingest_players(
    source: str = Query("sport_players", description="Source mode: team_roster, sport_players, search"),
    season: int | None = Query(None, description="Season year"),
    team_id: int | None = Query(
        None,
        alias="teamId",
        description="Internal team ID required when source=team_roster and optional filter when source=sport_players",
    ),
    roster_type: str = Query("active", alias="rosterType", description="Roster type for team roster ingestion"),
    sport_id: int = Query(1, alias="sportId", description="Sport ID for sport_players mode"),
    query: str | None = Query(None, alias="q", description="Search text when source=search"),
    use_cases: dict = Depends(get_player_use_cases),
) -> JSONResponse:
    start_time = datetime.now()
    current_year = datetime.now().year
    normalized_source = source.strip().lower()
    if season is not None and (season < 1876 or season > current_year + 1):
        raise DomainExceptions.InvalidDataError(f"season must be between 1876 and {current_year + 1}")
    if team_id is not None and team_id <= 0:
        raise DomainExceptions.InvalidDataError("teamId must be a positive integer")
    if sport_id <= 0:
        raise DomainExceptions.InvalidDataError("sportId must be a positive integer")

    resolved_team_mlb_id: int | None = None
    if team_id is not None and normalized_source in {"team_roster", "sport_players"}:
        team = await use_cases["get_team"].execute(team_id=team_id)
        resolved_team_mlb_id = team.mlb_id

    try:
        players = await use_cases["ingest_players_by_source"].execute(
            source=source,
            season=season,
            team_mlb_id=resolved_team_mlb_id,
            roster_type=roster_type,
            sport_id=sport_id,
            query=query,
        )
    except ValueError as error:
        raise DomainExceptions.InvalidDataError(str(error)) from error
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    ingestion_result = DataIngestionResultDTO(
        operation="player_ingestion",
        records_processed=len(players),
        records_created=len(players),
        records_updated=0,
        errors=[],
        duration_seconds=duration,
        timestamp=end_time,
    )
    return ResponseHandler.created(
        data={
            "ingestion_summary": ingestion_result,
            "sample_players": to_player_payload_list(players[:5]),
        },
        message=f"Successfully ingested {len(players)} players from source={source}",
    )

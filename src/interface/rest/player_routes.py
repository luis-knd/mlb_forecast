from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from application.ports.cache import CachePort
from application.use_cases.player_use_cases import (
    GetPlayerByMlbIdUseCase,
    GetPlayerUseCase,
    IngestPlayersBySourceUseCase,
    ListPlayersUseCase,
)
from application.use_cases.team_use_cases import GetTeamUseCase
from infrastructure.cache.cache_provider import get_cache_adapter
from infrastructure.db.database import get_db
from infrastructure.db.repositories.cached_team_repository import CachedTeamRepository
from infrastructure.db.repositories.player_repository import PlayerRepository
from infrastructure.db.repositories.team_repository import TeamRepository
from infrastructure.mlb_api.adapter import MLBApiAdapter
from interface.rest.adapters.hydration import (
    PLAYER_ALLOWED_INCLUDES,
    parse_include_selection,
    to_player_response_payload,
    to_player_response_payload_list,
)
from interface.rest.adapters.mappers import to_player_payload_list
from interface.rest.exception_handlers import DomainExceptions
from interface.rest.generated.models.models import (
    BadRequest,
    DataIngestionResponse,
    DataIngestionResultDTO,
    InternalServerError,
    NotFound,
    PlayerDetailResponse,
    PlayerListResponse,
    ServiceUnavailable,
    UnprocessableEntity,
)
from interface.rest.response_handler import ResponseHandler

router = APIRouter()


def _validate_ingest_players_request(
    source: str,
    season: int | None,
    team_id: int | None,
    sport_id: int,
) -> str:
    current_year = datetime.now().year
    normalized_source = source.strip().lower()

    if season is not None and (season < 1876 or season > current_year + 1):
        raise DomainExceptions.InvalidDataError(f"season must be between 1876 and {current_year + 1}")
    if team_id is not None and team_id <= 0:
        raise DomainExceptions.InvalidDataError("teamId must be a positive integer")
    if sport_id <= 0:
        raise DomainExceptions.InvalidDataError("sportId must be a positive integer")

    return normalized_source


async def _resolve_team_mlb_id_for_ingestion(
    normalized_source: str,
    team_id: int | None,
    use_cases: dict,
) -> int | None:
    if team_id is None or normalized_source not in {"team_roster", "sport_players"}:
        return None

    team = await use_cases["get_team"].execute(team_id=team_id)
    return team.mlb_id


async def _ingest_players_from_source(
    source: str,
    season: int | None,
    team_mlb_id: int | None,
    roster_type: str,
    sport_id: int,
    query: str | None,
    use_cases: dict,
):
    try:
        return await use_cases["ingest_players_by_source"].execute(
            source=source,
            season=season,
            team_mlb_id=team_mlb_id,
            roster_type=roster_type,
            sport_id=sport_id,
            query=query,
        )
    except ValueError as error:
        raise DomainExceptions.InvalidDataError(str(error)) from error


def _build_ingestion_result(players: list[object], start_time: datetime) -> DataIngestionResultDTO:
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    return DataIngestionResultDTO(
        operation="player_ingestion",
        records_processed=len(players),
        records_created=len(players),
        records_updated=0,
        errors=[],
        duration_seconds=duration,
        timestamp=end_time,
    )


def get_player_use_cases(
    db: Annotated[Session, Depends(get_db)],
    cache: Annotated[CachePort, Depends(get_cache_adapter)],
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
    team_id: Annotated[int | None, Query(description="Filter by internal team ID")] = None,
    position: Annotated[str | None, Query(description="Filter by position abbreviation")] = None,
    name: Annotated[str | None, Query(description="Filter by player name")] = None,
    active: Annotated[bool | None, Query(description="Filter by active status")] = None,
    limit: Annotated[int, Query(ge=1, le=200, description="Maximum number of players to return")] = 50,
    offset: Annotated[int, Query(ge=0, description="Pagination offset")] = 0,
    include: Annotated[
        list[str] | None,
        Query(
            description=(
                "Relations to hydrate. Supports comma-separated values and dot notation, "
                "e.g. current_team or current_team.venue_name"
            ),
        ),
    ] = None,
    *,
    use_cases: Annotated[dict, Depends(get_player_use_cases)],
) -> JSONResponse:
    if team_id is not None and team_id <= 0:
        raise DomainExceptions.InvalidDataError("team_id must be a positive integer")

    include_selection = parse_include_selection(include, PLAYER_ALLOWED_INCLUDES)

    players = await use_cases["list_players"].execute(
        team_id=team_id,
        position=position,
        name=name,
        active=active,
        limit=limit,
        offset=offset,
    )

    players_payload = to_player_response_payload_list(players, include_selection)
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
    player_id: Annotated[int, Path(description="MLB personId")],
    include: Annotated[
        list[str] | None,
        Query(
            description=(
                "Relations to hydrate. Supports comma-separated values and dot notation, "
                "e.g. current_team or current_team.venue_name"
            ),
        ),
    ] = None,
    *,
    use_cases: Annotated[dict, Depends(get_player_use_cases)],
) -> JSONResponse:
    if player_id <= 0:
        raise DomainExceptions.InvalidDataError("player_id must be a positive integer")

    include_selection = parse_include_selection(include, PLAYER_ALLOWED_INCLUDES)

    player = await use_cases["get_player_by_mlb_id"].execute(mlb_player_id=player_id)
    if not player:
        raise DomainExceptions.PlayerNotFoundError(player_id)

    return ResponseHandler.success(
        data=to_player_response_payload(player, include_selection),
        message=f"Player {player.full_name()} retrieved successfully",
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
    source: Annotated[str, Query(description="Source mode: team_roster, sport_players, search")] = "sport_players",
    season: Annotated[int | None, Query(description="Season year")] = None,
    team_id: Annotated[
        int | None,
        Query(
            alias="teamId",
            description=(
                "Internal team ID required when source=team_roster and optional filter when source=sport_players"
            ),
        ),
    ] = None,
    roster_type: Annotated[
        str,
        Query(alias="rosterType", description="Roster type for team roster ingestion"),
    ] = "active",
    sport_id: Annotated[int, Query(alias="sportId", description="Sport ID for sport_players mode")] = 1,
    query: Annotated[str | None, Query(alias="q", description="Search text when source=search")] = None,
    *,
    use_cases: Annotated[dict, Depends(get_player_use_cases)],
) -> JSONResponse:
    start_time = datetime.now()
    normalized_source = _validate_ingest_players_request(source, season, team_id, sport_id)
    resolved_team_mlb_id = await _resolve_team_mlb_id_for_ingestion(normalized_source, team_id, use_cases)
    players = await _ingest_players_from_source(
        source=source,
        season=season,
        team_mlb_id=resolved_team_mlb_id,
        roster_type=roster_type,
        sport_id=sport_id,
        query=query,
        use_cases=use_cases,
    )
    ingestion_result = _build_ingestion_result(players, start_time)

    return ResponseHandler.created(
        data={
            "ingestion_summary": ingestion_result,
            "sample_players": to_player_payload_list(players[:5]),
        },
        message=f"Successfully ingested {len(players)} players from source={source}",
    )

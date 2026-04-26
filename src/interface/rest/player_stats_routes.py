"""
REST routes for persisted player stats retrieval and ingestion.
"""

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from application.ports.cache import CachePort
from application.use_cases.player_stats_ingestion_use_cases import (
    IngestPlayerSeasonStatsUseCase,
    IngestPlayerStatsHistoryUseCase,
)
from application.use_cases.player_stats_read_use_cases import (
    GetPersistedPlayerCareerStatsUseCase,
    GetPersistedPlayerGameLogsUseCase,
    GetPersistedPlayerSeasonStatsUseCase,
    GetPersistedPlayerStatSplitsUseCase,
    GetPersistedPlayerYearByYearStatsUseCase,
)
from application.use_cases.player_use_cases import GetPlayerUseCase
from infrastructure.cache.cache_provider import get_cache_adapter
from infrastructure.db.database import get_db
from infrastructure.db.repositories.player_repository import PlayerRepository
from infrastructure.db.repositories.player_stats_repository import PlayerStatsRepository
from infrastructure.db.repositories.team_repository import TeamRepository
from infrastructure.mlb_api.adapter import MLBApiAdapter
from interface.rest.adapters.player_stats_mappers import to_group_collection_payload, to_history_collection_payload
from interface.rest.exception_handlers import DomainExceptions
from interface.rest.generated.models.models import (
    BadRequest,
    InternalServerError,
    NotFound,
    PlayerStatsAggregateResponse,
    PlayerStatsHistoryResponse,
    PlayerStatsIngestionResponse,
    ServiceUnavailable,
    UnprocessableEntity,
)
from interface.rest.response_handler import ResponseHandler

router = APIRouter()
MIN_SUPPORTED_SEASON = 1876


def get_persisted_player_stats_use_cases(
    db: Annotated[Session, Depends(get_db)],
    cache: Annotated[CachePort, Depends(get_cache_adapter)],
) -> dict[str, Any]:
    player_repository = PlayerRepository(db)
    team_repository = TeamRepository(db)
    player_stats_repository = PlayerStatsRepository(db)
    mlb_api_adapter = MLBApiAdapter()

    return {
        "get_player": GetPlayerUseCase(player_repository, cache),
        "get_season_stats": GetPersistedPlayerSeasonStatsUseCase(player_stats_repository, cache),
        "get_career_stats": GetPersistedPlayerCareerStatsUseCase(player_stats_repository, cache),
        "get_year_by_year_stats": GetPersistedPlayerYearByYearStatsUseCase(player_stats_repository, cache),
        "get_game_logs": GetPersistedPlayerGameLogsUseCase(player_stats_repository, cache),
        "get_stat_splits": GetPersistedPlayerStatSplitsUseCase(player_stats_repository, cache),
        "ingest_season_stats": IngestPlayerSeasonStatsUseCase(
            player_repository,
            team_repository,
            player_stats_repository,
            mlb_api_adapter,
            cache,
        ),
        "ingest_history_stats": IngestPlayerStatsHistoryUseCase(
            player_repository,
            team_repository,
            player_stats_repository,
            mlb_api_adapter,
            cache,
        ),
    }


def _validate_player_id(player_id: int) -> None:
    if player_id <= 0:
        raise DomainExceptions.InvalidDataError("player_id must be a positive integer")


async def _load_player_or_raise(player_id: int, use_cases: dict[str, Any]) -> None:
    _validate_player_id(player_id)
    player = await use_cases["get_player"].execute(player_id=player_id)
    if player is None:
        raise DomainExceptions.PlayerNotFoundError(player_id)


def _normalize_empty_records(records: list[Any], resource_name: str, player_id: int) -> JSONResponse | None:
    if records:
        return None
    return ResponseHandler.not_found(resource_name, player_id)


def _translate_validation_error(error: ValueError) -> None:
    raise DomainExceptions.InvalidDataError(str(error)) from error


@router.get(
    "/players/{player_id}/stats/season",
    tags=["Players", "Stats"],
    response_model=PlayerStatsAggregateResponse,
    responses={
        "400": {"model": BadRequest},
        "404": {"model": NotFound},
        "422": {"model": UnprocessableEntity},
        "500": {"model": InternalServerError},
        "503": {"model": ServiceUnavailable},
    },
)
async def get_persisted_player_season_stats(
    player_id: Annotated[int, Path(description="Internal player ID")],
    season: Annotated[int, Query(ge=MIN_SUPPORTED_SEASON, description="Season year")],
    group: Annotated[str, Query(description="Stats group to retrieve from persisted data")] = "all",
    game_type: Annotated[str | None, Query(alias="gameType", description="Persisted game type code")] = "R",
    *,
    use_cases: Annotated[dict[str, Any], Depends(get_persisted_player_stats_use_cases)],
) -> JSONResponse:
    await _load_player_or_raise(player_id, use_cases)
    try:
        records = await use_cases["get_season_stats"].execute(player_id, season, group, game_type)
    except ValueError as error:
        _translate_validation_error(error)
    not_found_response = _normalize_empty_records(records, "Player stats", player_id)
    if not_found_response is not None:
        return not_found_response
    normalized_game_type = records[0].game_type if records else (game_type or "R").upper()
    return ResponseHandler.success(
        data=to_group_collection_payload(
            player_id=player_id,
            stats="season",
            group=group.strip().lower(),
            season=season,
            game_type=normalized_game_type,
            records=records,
        ),
        message=f"Persisted player season stats retrieved successfully for season {season}",
    )


@router.get(
    "/players/{player_id}/stats/career",
    tags=["Players", "Stats"],
    response_model=PlayerStatsAggregateResponse,
    responses={
        "400": {"model": BadRequest},
        "404": {"model": NotFound},
        "422": {"model": UnprocessableEntity},
        "500": {"model": InternalServerError},
        "503": {"model": ServiceUnavailable},
    },
)
async def get_persisted_player_career_stats(
    player_id: Annotated[int, Path(description="Internal player ID")],
    group: Annotated[str, Query(description="Stats group to retrieve from persisted data")] = "all",
    game_type: Annotated[str | None, Query(alias="gameType", description="Persisted game type code")] = "R",
    *,
    use_cases: Annotated[dict[str, Any], Depends(get_persisted_player_stats_use_cases)],
) -> JSONResponse:
    await _load_player_or_raise(player_id, use_cases)
    try:
        records = await use_cases["get_career_stats"].execute(player_id, group, game_type)
    except ValueError as error:
        _translate_validation_error(error)
    not_found_response = _normalize_empty_records(records, "Player career stats", player_id)
    if not_found_response is not None:
        return not_found_response
    return ResponseHandler.success(
        data=to_group_collection_payload(
            player_id=player_id,
            stats="career",
            group=group.strip().lower(),
            game_type=records[0].game_type,
            records=records,
        ),
        message="Persisted player career stats retrieved successfully",
    )


@router.get(
    "/players/{player_id}/stats/year-by-year",
    tags=["Players", "Stats"],
    response_model=PlayerStatsAggregateResponse,
    responses={
        "400": {"model": BadRequest},
        "404": {"model": NotFound},
        "422": {"model": UnprocessableEntity},
        "500": {"model": InternalServerError},
        "503": {"model": ServiceUnavailable},
    },
)
async def get_persisted_player_year_by_year_stats(
    player_id: Annotated[int, Path(description="Internal player ID")],
    group: Annotated[str, Query(description="Stats group to retrieve from persisted data")] = "all",
    game_type: Annotated[str | None, Query(alias="gameType", description="Persisted game type code")] = "R",
    *,
    use_cases: Annotated[dict[str, Any], Depends(get_persisted_player_stats_use_cases)],
) -> JSONResponse:
    await _load_player_or_raise(player_id, use_cases)
    try:
        records = await use_cases["get_year_by_year_stats"].execute(player_id, group, game_type)
    except ValueError as error:
        _translate_validation_error(error)
    not_found_response = _normalize_empty_records(records, "Player year-by-year stats", player_id)
    if not_found_response is not None:
        return not_found_response
    return ResponseHandler.success(
        data=to_group_collection_payload(
            player_id=player_id,
            stats="yearByYear",
            group=group.strip().lower(),
            game_type=records[0].game_type,
            records=records,
        ),
        message="Persisted player year-by-year stats retrieved successfully",
    )


@router.get(
    "/players/{player_id}/stats/game-log",
    tags=["Players", "Stats"],
    response_model=PlayerStatsHistoryResponse,
    responses={
        "400": {"model": BadRequest},
        "404": {"model": NotFound},
        "422": {"model": UnprocessableEntity},
        "500": {"model": InternalServerError},
        "503": {"model": ServiceUnavailable},
    },
)
async def get_persisted_player_game_logs(
    player_id: Annotated[int, Path(description="Internal player ID")],
    season: Annotated[int, Query(ge=MIN_SUPPORTED_SEASON, description="Season year")],
    group: Annotated[str, Query(description="Stats group to retrieve from persisted data")] = "all",
    game_type: Annotated[str | None, Query(alias="gameType", description="Persisted game type code")] = "R",
    days_back: Annotated[
        int | None,
        Query(alias="daysBack", ge=1, description="Optional rolling window in days"),
    ] = None,
    limit: Annotated[int | None, Query(ge=1, le=500, description="Optional maximum records to return")] = None,
    *,
    use_cases: Annotated[dict[str, Any], Depends(get_persisted_player_stats_use_cases)],
) -> JSONResponse:
    await _load_player_or_raise(player_id, use_cases)
    try:
        records = await use_cases["get_game_logs"].execute(player_id, season, group, game_type, days_back, limit)
    except ValueError as error:
        _translate_validation_error(error)
    not_found_response = _normalize_empty_records(records, "Player game logs", player_id)
    if not_found_response is not None:
        return not_found_response
    normalized_game_type = records[0].game_type if records else (game_type or "R").upper()
    return ResponseHandler.success(
        data=to_history_collection_payload(
            player_id=player_id,
            stats="gameLog",
            group=group.strip().lower(),
            season=season,
            game_type=normalized_game_type,
            days_back=days_back,
            records=records,
        ),
        message="Persisted player game logs retrieved successfully",
    )


@router.get(
    "/players/{player_id}/stats/splits",
    tags=["Players", "Stats"],
    response_model=PlayerStatsHistoryResponse,
    responses={
        "400": {"model": BadRequest},
        "404": {"model": NotFound},
        "422": {"model": UnprocessableEntity},
        "500": {"model": InternalServerError},
        "503": {"model": ServiceUnavailable},
    },
)
async def get_persisted_player_stat_splits(
    player_id: Annotated[int, Path(description="Internal player ID")],
    season: Annotated[int, Query(ge=MIN_SUPPORTED_SEASON, description="Season year")],
    group: Annotated[str, Query(description="Stats group to retrieve from persisted data")] = "all",
    game_type: Annotated[str | None, Query(alias="gameType", description="Persisted game type code")] = "R",
    limit: Annotated[int | None, Query(ge=1, le=500, description="Optional maximum records to return")] = None,
    *,
    use_cases: Annotated[dict[str, Any], Depends(get_persisted_player_stats_use_cases)],
) -> JSONResponse:
    await _load_player_or_raise(player_id, use_cases)
    try:
        records = await use_cases["get_stat_splits"].execute(player_id, season, group, game_type, limit)
    except ValueError as error:
        _translate_validation_error(error)
    not_found_response = _normalize_empty_records(records, "Player stat splits", player_id)
    if not_found_response is not None:
        return not_found_response
    normalized_game_type = records[0].game_type if records else (game_type or "R").upper()
    return ResponseHandler.success(
        data=to_history_collection_payload(
            player_id=player_id,
            stats="statSplits",
            group=group.strip().lower(),
            season=season,
            game_type=normalized_game_type,
            records=records,
        ),
        message="Persisted player stat splits retrieved successfully",
    )


@router.post(
    "/data/ingest/player_stats/season",
    tags=["Players", "Stats", "Data Ingestion"],
    response_model=PlayerStatsIngestionResponse,
    status_code=201,
    responses={
        "400": {"model": BadRequest},
        "404": {"model": NotFound},
        "422": {"model": UnprocessableEntity},
        "500": {"model": InternalServerError},
        "503": {"model": ServiceUnavailable},
    },
)
async def ingest_persisted_player_season_stats(
    season: Annotated[int, Query(ge=MIN_SUPPORTED_SEASON, description="Season year to ingest")] = datetime.now().year,
    group: Annotated[str, Query(description="Stats group to ingest from StatsAPI")] = "all",
    game_type: Annotated[str | None, Query(alias="gameType", description="Persisted game type code")] = "R",
    player_id: Annotated[int | None, Query(alias="playerId", description="Internal player ID to ingest")] = None,
    team_id: Annotated[
        int | None,
        Query(alias="teamId", description="Internal team ID to ingest all roster players"),
    ] = None,
    force_refresh: Annotated[
        bool,
        Query(alias="forceRefresh", description="Force refresh even for historical seasons"),
    ] = False,
    *,
    use_cases: Annotated[dict[str, Any], Depends(get_persisted_player_stats_use_cases)],
) -> JSONResponse:
    try:
        ingestion_result = await use_cases["ingest_season_stats"].execute(
            season=season,
            group=group,
            game_type=game_type,
            player_id=player_id,
            team_id=team_id,
            force_refresh=force_refresh,
        )
    except ValueError as error:
        _translate_validation_error(error)
    return ResponseHandler.created(
        data=ingestion_result,
        message=f"Persisted player season stats ingested successfully for season {season}",
    )


@router.post(
    "/data/ingest/player_stats/history",
    tags=["Players", "Stats", "Data Ingestion"],
    response_model=PlayerStatsIngestionResponse,
    status_code=201,
    responses={
        "400": {"model": BadRequest},
        "404": {"model": NotFound},
        "422": {"model": UnprocessableEntity},
        "500": {"model": InternalServerError},
        "503": {"model": ServiceUnavailable},
    },
)
async def ingest_persisted_player_stats_history(
    season: Annotated[int, Query(ge=MIN_SUPPORTED_SEASON, description="Season year to ingest")] = datetime.now().year,
    group: Annotated[str, Query(description="Stats group to ingest from StatsAPI")] = "all",
    game_type: Annotated[str | None, Query(alias="gameType", description="Persisted game type code")] = "R",
    player_id: Annotated[int | None, Query(alias="playerId", description="Internal player ID to ingest")] = None,
    team_id: Annotated[
        int | None,
        Query(alias="teamId", description="Internal team ID to ingest all roster players"),
    ] = None,
    days_back: Annotated[
        int | None,
        Query(alias="daysBack", ge=1, description="Optional rolling daysBack for game logs"),
    ] = None,
    force_refresh: Annotated[
        bool,
        Query(alias="forceRefresh", description="Force refresh even for historical seasons"),
    ] = False,
    *,
    use_cases: Annotated[dict[str, Any], Depends(get_persisted_player_stats_use_cases)],
) -> JSONResponse:
    try:
        ingestion_result = await use_cases["ingest_history_stats"].execute(
            season=season,
            group=group,
            game_type=game_type,
            player_id=player_id,
            team_id=team_id,
            days_back=days_back,
            force_refresh=force_refresh,
        )
    except ValueError as error:
        _translate_validation_error(error)
    return ResponseHandler.created(
        data=ingestion_result,
        message=f"Persisted player history stats ingested successfully for season {season}",
    )

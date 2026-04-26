"""
REST API routes for data ingestion and machine learning operations.
"""

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from application.use_cases.game_use_cases import IngestGamesUseCase
from application.use_cases.team_stats_ingestion_use_cases import (
    IngestAllTeamStatsUseCase,
    IngestTeamCatchingStatsUseCase,
    IngestTeamFieldingStatsUseCase,
    IngestTeamHittingStatsUseCase,
    IngestTeamPitchingStatsUseCase,
)
from application.use_cases.team_use_cases import IngestTeamsUseCase
from infrastructure.cache.cache_provider import get_cache_adapter
from infrastructure.db.database import get_db
from infrastructure.db.repositories.cached_team_repository import CachedTeamRepository
from infrastructure.db.repositories.catching_stats_repository import CatchingStatsRepository
from infrastructure.db.repositories.fielding_stats_repository import FieldingStatsRepository
from infrastructure.db.repositories.game_repository import GameRepository
from infrastructure.db.repositories.hitting_stats_repository import HittingStatsRepository
from infrastructure.db.repositories.pitching_stats_repository import PitchingStatsRepository
from infrastructure.db.repositories.team_repository import TeamRepository
from infrastructure.mlb_api.adapter import MLBApiAdapter
from interface.rest.exception_handlers import DomainExceptions
from interface.rest.generated.models.models import (
    BadRequest,
    DataIngestionResultDTO,
    FullIngestionResponse,
    InternalServerError,
    MLRetrainResponse,
    NotFound,
    ServiceUnavailable,
    UnprocessableEntity,
)
from interface.rest.response_handler import ResponseHandler

router = APIRouter()
MIN_SUPPORTED_SEASON = 1900
MAX_DAYS_BACK = 30
MAX_SEASON_OFFSET = 1
StepExecutor = Callable[[], Awaitable[Any]]
INGESTION_STEP_ERRORS = (RuntimeError, ValueError, TypeError, OSError)


def get_data_ingestion_use_cases(db: Annotated[Session, Depends(get_db)]):
    """Get data ingestion use cases with dependencies."""
    # Repositories
    team_repository = TeamRepository(db)
    game_repository = GameRepository(db)
    hitting_stats_repository = HittingStatsRepository(db)
    pitching_stats_repository = PitchingStatsRepository(db)
    fielding_stats_repository = FieldingStatsRepository(db)
    catching_stats_repository = CatchingStatsRepository(db)

    # Adapters
    cache_adapter = get_cache_adapter()
    mlb_api_adapter = MLBApiAdapter()

    # Granular team stats use cases
    hitting_stats_use_case = IngestTeamHittingStatsUseCase(hitting_stats_repository, team_repository, mlb_api_adapter)
    pitching_stats_use_case = IngestTeamPitchingStatsUseCase(
        pitching_stats_repository, team_repository, mlb_api_adapter
    )
    fielding_stats_use_case = IngestTeamFieldingStatsUseCase(
        fielding_stats_repository, team_repository, mlb_api_adapter
    )
    catching_stats_use_case = IngestTeamCatchingStatsUseCase(
        catching_stats_repository, team_repository, mlb_api_adapter
    )

    # Composite use case for all team stats
    all_team_stats_use_case = IngestAllTeamStatsUseCase(
        hitting_stats_use_case,
        pitching_stats_use_case,
        fielding_stats_use_case,
        catching_stats_use_case,
    )

    # Use cached repository for teams
    cached_team_repository = CachedTeamRepository(team_repository, cache_adapter)

    return {
        "ingest_teams": IngestTeamsUseCase(cached_team_repository, mlb_api_adapter),
        "ingest_games": IngestGamesUseCase(game_repository, team_repository, mlb_api_adapter, cache_adapter),
        "ingest_all_team_stats": all_team_stats_use_case,
    }


def _validate_ingestion_params(season: int, days_back: int) -> None:
    current_year = datetime.now().year
    max_supported_season = current_year + MAX_SEASON_OFFSET
    if season < MIN_SUPPORTED_SEASON or season > max_supported_season:
        raise DomainExceptions.InvalidDataError(
            f"Season must be between {MIN_SUPPORTED_SEASON} and {max_supported_season}"
        )
    if days_back < 1 or days_back > MAX_DAYS_BACK:
        raise DomainExceptions.InvalidDataError(f"Days back must be between 1 and {MAX_DAYS_BACK}")


def _new_ingestion_results() -> dict[str, dict[str, bool | int | str | None]]:
    return {
        "teams": {"success": False, "count": 0, "error": None},
        "games": {"success": False, "count": 0, "error": None},
        "team_stats": {"success": False, "count": 0, "error": None},
    }


def _count_team_stats_payload(team_stats: Any) -> int:
    if not isinstance(team_stats, dict):
        return 0
    return sum(
        len(team_stats.get(section, []))
        for section in ("hitting_stats", "pitching_stats", "fielding_stats", "catching_stats")
    )


async def _run_ingestion_step(
    step_key: str,
    executor: StepExecutor,
    ingestion_results: dict[str, dict[str, bool | int | str | None]],
    errors: list[str],
    count_extractor: Callable[[Any], int] = len,
) -> int:
    try:
        result = await executor()
        count = count_extractor(result)
        ingestion_results[step_key]["success"] = True
        ingestion_results[step_key]["count"] = count
        return count
    except INGESTION_STEP_ERRORS as exc:
        ingestion_results[step_key]["error"] = str(exc)
        errors.append(f"{step_key.replace('_', ' ').title()} ingestion failed: {exc}")
        return 0


async def _collect_ingestion_results(
    use_cases: dict[str, Any],
    season: int,
    days_back: int,
) -> tuple[dict[str, dict[str, bool | int | str | None]], int, list[str]]:
    ingestion_results = _new_ingestion_results()
    errors: list[str] = []
    total_records = 0
    total_records += await _run_ingestion_step("teams", use_cases["ingest_teams"].execute, ingestion_results, errors)
    total_records += await _run_ingestion_step(
        "games",
        lambda: use_cases["ingest_games"].execute(days_back=days_back),
        ingestion_results,
        errors,
    )
    total_records += await _run_ingestion_step(
        "team_stats",
        lambda: use_cases["ingest_all_team_stats"].execute(season=season),
        ingestion_results,
        errors,
        _count_team_stats_payload,
    )
    return ingestion_results, total_records, errors


def _build_ingestion_response(
    season: int,
    start_time: datetime,
    ingestion_results: dict[str, dict[str, bool | int | str | None]],
    total_records: int,
    errors: list[str],
) -> JSONResponse:
    end_time = datetime.now()
    ingestion_summary = DataIngestionResultDTO(
        operation="full_data_ingestion",
        records_processed=total_records,
        records_created=total_records,
        records_updated=0,
        errors=errors,
        duration_seconds=(end_time - start_time).total_seconds(),
        timestamp=end_time,
    )
    overall_success = all(result["success"] for result in ingestion_results.values())
    if not overall_success and errors:
        raise DomainExceptions.ExternalServiceError("Data Ingestion", "; ".join(errors))
    return ResponseHandler.created(
        data={
            "overall_summary": ingestion_summary,
            "teams_ingested": ingestion_results["teams"]["count"],
            "games_ingested": ingestion_results["games"]["count"],
            "stats_ingested": ingestion_results["team_stats"]["count"],
            "breakdown": ingestion_results,
        },
        message=f"Full data ingestion completed successfully for season {season}",
    )


@router.post(
    "/data/ingest/full",
    tags=["Data Ingestion"],
    response_model=FullIngestionResponse,
    status_code=201,
    responses={
        "400": {"model": BadRequest},
        "404": {"model": NotFound},
        "422": {"model": UnprocessableEntity},
        "500": {"model": InternalServerError},
        "503": {"model": ServiceUnavailable},
    },
)
async def ingest_full_data(
    season: Annotated[int, Query(description="Season to ingest data for")] = datetime.now().year,
    days_back: Annotated[int, Query(le=30, description="Number of days back to ingest games for")] = 7,
    *,
    use_cases: Annotated[dict, Depends(get_data_ingestion_use_cases)],
) -> JSONResponse:
    """
    Handle the full data ingestion process for a given season.

    Fetches and processes data for teams, games, and team statistics. The process
    involves multiple steps, each of which can succeed or fail independently.

    Args:
        season: The season year for which data should be ingested
        days_back: The number of days back to ingest games for
        use_cases: Dependency providing use cases for data ingestion

    Returns:
        JSONResponse: Standardized response with full ingestion results

    Raises:
        DomainExceptions.InvalidDataError: If season or days_back is invalid
        DomainExceptions.ExternalServiceError: If MLB API is unavailable
    """
    _validate_ingestion_params(season, days_back)
    start_time = datetime.now()
    try:
        ingestion_results, total_records, errors = await _collect_ingestion_results(
            use_cases=use_cases,
            season=season,
            days_back=days_back,
        )
        return _build_ingestion_response(season, start_time, ingestion_results, total_records, errors)
    except Exception as e:
        if "MLB API" in str(e) or "api" in str(e).lower():
            raise DomainExceptions.ExternalServiceError("MLB API", str(e)) from e
        raise


@router.post("/ml/retrain", tags=["ML Model"], response_model=MLRetrainResponse)
async def retrain_ml_model():
    """
    Retrain the Machine Learning model with new data.

    Returns:
        Status message
    """
    # This is a placeholder that will be implemented with actual use cases
    return {"message": "Retrain ML model endpoint - To be implemented"}

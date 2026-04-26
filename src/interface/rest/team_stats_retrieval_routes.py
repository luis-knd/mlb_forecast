"""
REST API routes for team statistics retrieval operations.
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from application.ports.cache import CachePort
from application.use_cases.team_stats_use_cases import GetTeamStatsUseCase
from domain.value_objects.team_stats_category import TeamStatsCategory
from infrastructure.cache.cache_provider import get_cache_adapter
from infrastructure.db.database import get_db
from infrastructure.db.repositories.team_stats_repository import TeamStatsRepository
from interface.rest.adapters.mappers import to_team_stats_dto
from interface.rest.exception_handlers import DomainExceptions
from interface.rest.generated.models.models import (
    BadRequest,
    InternalServerError,
    NotFound,
    ServiceUnavailable,
    TeamSeasonStatsDetailResponse,
    UnprocessableEntity,
)
from interface.rest.response_handler import ResponseHandler

router = APIRouter()


def get_team_stats_use_cases(
    db: Annotated[Session, Depends(get_db)],
    cache_adapter: Annotated[CachePort, Depends(get_cache_adapter)],
):
    """Get team stats use cases with dependencies."""
    team_stats_repository = TeamStatsRepository(db)

    return {
        "get_team_stats": GetTeamStatsUseCase(team_stats_repository, cache_adapter),
    }


def _parse_season_year(season: str) -> int:
    try:
        return int(season)
    except (TypeError, ValueError) as error:
        raise HTTPException(status_code=422, detail="season must be an integer year") from error


def _validate_season_range(season_year: int) -> None:
    current_year = datetime.now().year
    max_historical_season = current_year - 30
    if max_historical_season <= season_year <= current_year:
        return
    raise DomainExceptions.InvalidDataError(f"Season must be between {max_historical_season} and {current_year}")


def _resolve_stats_category(category: str | None) -> TeamStatsCategory:
    normalized_category = category.strip().lower() if category else None
    if not normalized_category:
        return TeamStatsCategory.ALL
    try:
        return TeamStatsCategory(normalized_category)
    except ValueError as error:
        allowed_values = ", ".join(TeamStatsCategory.allowed_values())
        raise HTTPException(status_code=422, detail=f"category must be one of: {allowed_values}") from error


@router.get(
    "/teams/{team_id}/stats/{season}",
    response_model=TeamSeasonStatsDetailResponse,
    responses={
        "400": {"model": BadRequest},
        "404": {"model": NotFound},
        "422": {"model": UnprocessableEntity},
        "500": {"model": InternalServerError},
        "503": {"model": ServiceUnavailable},
    },
    tags=["Teams", "Stats"],
)
async def get_team_stats(
    team_id: Annotated[int, Path(description="The ID of the team to get stats for")],
    season: Annotated[str, Path(description="The season to get stats for")],
    category: Annotated[
        str | None,
        Query(
            description="Optional stats category filter. Defaults to `all`.",
            json_schema_extra={"enum": list(TeamStatsCategory.allowed_values())},
        ),
    ] = "all",
    *,
    use_cases: Annotated[dict, Depends(get_team_stats_use_cases)],
) -> JSONResponse:
    """
    Retrieve statistical data for a specific team for a given season.

    This endpoint fetches and provides detailed statistics related to a specific team ID
    and season. It employs dependency injection to fetch use cases and ensures proper
    error handling for various scenarios.

    Args:
        team_id: The ID of the team to get statistics for
        season: The season year to retrieve statistics for
        category: Optional statistics category filter
        use_cases: Dependency to retrieve the use cases related to retrieving team statistics

    Returns:
        JSONResponse: Standardized response with team statistics

    Raises:
        DomainExceptions.InvalidDataError: If team_id or season is invalid
        DomainExceptions.TeamNotFoundError: If team statistics are not found
    """
    # Validate inputs
    if team_id <= 0:
        raise DomainExceptions.InvalidDataError("Team ID must be a positive integer")

    season_year = _parse_season_year(season)
    _validate_season_range(season_year)
    resolved_category = _resolve_stats_category(category)
    try:
        get_team_stats_use_case = use_cases["get_team_stats"]
        team_stats = await get_team_stats_use_case.execute(
            team_id=team_id,
            season=season_year,
            category=resolved_category,
        )

        if not team_stats:
            raise DomainExceptions.TeamNotFoundError(team_id)

        team_stats_dto = to_team_stats_dto(team_stats)

        return ResponseHandler.success(
            data=team_stats_dto,
            message=f"Team statistics retrieved successfully for season {season_year}",
        )

    except DomainExceptions.TeamNotFoundError:
        raise
    except Exception as e:
        raise DomainExceptions.ExternalServiceError("Database", str(e)) from e

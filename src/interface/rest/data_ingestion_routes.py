"""
REST API routes for data ingestion and machine learning operations.
"""

from datetime import datetime
from typing import Dict, Union

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from src.application.use_cases.game_use_cases import IngestGamesUseCase
from src.application.use_cases.team_stats_ingestion_use_cases import (
    IngestAllTeamStatsUseCase,
    IngestTeamCatchingStatsUseCase,
    IngestTeamFieldingStatsUseCase,
    IngestTeamHittingStatsUseCase,
    IngestTeamPitchingStatsUseCase,
)
from src.application.use_cases.team_use_cases import IngestTeamsUseCase
from src.infrastructure.cache.cache_provider import get_cache_adapter
from src.infrastructure.db.database import get_db
from src.infrastructure.db.repositories.cached_team_repository import CachedTeamRepository
from src.infrastructure.db.repositories.catching_stats_repository import CatchingStatsRepository
from src.infrastructure.db.repositories.fielding_stats_repository import FieldingStatsRepository
from src.infrastructure.db.repositories.game_repository import GameRepository
from src.infrastructure.db.repositories.hitting_stats_repository import HittingStatsRepository
from src.infrastructure.db.repositories.pitching_stats_repository import PitchingStatsRepository
from src.infrastructure.db.repositories.team_repository import TeamRepository
from src.infrastructure.mlb_api.adapter import MLBApiAdapter
from src.interface.rest.exception_handlers import DomainExceptions
from src.interface.rest.generated.models.models import (
    BadRequest,
    DataIngestionResultDTO,
    FullIngestionResponse,
    InternalServerError,
    NotFound,
    ServiceUnavailable,
    UnprocessableEntity,
)
from src.interface.rest.response_handler import ResponseHandler

router = APIRouter()


def get_data_ingestion_use_cases(db: Session = Depends(get_db)):
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
    season: int = Query(datetime.now().year, description="Season to ingest data for"),
    days_back: int = Query(7, le=30, description="Number of days back to ingest games for"),
    use_cases: Dict = Depends(get_data_ingestion_use_cases),
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
    # Validate inputs
    current_year = datetime.now().year
    if season < 1900 or season > current_year + 1:
        raise DomainExceptions.InvalidDataError(f"Season must be between 1900 and {current_year + 1}")

    if days_back < 1 or days_back > 30:
        raise DomainExceptions.InvalidDataError("Days back must be between 1 and 30")

    start_time = datetime.now()

    # Define proper type structure for ingestion results
    ingestion_results: Dict[str, Dict[str, Union[bool, int, str, None]]] = {
        "teams": {"success": False, "count": 0, "error": None},
        "games": {"success": False, "count": 0, "error": None},
        "team_stats": {"success": False, "count": 0, "error": None},
    }

    total_records = 0
    errors = []

    try:
        # Step 1: Ingest teams
        try:
            ingest_teams_use_case = use_cases["ingest_teams"]
            teams = await ingest_teams_use_case.execute()
            ingestion_results["teams"]["success"] = True
            ingestion_results["teams"]["count"] = len(teams)
            total_records += len(teams)
        except Exception as e:
            ingestion_results["teams"]["error"] = str(e)
            errors.append(f"Teams ingestion failed: {str(e)}")

        # Step 2: Ingest games
        try:
            ingest_games_use_case = use_cases["ingest_games"]
            games = await ingest_games_use_case.execute(days_back=days_back)
            ingestion_results["games"]["success"] = True
            ingestion_results["games"]["count"] = len(games)
            total_records += len(games)
        except Exception as e:
            ingestion_results["games"]["error"] = str(e)
            errors.append(f"Games ingestion failed: {str(e)}")

        # Step 3: Ingest team stats
        try:
            ingest_all_team_stats_use_case = use_cases["ingest_all_team_stats"]
            team_stats = await ingest_all_team_stats_use_case.execute(season=season)

            stats_count = (
                len(team_stats.get("hitting_stats", []))
                + len(team_stats.get("pitching_stats", []))
                + len(team_stats.get("fielding_stats", []))
                + len(team_stats.get("catching_stats", []))
            )

            ingestion_results["team_stats"]["success"] = True
            ingestion_results["team_stats"]["count"] = stats_count
            total_records += stats_count
        except Exception as e:
            ingestion_results["team_stats"]["error"] = str(e)
            errors.append(f"Team stats ingestion failed: {str(e)}")

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Create overall summary
        ingestion_summary = DataIngestionResultDTO(
            operation="full_data_ingestion",
            records_processed=total_records,
            records_created=total_records,  # Simplified assumption
            records_updated=0,
            errors=errors,
            duration_seconds=duration,
            timestamp=end_time,
        )

        # Determine overall success
        overall_success = all(result["success"] for result in ingestion_results.values())

        if not overall_success and errors:
            # If there are critical errors, raise an exception
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

    except Exception as e:
        if "MLB API" in str(e) or "api" in str(e).lower():
            raise DomainExceptions.ExternalServiceError("MLB API", str(e))
        raise


@router.post("/ml/retrain", tags=["ML Model"])
async def retrain_ml_model():
    """
    Retrain the Machine Learning model with new data.

    Returns:
        Status message
    """
    # This is a placeholder that will be implemented with actual use cases
    return {"message": "Retrain ML model endpoint - To be implemented"}

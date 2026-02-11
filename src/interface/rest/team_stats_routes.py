"""
REST API routes for team statistics operations.

All handlers return standardized envelopes via ResponseHandler to keep
responses consistent with the API contract.
"""

from datetime import datetime
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, Query

from src.application.use_cases.team_stats_ingestion_use_cases import (
    IngestAllTeamStatsUseCase,
    IngestTeamCatchingStatsUseCase,
    IngestTeamFieldingStatsUseCase,
    IngestTeamHittingStatsUseCase,
    IngestTeamPitchingStatsUseCase,
)
from src.infrastructure.db.database import get_db
from src.infrastructure.db.repositories.catching_stats_repository import CatchingStatsRepository
from src.infrastructure.db.repositories.fielding_stats_repository import FieldingStatsRepository
from src.infrastructure.db.repositories.hitting_stats_repository import HittingStatsRepository
from src.infrastructure.db.repositories.pitching_stats_repository import PitchingStatsRepository
from src.infrastructure.db.repositories.team_repository import TeamRepository
from src.infrastructure.mlb_api.adapter import MLBApiAdapter
from src.interface.rest.generated.models.models import (
    BadRequest,
    InternalServerError,
    NotFound,
    ServiceUnavailable,
    TeamStatsIngestionResponse,
    UnprocessableEntity,
)
from src.interface.rest.response_handler import ResponseHandler

router = APIRouter()


def get_team_stats_ingestion_use_cases(db=Depends(get_db)):
    """Get team stats ingestion use cases with dependencies."""
    # Repositories
    team_repository = TeamRepository(db)
    hitting_stats_repository = HittingStatsRepository(db)
    pitching_stats_repository = PitchingStatsRepository(db)
    fielding_stats_repository = FieldingStatsRepository(db)
    catching_stats_repository = CatchingStatsRepository(db)

    # Adapters
    mlb_api = MLBApiAdapter()

    # Use cases
    hitting_stats_use_case = IngestTeamHittingStatsUseCase(hitting_stats_repository, team_repository, mlb_api)
    pitching_stats_use_case = IngestTeamPitchingStatsUseCase(pitching_stats_repository, team_repository, mlb_api)
    fielding_stats_use_case = IngestTeamFieldingStatsUseCase(fielding_stats_repository, team_repository, mlb_api)
    catching_stats_use_case = IngestTeamCatchingStatsUseCase(catching_stats_repository, team_repository, mlb_api)
    all_stats_use_case = IngestAllTeamStatsUseCase(
        hitting_stats_use_case,
        pitching_stats_use_case,
        fielding_stats_use_case,
        catching_stats_use_case,
    )

    return {
        "ingest_hitting_stats": hitting_stats_use_case,
        "ingest_pitching_stats": pitching_stats_use_case,
        "ingest_fielding_stats": fielding_stats_use_case,
        "ingest_catching_stats": catching_stats_use_case,
        "ingest_all_stats": all_stats_use_case,
    }


@router.post(
    "/data/ingest/team_stats",
    tags=["Teams", "Stats", "Data Ingestion"],
    response_model=TeamStatsIngestionResponse,
    status_code=201,
    responses={
        "201": {"model": TeamStatsIngestionResponse},
        "400": {"model": BadRequest},
        "404": {"model": NotFound},
        "422": {"model": UnprocessableEntity},
        "500": {"model": InternalServerError},
        "503": {"model": ServiceUnavailable},
    },
)
async def ingest_all_team_stats(
    season: int = Query(datetime.now().year, description="Season to ingest team statistics for"),
    use_cases: Dict = Depends(get_team_stats_ingestion_use_cases),
):
    """
    Ingest all team statistics data from the MLB API for a specific season.

    This endpoint allows for the ingestion of all team statistics (hitting, pitching, fielding, catching)
    from the MLB API for a given season. It uses the IngestAllTeamStatsUseCase to fetch and store
    statistics for all teams in the specified season.

    Parameters:
        season (int): The season year to ingest statistics for. Defaults to the current year.
        use_cases (Dict): Dependency-injected dictionary containing team stats ingestion use cases.

    Returns:
        dict: A dictionary containing success status, message, and data about the ingested
        team statistics including the count and season.

    Raises:
        HTTPException: If an error occurs during the team statistics ingestion process,
        an HTTP 500 status code is raised with an error message.
    """
    try:
        # Get the use case
        ingest_all_stats_use_case = use_cases["ingest_all_stats"]

        # Execute the use case
        ingested_stats = await ingest_all_stats_use_case.execute(season=season)

        data = {
            "hitting_stats_count": len(ingested_stats["hitting_stats"]),
            "pitching_stats_count": len(ingested_stats["pitching_stats"]),
            "fielding_stats_count": len(ingested_stats["fielding_stats"]),
            "catching_stats_count": len(ingested_stats["catching_stats"]),
            "season": season,
        }

        return ResponseHandler.created(
            data=data,
            message=f"All team statistics ingested successfully for season {season}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error ingesting team statistics: {str(e)}")


@router.post(
    "/data/ingest/team_stats/hitting",
    tags=["Teams", "Stats", "Data Ingestion"],
    response_model=TeamStatsIngestionResponse,
    status_code=201,
    responses={
        "201": {"model": TeamStatsIngestionResponse},
        "400": {"model": BadRequest},
        "404": {"model": NotFound},
        "422": {"model": UnprocessableEntity},
        "500": {"model": InternalServerError},
        "503": {"model": ServiceUnavailable},
    },
)
async def ingest_team_hitting_stats(
    season: int = Query(datetime.now().year, description="Season to ingest team hitting statistics for"),
    use_cases: Dict = Depends(get_team_stats_ingestion_use_cases),
):
    """
    Ingest team hitting statistics data from the MLB API for a specific season.

    This endpoint allows for the ingestion of team hitting statistics from the MLB API
    for a given season. It uses the IngestTeamHittingStatsUseCase to fetch and store
    hitting statistics for all teams in the specified season.

    Parameters:
        season (int): The season year to ingest statistics for. Defaults to the current year.
        use_cases (Dict): Dependency-injected dictionary containing team stats ingestion use cases.

    Returns:
        dict: A dictionary containing success status, message, and data about the ingested
        team hitting statistics including the count and season.

    Raises:
        HTTPException: If an error occurs during the team hitting statistics ingestion process,
        an HTTP 500 status code is raised with an error message.
    """
    try:
        # Get the use case
        ingest_hitting_stats_use_case = use_cases["ingest_hitting_stats"]

        # Execute the use case
        ingested_stats = await ingest_hitting_stats_use_case.execute(season=season)

        return ResponseHandler.created(
            data={
                "hitting_stats_count": len(ingested_stats),
                "season": season,
            },
            message=f"Team hitting statistics ingested successfully for season {season}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error ingesting team hitting statistics: {str(e)}")


@router.post(
    "/data/ingest/team_stats/pitching",
    tags=["Teams", "Stats", "Data Ingestion"],
    response_model=TeamStatsIngestionResponse,
    status_code=201,
    responses={
        "201": {"model": TeamStatsIngestionResponse},
        "400": {"model": BadRequest},
        "404": {"model": NotFound},
        "422": {"model": UnprocessableEntity},
        "500": {"model": InternalServerError},
        "503": {"model": ServiceUnavailable},
    },
)
async def ingest_team_pitching_stats(
    season: int = Query(datetime.now().year, description="Season to ingest team pitching statistics for"),
    use_cases: Dict = Depends(get_team_stats_ingestion_use_cases),
):
    """
    Ingest team pitching statistics data from the MLB API for a specific season.

    This endpoint allows for the ingestion of team pitching statistics from the MLB API
    for a given season. It uses the IngestTeamPitchingStatsUseCase to fetch and store
    pitching statistics for all teams in the specified season.

    Parameters:
        season (int): The season year to ingest statistics for. Defaults to the current year.
        use_cases (Dict): Dependency-injected dictionary containing team stats ingestion use cases.

    Returns:
        dict: A dictionary containing success status, message, and data about the ingested
        team pitching statistics including the count and season.

    Raises:
        HTTPException: If an error occurs during the team pitching statistics ingestion process,
        an HTTP 500 status code is raised with an error message.
    """
    try:
        # Get the use case
        ingest_pitching_stats_use_case = use_cases["ingest_pitching_stats"]

        # Execute the use case
        ingested_stats = await ingest_pitching_stats_use_case.execute(season=season)

        return ResponseHandler.created(
            data={
                "pitching_stats_count": len(ingested_stats),
                "season": season,
            },
            message=f"Team pitching statistics ingested successfully for season {season}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error ingesting team pitching statistics: {str(e)}",
        )


@router.post(
    "/data/ingest/team_stats/fielding",
    tags=["Teams", "Stats", "Data Ingestion"],
    response_model=TeamStatsIngestionResponse,
    status_code=201,
    responses={
        "201": {"model": TeamStatsIngestionResponse},
        "400": {"model": BadRequest},
        "404": {"model": NotFound},
        "422": {"model": UnprocessableEntity},
        "500": {"model": InternalServerError},
        "503": {"model": ServiceUnavailable},
    },
)
async def ingest_team_fielding_stats(
    season: int = Query(datetime.now().year, description="Season to ingest team fielding statistics for"),
    use_cases: Dict = Depends(get_team_stats_ingestion_use_cases),
):
    """
    Ingest team fielding statistics data from the MLB API for a specific season.

    This endpoint allows for the ingestion of team fielding statistics from the MLB API
    for a given season. It uses the IngestTeamFieldingStatsUseCase to fetch and store
    fielding statistics for all teams in the specified season.

    Parameters:
        season (int): The season year to ingest statistics for. Defaults to the current year.
        use_cases (Dict): Dependency-injected dictionary containing team stats ingestion use cases.

    Returns:
        dict: A dictionary containing success status, message, and data about the ingested
        team fielding statistics including the count and season.

    Raises:
        HTTPException: If an error occurs during the team fielding statistics ingestion process,
        an HTTP 500 status code is raised with an error message.
    """
    try:
        # Get the use case
        ingest_fielding_stats_use_case = use_cases["ingest_fielding_stats"]

        # Execute the use case
        ingested_stats = await ingest_fielding_stats_use_case.execute(season=season)

        return ResponseHandler.created(
            data={
                "fielding_stats_count": len(ingested_stats),
                "season": season,
            },
            message=f"Team fielding statistics ingested successfully for season {season}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error ingesting team fielding statistics: {str(e)}",
        )


@router.post(
    "/data/ingest/team_stats/catching",
    tags=["Teams", "Stats", "Data Ingestion"],
    response_model=TeamStatsIngestionResponse,
    status_code=201,
    responses={
        "201": {"model": TeamStatsIngestionResponse},
        "400": {"model": BadRequest},
        "404": {"model": NotFound},
        "422": {"model": UnprocessableEntity},
        "500": {"model": InternalServerError},
        "503": {"model": ServiceUnavailable},
    },
)
async def ingest_team_catching_stats(
    season: int = Query(datetime.now().year, description="Season to ingest team catching statistics for"),
    use_cases: Dict = Depends(get_team_stats_ingestion_use_cases),
):
    """
    Ingest team catching statistics data from the MLB API for a specific season.

    This endpoint allows for the ingestion of team catching statistics from the MLB API
    for a given season. It uses the IngestTeamCatchingStatsUseCase to fetch and store
    catching statistics for all teams in the specified season.

    Parameters:
        season (int): The season year to ingest statistics for. Defaults to the current year.
        use_cases (Dict): Dependency-injected dictionary containing team stats ingestion use cases.

    Returns:
        dict: A dictionary containing success status, message, and data about the ingested
        team catching statistics including the count and season.

    Raises:
        HTTPException: If an error occurs during the team catching statistics ingestion process,
        an HTTP 500 status code is raised with an error message.
    """
    try:
        # Get the use case
        ingest_catching_stats_use_case = use_cases["ingest_catching_stats"]

        # Execute the use case
        ingested_stats = await ingest_catching_stats_use_case.execute(season=season)

        return ResponseHandler.created(
            data={
                "catching_stats_count": len(ingested_stats),
                "season": season,
            },
            message=f"Team catching statistics ingested successfully for season {season}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error ingesting team catching statistics: {str(e)}",
        )

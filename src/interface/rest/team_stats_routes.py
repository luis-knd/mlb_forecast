"""REST API routes for team statistics ingestion."""

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from application.use_cases.team_stats_ingestion_use_cases import (
    IngestAllTeamStatsUseCase,
    IngestTeamCatchingStatsUseCase,
    IngestTeamFieldingStatsUseCase,
    IngestTeamHittingStatsUseCase,
    IngestTeamPitchingStatsUseCase,
)
from infrastructure.db.database import get_db
from infrastructure.db.repositories.catching_stats_repository import CatchingStatsRepository
from infrastructure.db.repositories.fielding_stats_repository import FieldingStatsRepository
from infrastructure.db.repositories.hitting_stats_repository import HittingStatsRepository
from infrastructure.db.repositories.pitching_stats_repository import PitchingStatsRepository
from infrastructure.db.repositories.team_repository import TeamRepository
from infrastructure.mlb_api.adapter import MLBApiAdapter
from interface.rest.generated.models.models import (
    BadRequest,
    InternalServerError,
    NotFound,
    ServiceUnavailable,
    TeamStatsIngestionResponse,
    UnprocessableEntity,
)
from interface.rest.response_handler import ResponseHandler

router = APIRouter()


def get_team_stats_ingestion_use_cases(db: Annotated[Session, Depends(get_db)]) -> dict[str, Any]:
    """Create team statistics ingestion use cases."""
    team_repository = TeamRepository(db)
    hitting_stats_repository = HittingStatsRepository(db)
    pitching_stats_repository = PitchingStatsRepository(db)
    fielding_stats_repository = FieldingStatsRepository(db)
    catching_stats_repository = CatchingStatsRepository(db)
    mlb_api = MLBApiAdapter()

    hitting_stats_use_case = IngestTeamHittingStatsUseCase(
        hitting_stats_repository,
        team_repository,
        mlb_api,
    )
    pitching_stats_use_case = IngestTeamPitchingStatsUseCase(
        pitching_stats_repository,
        team_repository,
        mlb_api,
    )
    fielding_stats_use_case = IngestTeamFieldingStatsUseCase(
        fielding_stats_repository,
        team_repository,
        mlb_api,
    )
    catching_stats_use_case = IngestTeamCatchingStatsUseCase(
        catching_stats_repository,
        team_repository,
        mlb_api,
    )
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
    season: Annotated[int, Query(description="Season year to ingest all team statistics for.")] = datetime.now().year,
    *,
    use_cases: Annotated[dict[str, Any], Depends(get_team_stats_ingestion_use_cases)],
):
    """Ingest all team statistics for a season."""
    try:
        ingest_all_stats_use_case = use_cases["ingest_all_stats"]
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
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Error ingesting team statistics: {error}",
        ) from error


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
    season: Annotated[int, Query(description="Season year to ingest team hitting statistics for.")] = (
        datetime.now().year
    ),
    *,
    use_cases: Annotated[dict[str, Any], Depends(get_team_stats_ingestion_use_cases)],
):
    """Ingest team hitting statistics for a season."""
    try:
        ingest_hitting_stats_use_case = use_cases["ingest_hitting_stats"]
        ingested_stats = await ingest_hitting_stats_use_case.execute(season=season)

        return ResponseHandler.created(
            data={
                "hitting_stats_count": len(ingested_stats),
                "season": season,
            },
            message=(f"Team hitting statistics ingested successfully for season {season}"),
        )
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Error ingesting team hitting statistics: {error}",
        ) from error


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
    season: Annotated[int, Query(description="Season year to ingest team pitching statistics for.")] = (
        datetime.now().year
    ),
    *,
    use_cases: Annotated[dict[str, Any], Depends(get_team_stats_ingestion_use_cases)],
):
    """Ingest team pitching statistics for a season."""
    try:
        ingest_pitching_stats_use_case = use_cases["ingest_pitching_stats"]
        ingested_stats = await ingest_pitching_stats_use_case.execute(season=season)

        return ResponseHandler.created(
            data={
                "pitching_stats_count": len(ingested_stats),
                "season": season,
            },
            message=(f"Team pitching statistics ingested successfully for season {season}"),
        )
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Error ingesting team pitching statistics: {error}",
        ) from error


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
    season: Annotated[int, Query(description="Season year to ingest team fielding statistics for.")] = (
        datetime.now().year
    ),
    *,
    use_cases: Annotated[dict[str, Any], Depends(get_team_stats_ingestion_use_cases)],
):
    """Ingest team fielding statistics for a season."""
    try:
        ingest_fielding_stats_use_case = use_cases["ingest_fielding_stats"]
        ingested_stats = await ingest_fielding_stats_use_case.execute(season=season)

        return ResponseHandler.created(
            data={
                "fielding_stats_count": len(ingested_stats),
                "season": season,
            },
            message=(f"Team fielding statistics ingested successfully for season {season}"),
        )
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Error ingesting team fielding statistics: {error}",
        ) from error


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
    season: Annotated[int, Query(description="Season year to ingest team catching statistics for.")] = (
        datetime.now().year
    ),
    *,
    use_cases: Annotated[dict[str, Any], Depends(get_team_stats_ingestion_use_cases)],
):
    """Ingest team catching statistics for a season."""
    try:
        ingest_catching_stats_use_case = use_cases["ingest_catching_stats"]
        ingested_stats = await ingest_catching_stats_use_case.execute(season=season)

        return ResponseHandler.created(
            data={
                "catching_stats_count": len(ingested_stats),
                "season": season,
            },
            message=(f"Team catching statistics ingested successfully for season {season}"),
        )
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Error ingesting team catching statistics: {error}",
        ) from error

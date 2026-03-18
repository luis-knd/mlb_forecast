from datetime import datetime

from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from application.ports.cache import CachePort
from application.use_cases.team_use_cases import GetTeamUseCase, IngestTeamsUseCase, ListTeamsUseCase
from infrastructure.cache.cache_provider import get_cache_adapter
from infrastructure.db.database import get_db
from infrastructure.db.repositories.cached_team_repository import CachedTeamRepository
from infrastructure.db.repositories.team_repository import TeamRepository
from infrastructure.mlb_api.adapter import MLBApiAdapter
from interface.rest.adapters.mappers import to_team_dto, to_team_dto_list
from interface.rest.exception_handlers import DomainExceptions
from interface.rest.generated.models.models import (
    BadRequest,
    DataIngestionResponse,
    DataIngestionResultDTO,
    InternalServerError,
    NotFound,
    ServiceUnavailable,
    TeamDetailResponse,
    TeamListResponse,
    UnprocessableEntity,
)
from interface.rest.response_handler import ResponseHandler

router = APIRouter()


def get_team_use_cases(
    db: Session = Depends(get_db),
    cache: CachePort = Depends(get_cache_adapter),
):
    team_repository = TeamRepository(db)
    # cache used from argument

    # Use cached repository decorator
    cached_team_repository = CachedTeamRepository(team_repository, cache)

    mlb_api_adapter = MLBApiAdapter()
    return {
        "list_teams": ListTeamsUseCase(cached_team_repository),
        "get_team": GetTeamUseCase(cached_team_repository),
        "ingest_teams": IngestTeamsUseCase(cached_team_repository, mlb_api_adapter),
    }


@router.get(
    "/teams",
    tags=["Teams"],
    response_model=TeamListResponse,
    responses={
        "400": {"model": BadRequest},
        "404": {"model": NotFound},
        "422": {"model": UnprocessableEntity},
        "500": {"model": InternalServerError},
        "503": {"model": ServiceUnavailable},
    },
)
async def list_teams(
    league: str | None = Query(None, description="Filter by league (e.g. American or National)"),
    division: str | None = Query(None, description="Filter by division (e.g. East, West, Central)"),
    use_cases: dict = Depends(get_team_use_cases),
) -> JSONResponse:
    teams = await use_cases["list_teams"].execute(league=league, division=division)
    teams_dto = to_team_dto_list(teams)
    return ResponseHandler.success(
        data=teams_dto,
        message=f"Retrieved {len(teams_dto)} teams successfully",
    )


@router.get(
    "/teams/{team_id}",
    tags=["Teams"],
    response_model=TeamDetailResponse,
    responses={
        "400": {"model": BadRequest},
        "404": {"model": NotFound},
        "422": {"model": UnprocessableEntity},
        "500": {"model": InternalServerError},
        "503": {"model": ServiceUnavailable},
    },
)
async def get_team(
    team_id: int = Path(..., description="The ID of the team to get"),
    use_cases: dict = Depends(get_team_use_cases),
) -> JSONResponse:
    team = await use_cases["get_team"].execute(team_id=team_id)
    team_dto = to_team_dto(team)
    return ResponseHandler.success(
        data=team_dto,
        message=f"Team {team_dto.name} retrieved successfully",
    )


@router.post(
    "/data/ingest/teams",
    tags=["Teams", "Data Ingestion"],
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
async def ingest_teams(
    use_cases: dict = Depends(get_team_use_cases),
) -> JSONResponse:
    start_time = datetime.now()
    try:
        ingested_teams = await use_cases["ingest_teams"].execute()
    except DomainExceptions.ExternalServiceError:
        raise
    except Exception as e:
        raise DomainExceptions.ExternalServiceError("MLB API", str(e))
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    teams_dto = to_team_dto_list(ingested_teams)
    ingestion_result = DataIngestionResultDTO(
        operation="team_ingestion",
        records_processed=len(ingested_teams),
        records_created=len(ingested_teams),
        records_updated=0,  # TODO I need to pass correctly the differences between existing and new records
        errors=[],
        duration_seconds=duration,
        timestamp=end_time,
    )

    return ResponseHandler.created(
        data={"ingestion_summary": ingestion_result, "sample_teams": teams_dto},
        message=f"Successfully ingested {len(ingested_teams)} teams",
    )

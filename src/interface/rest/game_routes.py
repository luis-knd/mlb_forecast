from datetime import datetime
from typing import Dict, Optional

from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from src.application.use_cases.game_use_cases import (
    GetGameUseCase,
    IngestGamesUseCase,
    ListGamesUseCase,
    ListUpcomingGamesUseCase,
)
from src.infrastructure.cache.cache_provider import get_cache_adapter
from src.infrastructure.db.database import get_db
from src.infrastructure.db.repositories.game_repository import GameRepository
from src.infrastructure.db.repositories.team_repository import TeamRepository
from src.infrastructure.mlb_api.adapter import MLBApiAdapter
from src.interface.rest.adapters.mappers import to_game_dto, to_game_dto_list
from src.interface.rest.exception_handlers import DomainExceptions
from src.interface.rest.generated.models.models import (
    BadRequest,
    DataIngestionResponse,
    DataIngestionResultDTO,
    GameDetailResponse,
    GameListResponse,
    InternalServerError,
    NotFound,
    ServiceUnavailable,
    UnprocessableEntity,
)
from src.interface.rest.response_handler import ResponseHandler

router = APIRouter()


def get_game_use_cases(db: Session = Depends(get_db)):
    """Get game use cases with dependencies."""
    game_repository = GameRepository(db)
    team_repository = TeamRepository(db)
    cache_adapter = get_cache_adapter()
    mlb_api_adapter = MLBApiAdapter()

    return {
        "list_games": ListGamesUseCase(game_repository, cache_adapter),
        "get_game": GetGameUseCase(game_repository, cache_adapter),
        "ingest_games": IngestGamesUseCase(game_repository, team_repository, mlb_api_adapter, cache_adapter),
        "list_upcoming_games": ListUpcomingGamesUseCase(game_repository, cache_adapter),
    }


@router.get(
    "/games",
    tags=["Games"],
    response_model=GameListResponse,
    responses={
        "400": {"model": BadRequest},
        "404": {"model": NotFound},
        "422": {"model": UnprocessableEntity},
        "500": {"model": InternalServerError},
        "503": {"model": ServiceUnavailable},
    },
)
async def list_games(
    date: Optional[str] = Query(None, description="Filter by date in YYYY-MM-DD format"),
    team_id: Optional[int] = Query(None, description="Filter by team ID"),
    status: Optional[str] = Query(None, description="Filter by game status (scheduled, in_progress, completed)"),
    limit: int = Query(50, le=200, description="Maximum number of games to return"),
    use_cases: Dict = Depends(get_game_use_cases),
) -> JSONResponse:
    """
    Retrieve games with optional filtering and pagination.

    Args:
        date: Filter by date in YYYY-MM-DD format
        team_id: Filter by team ID
        status: Filter by game status
        limit: Maximum number of games to return
        use_cases: Dependency injected use cases

    Returns:
        JSONResponse: Standardized response with games list

    Raises:
        DomainExceptions.InvalidDataError: If filters are invalid
    """
    # Validate date format if provided
    if date:
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise DomainExceptions.InvalidDataError("Date must be in YYYY-MM-DD format")

    # Validate status if provided
    valid_statuses = ["scheduled", "in_progress", "completed", "postponed", "cancelled"]
    if status and status not in valid_statuses:
        raise DomainExceptions.InvalidDataError(f"Status must be one of: {', '.join(valid_statuses)}")

    # Validate team_id if provided
    if team_id is not None and team_id <= 0:
        raise DomainExceptions.InvalidDataError("Team ID must be a positive integer")

    list_games_use_case = use_cases["list_games"]

    # Convert date string to a date object if provided
    game_date = None
    if date:
        game_date = datetime.strptime(date, "%Y-%m-%d").date()

    games = await list_games_use_case.execute(game_date=game_date, team_id=team_id, status=status, limit=limit)

    games_dto = to_game_dto_list(games)

    return ResponseHandler.success(data=games_dto, message=f"Retrieved {len(games_dto)} games successfully")


@router.get(
    "/games/{game_id}",
    tags=["Games"],
    response_model=GameDetailResponse,
    responses={
        "400": {"model": BadRequest},
        "404": {"model": NotFound},
        "422": {"model": UnprocessableEntity},
        "500": {"model": InternalServerError},
        "503": {"model": ServiceUnavailable},
    },
)
async def get_game(
    game_id: int = Path(..., description="The ID of the game to get"),
    use_cases: Dict = Depends(get_game_use_cases),
) -> JSONResponse:
    """
    Get a game by its ID.

    Args:
        game_id: The ID of the game to retrieve
        use_cases: Dependency injected use cases

    Returns:
        JSONResponse: Standardized response with game details

    Raises:
        DomainExceptions.GameNotFoundError: If game is not found
        DomainExceptions.InvalidDataError: If game_id is invalid
    """
    if game_id <= 0:
        raise DomainExceptions.InvalidDataError("Game ID must be a positive integer")

    get_game_use_case = use_cases["get_game"]
    game = await get_game_use_case.execute(game_id=game_id)

    if not game:
        raise DomainExceptions.GameNotFoundError(game_id)

    game_dto = to_game_dto(game)

    return ResponseHandler.success(data=game_dto, message=f"Game {game_id} retrieved successfully")


@router.post(
    "/data/ingest/games",
    tags=["Games", "Data Ingestion"],
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
async def ingest_games(
    date: Optional[str] = Query(None, description="Specific date to ingest games for (YYYY-MM-DD)"),
    days_back: int = Query(7, le=30, description="Number of days back to ingest games for"),
    use_cases: Dict = Depends(get_game_use_cases),
) -> JSONResponse:
    """
    Ingest game data from external MLB API.

    Args:
        date: Specific date to ingest games for in YYYY-MM-DD format
        days_back: Number of days back to ingest (max 30)
        use_cases: Dependency injected use cases

    Returns:
        JSONResponse: Standardized response with ingestion results

    Raises:
        DomainExceptions.InvalidDataError: If date format is invalid
        DomainExceptions.ExternalServiceError: If MLB API is unavailable
    """
    start_time = datetime.now()
    game_date = None
    if date:
        try:
            game_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise DomainExceptions.InvalidDataError("Date must be in YYYY-MM-DD format")
    if days_back < 1 or days_back > 30:
        raise DomainExceptions.InvalidDataError("Days back must be between 1 and 30")
    try:
        ingest_games_use_case = use_cases["ingest_games"]
        if game_date:
            ingested_games = await ingest_games_use_case.execute(game_date=game_date)
            operation_desc = f"date {date}"
        else:
            ingested_games = await ingest_games_use_case.execute(days_back=days_back)
            operation_desc = f"last {days_back} days"
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        games_dto = to_game_dto_list(ingested_games[:5])
        ingestion_result = DataIngestionResultDTO(
            operation="game_ingestion",
            records_processed=len(ingested_games),
            records_created=len(ingested_games),
            records_updated=0,
            errors=[],
            duration_seconds=duration,
            timestamp=end_time,
        )
        return ResponseHandler.created(
            data={"ingestion_summary": ingestion_result, "sample_games": games_dto},
            message=f"Successfully ingested {len(ingested_games)} games for {operation_desc}",
        )
    except Exception as e:
        if "MLB API" in str(e) or "api" in str(e).lower():
            raise DomainExceptions.ExternalServiceError("MLB API", str(e))
        raise

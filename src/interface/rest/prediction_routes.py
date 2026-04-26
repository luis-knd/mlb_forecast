"""
REST API routes for prediction operations.
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from application.use_cases.prediction_use_cases import GeneratePredictionUseCase, GetPredictionsForGameUseCase
from infrastructure.cache.cache_provider import get_cache_adapter
from infrastructure.db.database import get_db
from infrastructure.db.repositories.game_repository import GameRepository
from infrastructure.db.repositories.prediction_repository import PredictionRepository
from infrastructure.db.repositories.team_stats_repository import TeamStatsRepository
from infrastructure.ml.model_adapter import MLModelAdapter
from interface.rest.exception_handlers import DomainExceptions
from interface.rest.generated.models.models import (
    BadRequest,
    InternalServerError,
    NotFound,
    PredictionCreateResponse,
    PredictionDTO,
    PredictionListResponse,
    ServiceUnavailable,
    UnprocessableEntity,
)
from interface.rest.response_handler import ResponseHandler

router = APIRouter()


def get_prediction_use_cases(db: Annotated[Session, Depends(get_db)]):
    """Get prediction use cases with dependencies."""
    prediction_repository = PredictionRepository(db)
    game_repository = GameRepository(db)
    team_stats_repository = TeamStatsRepository(db)
    cache_adapter = get_cache_adapter()
    ml_model_adapter = MLModelAdapter()

    return {
        "get_predictions": GetPredictionsForGameUseCase(prediction_repository, cache_adapter),
        "generate_prediction": GeneratePredictionUseCase(
            prediction_repository, game_repository, team_stats_repository, ml_model_adapter, cache_adapter
        ),
    }


@router.get(
    "/predictions/{game_id}",
    tags=["Predictions"],
    response_model=PredictionListResponse,
    responses={
        "400": {"model": BadRequest},
        "404": {"model": NotFound},
        "422": {"model": UnprocessableEntity},
        "500": {"model": InternalServerError},
        "503": {"model": ServiceUnavailable},
    },
)
async def get_game_predictions(
    game_id: Annotated[int, Path(description="The ID of the game to get predictions for")],
    prediction_type: Annotated[str | None, Query(description="Filter by prediction type")] = None,
    *,
    use_cases: Annotated[dict, Depends(get_prediction_use_cases)],
) -> JSONResponse:
    """
    Get predictions for a specific game.

    Retrieves machine learning predictions for a game including win probabilities
    and predicted scores for both teams.

    Args:
        game_id: The ID of the game to get predictions for
        prediction_type: Optional filter by prediction type
        use_cases: Dependency injected dictionary containing use cases

    Returns:
        JSONResponse: Standardized response with prediction data

    Raises:
        DomainExceptions.InvalidDataError: If game_id is invalid
    """
    if game_id <= 0:
        raise DomainExceptions.InvalidDataError("Game ID must be a positive integer")

    get_predictions_use_case = use_cases["get_predictions"]
    predictions = await get_predictions_use_case.execute(game_id=game_id, prediction_type=prediction_type)

    if not predictions:
        return ResponseHandler.success(data=[], message=f"No predictions found for game {game_id}")

    predictions_dto = [PredictionDTO.model_validate(prediction) for prediction in predictions]

    return ResponseHandler.success(
        data=predictions_dto, message=f"Retrieved {len(predictions_dto)} predictions for game {game_id}"
    )


@router.post(
    "/predictions",
    tags=["Predictions"],
    response_model=PredictionCreateResponse,
    status_code=201,
    responses={
        "201": {"model": PredictionCreateResponse},
        "400": {"model": BadRequest},
        "404": {"model": NotFound},
        "422": {"model": UnprocessableEntity},
        "500": {"model": InternalServerError},
        "503": {"model": ServiceUnavailable},
    },
)
async def generate_prediction(
    game_id: Annotated[int, Query(description="The ID of the game to create prediction for")],
    prediction_type: Annotated[str, Query(description="Type of prediction to generate")] = "winner",
    *,
    use_cases: Annotated[dict, Depends(get_prediction_use_cases)],
) -> JSONResponse:
    """
    Generate a new prediction for a game.

    Creates machine learning predictions for a game using current team statistics
    and historical performance data.

    Args:
        game_id: The ID of the game to create prediction for
        prediction_type: Type of prediction to generate (winner, total_runs, etc.)
        use_cases: Dependency injected dictionary containing use cases

    Returns:
        JSONResponse: Standardized response with created prediction

    Raises:
        DomainExceptions.GameNotFoundError: If the game is not found
        DomainExceptions.InvalidDataError: If game_id is invalid
        DomainExceptions.ExternalServiceError: If ML model is unavailable
    """
    if game_id <= 0:
        raise DomainExceptions.InvalidDataError("Game ID must be a positive integer")

    valid_prediction_types = ["winner", "total_runs", "score"]
    if prediction_type not in valid_prediction_types:
        raise DomainExceptions.InvalidDataError(f"Prediction type must be one of: {', '.join(valid_prediction_types)}")

    start_time = datetime.now()

    try:
        generate_prediction_use_case = use_cases["generate_prediction"]
        prediction = await generate_prediction_use_case.execute(game_id=game_id, prediction_type=prediction_type)

        if not prediction:
            raise DomainExceptions.GameNotFoundError(game_id)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        prediction_dto = PredictionDTO.model_validate(prediction)

        return ResponseHandler.created(
            data={
                "prediction": prediction_dto,
                "processing_time_seconds": duration,
                "created_at": end_time.isoformat(),
            },
            message=f"Prediction created successfully for game {game_id}",
        )

    except Exception as e:
        if "model" in str(e).lower() or "ml" in str(e).lower():
            raise DomainExceptions.ExternalServiceError("ML Model", str(e)) from e
        raise

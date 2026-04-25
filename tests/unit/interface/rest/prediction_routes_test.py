import json
from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from interface.rest.exception_handlers import DomainExceptions
from interface.rest import prediction_routes as prediction_routes_module
from interface.rest.prediction_routes import generate_prediction, get_game_predictions


def _body(response):
    return json.loads(response.body)


def _prediction_payload(game_id: int) -> dict:
    return {
        "id": 5,
        "game_id": game_id,
        "ml_model_version": "test-v1",
        "home_win_probability": 0.62,
        "away_win_probability": 0.38,
        "predicted_home_score": 5,
        "predicted_away_score": 3,
        "confidence_score": 0.8,
        "created_at": datetime(2026, 3, 18, 10, 0, 0),
    }


@pytest.mark.asyncio
async def test_get_game_predictions_returns_empty_success_when_no_predictions():
    # Given
    use_cases = {"get_predictions": AsyncMock()}
    use_cases["get_predictions"].execute.return_value = []

    # When
    response = await get_game_predictions(game_id=10, prediction_type=None, use_cases=use_cases)

    # Then
    payload = _body(response)
    assert payload["status"] == "success"
    assert payload["data"] == []


@pytest.mark.asyncio
async def test_get_game_predictions_returns_serialized_prediction_list():
    # Given
    use_cases = {"get_predictions": AsyncMock()}
    use_cases["get_predictions"].execute.return_value = [_prediction_payload(game_id=21)]

    # When
    response = await get_game_predictions(game_id=21, prediction_type="winner", use_cases=use_cases)

    # Then
    payload = _body(response)
    assert payload["status"] == "success"
    assert payload["data"][0]["game_id"] == 21
    assert "Retrieved 1 predictions" in payload["message"]


@pytest.mark.asyncio
async def test_get_game_predictions_rejects_non_positive_game_id():
    # Given / When / Then
    with pytest.raises(DomainExceptions.InvalidDataError, match="Game ID must be a positive integer"):
        await get_game_predictions(game_id=0, prediction_type=None, use_cases={"get_predictions": AsyncMock()})


@pytest.mark.asyncio
async def test_generate_prediction_rejects_invalid_prediction_type():
    # Given / When / Then
    with pytest.raises(DomainExceptions.InvalidDataError, match="Prediction type must be one of"):
        await generate_prediction(
            game_id=12,
            prediction_type="invalid-type",
            use_cases={"generate_prediction": AsyncMock()},
        )


@pytest.mark.asyncio
async def test_generate_prediction_rejects_non_positive_game_id():
    # Given / When / Then
    with pytest.raises(DomainExceptions.InvalidDataError, match="Game ID must be a positive integer"):
        await generate_prediction(game_id=0, prediction_type="winner", use_cases={"generate_prediction": AsyncMock()})


@pytest.mark.asyncio
async def test_generate_prediction_wraps_model_errors_as_external_service_error():
    # Given
    use_cases = {"generate_prediction": AsyncMock()}
    use_cases["generate_prediction"].execute.side_effect = RuntimeError("ML model not loaded")

    # When / Then
    with pytest.raises(DomainExceptions.ExternalServiceError):
        await generate_prediction(game_id=33, prediction_type="winner", use_cases=use_cases)


@pytest.mark.asyncio
async def test_generate_prediction_returns_created_payload_with_processing_metadata():
    # Given
    use_cases = {"generate_prediction": AsyncMock()}
    use_cases["generate_prediction"].execute.return_value = _prediction_payload(game_id=33)

    # When
    response = await generate_prediction(game_id=33, prediction_type="winner", use_cases=use_cases)

    # Then
    payload = _body(response)
    assert response.status_code == 201
    assert payload["status"] == "success"
    assert payload["data"]["prediction"]["game_id"] == 33
    assert payload["data"]["processing_time_seconds"] >= 0


@pytest.mark.asyncio
async def test_generate_prediction_raises_game_not_found_when_use_case_returns_none():
    # Given
    use_cases = {"generate_prediction": AsyncMock()}
    use_cases["generate_prediction"].execute.return_value = None

    # When / Then
    with pytest.raises(DomainExceptions.GameNotFoundError):
        await generate_prediction(game_id=404, prediction_type="winner", use_cases=use_cases)


@pytest.mark.asyncio
async def test_generate_prediction_reraises_non_model_errors():
    # Given
    use_cases = {"generate_prediction": AsyncMock()}
    use_cases["generate_prediction"].execute.side_effect = RuntimeError("database timeout")

    # When / Then
    with pytest.raises(RuntimeError, match="database timeout"):
        await generate_prediction(game_id=11, prediction_type="winner", use_cases=use_cases)


def test_get_prediction_use_cases_builds_expected_dependency_map(monkeypatch):
    # Given
    fake_db = object()

    class _PredictionRepository:
        def __init__(self, db):
            self.db = db

    class _GameRepository:
        def __init__(self, db):
            self.db = db

    class _TeamStatsRepository:
        def __init__(self, db):
            self.db = db

    class _MLModelAdapter:
        pass

    class _GetPredictionsUseCase:
        def __init__(self, prediction_repo, cache):
            self.prediction_repo = prediction_repo
            self.cache = cache

    class _GeneratePredictionUseCase:
        def __init__(self, prediction_repo, game_repo, team_stats_repo, ml_model, cache):
            self.prediction_repo = prediction_repo
            self.game_repo = game_repo
            self.team_stats_repo = team_stats_repo
            self.ml_model = ml_model
            self.cache = cache

    cache_adapter = object()
    monkeypatch.setattr(prediction_routes_module, "PredictionRepository", _PredictionRepository)
    monkeypatch.setattr(prediction_routes_module, "GameRepository", _GameRepository)
    monkeypatch.setattr(prediction_routes_module, "TeamStatsRepository", _TeamStatsRepository)
    monkeypatch.setattr(prediction_routes_module, "MLModelAdapter", _MLModelAdapter)
    monkeypatch.setattr(prediction_routes_module, "GetPredictionsForGameUseCase", _GetPredictionsUseCase)
    monkeypatch.setattr(prediction_routes_module, "GeneratePredictionUseCase", _GeneratePredictionUseCase)
    monkeypatch.setattr(prediction_routes_module, "get_cache_adapter", lambda: cache_adapter)

    # When
    use_cases = prediction_routes_module.get_prediction_use_cases(db=fake_db)

    # Then
    assert set(use_cases.keys()) == {"get_predictions", "generate_prediction"}
    assert use_cases["get_predictions"].prediction_repo.db is fake_db
    assert use_cases["generate_prediction"].game_repo.db is fake_db
    assert use_cases["generate_prediction"].cache is cache_adapter

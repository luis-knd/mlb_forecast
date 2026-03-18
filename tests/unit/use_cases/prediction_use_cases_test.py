from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from application.use_cases.prediction_use_cases import (
    GeneratePredictionUseCase,
    GetPredictionsForGameUseCase,
    ListUpcomingPredictionsUseCase,
    UpdatePredictionWithResultUseCase,
)
from domain.entities.game import Game
from domain.entities.prediction import Prediction
from domain.entities.team_stats import TeamStats


@pytest.fixture
def sample_game() -> Game:
    return Game(
        id=10,
        mlb_game_id=20240101,
        home_team_id=1,
        away_team_id=2,
        game_date=datetime.now(UTC) + timedelta(days=1),
        status="scheduled",
    )


@pytest.fixture
def completed_game() -> Game:
    return Game(
        id=10,
        mlb_game_id=20240101,
        home_team_id=1,
        away_team_id=2,
        game_date=datetime.now(UTC) - timedelta(days=1),
        status="completed",
        home_score=5,
        away_score=3,
        winning_team_id=1,
    )


@pytest.fixture
def sample_team_stats() -> TeamStats:
    return TeamStats.create(
        team_id=1,
        season=datetime.now(UTC).year,
        games_played=50,
        wins=30,
        losses=20,
    )


@pytest.fixture
def sample_prediction() -> Prediction:
    return Prediction(
        id=21,
        game_id=10,
        prediction_type="winner",
        home_win_probability=0.6,
        away_win_probability=0.4,
        model_version="v1",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


class TestGeneratePredictionUseCase:
    @pytest.mark.asyncio
    async def test_returns_none_when_game_not_found(self, sample_team_stats):
        # Given
        prediction_repository = AsyncMock()
        game_repository = AsyncMock()
        game_repository.get_by_id = AsyncMock(return_value=None)
        team_stats_repository = AsyncMock()
        ml_model = AsyncMock()
        cache = AsyncMock()
        use_case = GeneratePredictionUseCase(
            prediction_repository,
            game_repository,
            team_stats_repository,
            ml_model,
            cache,
        )

        # When
        result = await use_case.execute(game_id=10)

        # Then
        assert result is None
        ml_model.predict_game_outcome.assert_not_called()
        prediction_repository.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_none_when_game_already_completed(
        self,
        completed_game,
        sample_team_stats,
    ):
        # Given
        prediction_repository = AsyncMock()
        game_repository = AsyncMock()
        game_repository.get_by_id = AsyncMock(return_value=completed_game)
        team_stats_repository = AsyncMock()
        ml_model = AsyncMock()
        cache = AsyncMock()
        use_case = GeneratePredictionUseCase(
            prediction_repository,
            game_repository,
            team_stats_repository,
            ml_model,
            cache,
        )

        # When
        result = await use_case.execute(game_id=10)

        # Then
        assert result is None
        ml_model.predict_game_outcome.assert_not_called()
        prediction_repository.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_none_when_team_stats_missing(self, sample_game):
        # Given
        prediction_repository = AsyncMock()
        game_repository = AsyncMock()
        game_repository.get_by_id = AsyncMock(return_value=sample_game)
        team_stats_repository = AsyncMock()
        team_stats_repository.get_by_team_and_season = AsyncMock(return_value=None)
        ml_model = AsyncMock()
        cache = AsyncMock()
        use_case = GeneratePredictionUseCase(
            prediction_repository,
            game_repository,
            team_stats_repository,
            ml_model,
            cache,
        )

        # When
        result = await use_case.execute(game_id=10)

        # Then
        assert result is None
        ml_model.predict_game_outcome.assert_not_called()
        prediction_repository.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_generates_prediction_and_clears_cache(
        self,
        sample_game,
        sample_team_stats,
        sample_prediction,
    ):
        # Given
        prediction_repository = AsyncMock()
        prediction_repository.save = AsyncMock(return_value=sample_prediction)
        game_repository = AsyncMock()
        game_repository.get_by_id = AsyncMock(return_value=sample_game)
        game_repository.list_historical_matchups = AsyncMock(return_value=[])
        team_stats_repository = AsyncMock()
        team_stats_repository.get_by_team_and_season = AsyncMock(side_effect=[sample_team_stats, sample_team_stats])
        ml_model = AsyncMock()
        base_prediction = Prediction.create(
            game_id=0,
            prediction_type="winner",
            model_version="v1",
        )
        ml_model.predict_game_outcome = AsyncMock(return_value=base_prediction)
        cache = AsyncMock()
        use_case = GeneratePredictionUseCase(
            prediction_repository,
            game_repository,
            team_stats_repository,
            ml_model,
            cache,
        )

        # When
        result = await use_case.execute(game_id=10, prediction_type="winner")

        # Then
        ml_model.predict_game_outcome.assert_awaited_once()
        prediction_repository.save.assert_awaited_once()
        cache.clear.assert_awaited_once_with(pattern="predictions:game:10*")
        assert result is sample_prediction


class TestGetPredictionsForGameUseCase:
    @pytest.mark.asyncio
    async def test_returns_cached_predictions(self, sample_prediction):
        # Given
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=[sample_prediction])
        prediction_repository = AsyncMock()
        use_case = GetPredictionsForGameUseCase(prediction_repository, cache)

        # When
        result = await use_case.execute(game_id=10)

        # Then
        cache.get.assert_called_once_with("predictions:game:10:all")
        prediction_repository.list_by_game.assert_not_called()
        assert result == [sample_prediction]

    @pytest.mark.asyncio
    async def test_filters_by_prediction_type(self, sample_prediction):
        # Given
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=None)
        prediction_repository = AsyncMock()
        prediction_repository.list_by_game_and_type = AsyncMock(return_value=[sample_prediction])
        use_case = GetPredictionsForGameUseCase(prediction_repository, cache)

        # When
        result = await use_case.execute(game_id=10, prediction_type="winner")

        # Then
        prediction_repository.list_by_game_and_type.assert_awaited_once_with(
            10,
            "winner",
        )
        cache.set.assert_awaited_once_with(
            "predictions:game:10:winner",
            [sample_prediction],
            ttl=1800,
        )
        assert result == [sample_prediction]

    @pytest.mark.asyncio
    async def test_fetches_all_predictions_when_no_filter(self, sample_prediction):
        # Given
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=None)
        prediction_repository = AsyncMock()
        prediction_repository.list_by_game = AsyncMock(return_value=[sample_prediction])
        use_case = GetPredictionsForGameUseCase(prediction_repository, cache)

        # When
        result = await use_case.execute(game_id=10)

        # Then
        prediction_repository.list_by_game.assert_awaited_once_with(10)
        cache.set.assert_awaited_once_with(
            "predictions:game:10:all",
            [sample_prediction],
            ttl=1800,
        )
        assert result == [sample_prediction]


class TestListUpcomingPredictionsUseCase:
    @pytest.mark.asyncio
    async def test_returns_cached_result(self):
        # Given
        cached_payload = [{"game": object(), "predictions": []}]
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=cached_payload)
        prediction_repository = AsyncMock()
        game_repository = AsyncMock()
        use_case = ListUpcomingPredictionsUseCase(
            prediction_repository,
            game_repository,
            cache,
        )

        # When
        result = await use_case.execute(days_ahead=2, limit=5)

        # Then
        cache.get.assert_called_once_with("predictions:upcoming:2:5")
        game_repository.list_upcoming_games.assert_not_called()
        assert result == cached_payload

    @pytest.mark.asyncio
    async def test_collects_predictions_and_caches(self, sample_prediction):
        # Given
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=None)
        upcoming_games = [
            Game(
                id=1,
                mlb_game_id=100,
                home_team_id=1,
                away_team_id=2,
                game_date=datetime.now(UTC) + timedelta(days=1),
                status="scheduled",
            )
        ]
        game_repository = AsyncMock()
        game_repository.list_upcoming_games = AsyncMock(return_value=upcoming_games)

        prediction_with_timestamp = Prediction(
            id=1,
            game_id=1,
            prediction_type="winner",
            home_win_probability=0.6,
            away_win_probability=0.4,
            model_version="v1",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        prediction_repository = AsyncMock()
        prediction_repository.list_by_game = AsyncMock(return_value=[prediction_with_timestamp])
        use_case = ListUpcomingPredictionsUseCase(
            prediction_repository,
            game_repository,
            cache,
        )

        # When
        result = await use_case.execute(days_ahead=1, limit=1)

        # Then
        game_repository.list_upcoming_games.assert_awaited_once_with(1, 1)
        prediction_repository.list_by_game.assert_awaited_once_with(1)
        cache.set.assert_awaited_once()
        assert result[0]["game"].id == 1
        assert result[0]["predictions"] == [prediction_with_timestamp]


class TestUpdatePredictionWithResultUseCase:
    @pytest.mark.asyncio
    async def test_returns_none_when_prediction_missing(self):
        # Given
        prediction_repository = AsyncMock()
        prediction_repository.get_by_id = AsyncMock(return_value=None)
        game_repository = AsyncMock()
        cache = AsyncMock()
        use_case = UpdatePredictionWithResultUseCase(
            prediction_repository,
            game_repository,
            cache,
        )

        # When
        result = await use_case.execute(prediction_id=5)

        # Then
        assert result is None
        game_repository.get_by_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_none_when_game_not_found(self, sample_prediction):
        # Given
        prediction_repository = AsyncMock()
        prediction_repository.get_by_id = AsyncMock(return_value=sample_prediction)
        game_repository = AsyncMock()
        game_repository.get_by_id = AsyncMock(return_value=None)
        cache = AsyncMock()
        use_case = UpdatePredictionWithResultUseCase(
            prediction_repository,
            game_repository,
            cache,
        )

        # When
        result = await use_case.execute(prediction_id=21)

        # Then
        assert result is None
        prediction_repository.update_with_actual_result.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_none_when_game_not_completed(
        self,
        sample_prediction,
        sample_game,
    ):
        # Given
        prediction_repository = AsyncMock()
        prediction_repository.get_by_id = AsyncMock(return_value=sample_prediction)
        game_repository = AsyncMock()
        game_repository.get_by_id = AsyncMock(return_value=sample_game)
        cache = AsyncMock()
        use_case = UpdatePredictionWithResultUseCase(
            prediction_repository,
            game_repository,
            cache,
        )

        # When
        result = await use_case.execute(prediction_id=21)

        # Then
        assert result is None
        prediction_repository.update_with_actual_result.assert_not_called()

    @pytest.mark.asyncio
    async def test_updates_prediction_with_winner_accuracy(
        self,
        sample_prediction,
        completed_game,
    ):
        # Given
        prediction_repository = AsyncMock()
        prediction_repository.get_by_id = AsyncMock(return_value=sample_prediction)
        updated_prediction = Prediction(
            id=sample_prediction.id,
            game_id=sample_prediction.game_id,
            prediction_type="winner",
            home_win_probability=0.6,
            away_win_probability=0.4,
            model_version="v1",
            actual_result={"home_score": 5, "away_score": 3},
            prediction_accuracy=1.0,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        prediction_repository.update_with_actual_result = AsyncMock(return_value=updated_prediction)
        game_repository = AsyncMock()
        game_repository.get_by_id = AsyncMock(return_value=completed_game)
        cache = AsyncMock()
        use_case = UpdatePredictionWithResultUseCase(
            prediction_repository,
            game_repository,
            cache,
        )

        # When
        result = await use_case.execute(prediction_id=21)

        # Then
        prediction_repository.update_with_actual_result.assert_awaited_once()
        cache.clear.assert_awaited_once_with(pattern="predictions:game:10*")
        assert result is updated_prediction

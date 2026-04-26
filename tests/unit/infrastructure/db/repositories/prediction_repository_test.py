from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from domain.entities.prediction import Prediction
from infrastructure.db.repositories.prediction_repository import PredictionRepository


class TestPredictionRepository:
    @pytest.fixture
    def session(self):
        return MagicMock()

    @pytest.fixture
    def repository(self, session):
        return PredictionRepository(session)

    @staticmethod
    def _prediction_model(prediction_id: int = 1) -> SimpleNamespace:
        now = datetime(2026, 4, 1, 12, 0, 0)
        game_model = SimpleNamespace(
            id=10,
            mlb_game_id=9001,
            home_team_id=1,
            away_team_id=2,
            game_date=now,
            scheduled_innings=9,
            status="scheduled",
            home_score=None,
            away_score=None,
            winning_team_id=None,
            created_at=now,
            updated_at=now,
            home_team=None,
            away_team=None,
            winning_team=None,
        )
        return SimpleNamespace(
            id=prediction_id,
            game_id=10,
            prediction_type="winner",
            home_win_probability=0.6,
            away_win_probability=0.4,
            over_under_runs=8.5,
            total_runs_prediction=9.0,
            detailed_predictions={"winner": "home"},
            model_version="1.0.0",
            confidence_score=0.8,
            feature_importance={"x": 1},
            actual_result=None,
            prediction_accuracy=None,
            created_at=now,
            updated_at=now,
            game=game_model,
        )

    @pytest.mark.asyncio
    async def test_get_by_id_and_list_queries_map_entities(self, repository, session):
        # Given
        model = self._prediction_model()
        query = session.query.return_value.options.return_value
        query.filter.return_value.first.return_value = model
        query.filter.return_value.order_by.return_value.all.return_value = [model]
        query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [model]
        query.order_by.return_value.limit.return_value.all.return_value = [model]

        # When
        by_id = await repository.get_by_id(1)
        by_game = await repository.list_by_game(10)
        by_game_type = await repository.list_by_game_and_type(10, "winner")
        latest = await repository.list_latest_predictions(limit=5)
        by_version = await repository.list_by_model_version("1.0.0", limit=5)

        # Then
        assert by_id is not None
        assert by_id.prediction_type == "winner"
        assert len(by_game) == 1
        assert len(by_game_type) == 1
        assert len(latest) == 1
        assert len(by_version) == 1

    @pytest.mark.asyncio
    async def test_get_by_id_returns_none_when_missing(self, repository, session):
        # Given
        session.query.return_value.options.return_value.filter.return_value.first.return_value = None

        # When
        result = await repository.get_by_id(404)

        # Then
        assert result is None

    @pytest.mark.asyncio
    async def test_save_updates_existing_prediction_by_id(self, repository, session):
        # Given
        existing_model = self._prediction_model(prediction_id=1)
        session.query.return_value.filter.return_value.first.return_value = existing_model
        repository.get_by_id = AsyncMock(return_value=Prediction.create(10, "winner", "1.0.0"))

        entity = Prediction.create(10, "winner", "1.0.1", home_win_probability=0.55, away_win_probability=0.45)
        entity.id = 1

        # When
        result = await repository.save(entity)

        # Then
        assert result is not None
        session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_creates_new_prediction(self, repository, session):
        # Given
        session.query.return_value.filter.return_value.first.return_value = None
        repository.get_by_id = AsyncMock(return_value=Prediction.create(10, "winner", "1.0.0"))
        entity = Prediction.create(10, "winner", "1.0.0")

        # When
        result = await repository.save(entity)

        # Then
        assert result is not None
        session.add.assert_called_once()
        session.commit.assert_called_once()
        session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_with_actual_result_and_delete(self, repository, session):
        # Given
        existing_model = self._prediction_model(prediction_id=8)
        session.query.return_value.filter.return_value.first.side_effect = [existing_model, existing_model, None]
        repository.get_by_id = AsyncMock(return_value=Prediction.create(10, "winner", "1.0.0"))

        # When
        updated = await repository.update_with_actual_result(8, {"winner": "home"}, 1.0)
        deleted = await repository.delete(8)
        deleted_missing = await repository.delete(9)

        # Then
        assert updated is not None
        assert deleted is True
        assert deleted_missing is False

    @pytest.mark.asyncio
    async def test_get_prediction_accuracy_by_model(self, repository, session):
        # Given
        scalar_query = session.query.return_value.filter.return_value
        scalar_query.scalar.side_effect = [0.73, None]

        # When
        avg = await repository.get_prediction_accuracy_by_model("v1")
        empty = await repository.get_prediction_accuracy_by_model("v2")

        # Then
        assert avg == 0.73
        assert empty == 0.0

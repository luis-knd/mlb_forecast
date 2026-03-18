from datetime import UTC, datetime

import pytest

from domain.entities.prediction import Prediction


class TestPredictionEntity:
    def test_create_assigns_fields_and_timestamps(self):
        # Given
        model_version = "v0.1.0"

        # When
        prediction = Prediction.create(
            game_id=1,
            prediction_type="winner",
            model_version=model_version,
            home_win_probability=0.7,
            away_win_probability=0.3,
            total_runs_prediction=8.5,
        )

        # Then
        assert prediction.id is None
        assert prediction.game_id == 1
        assert prediction.prediction_type == "winner"
        assert prediction.model_version == model_version
        assert prediction.created_at is not None
        assert prediction.updated_at is not None

    def test_update_with_actual_result_mutates_state(self):
        # Given
        prediction = Prediction.create(game_id=5, prediction_type="winner", model_version="v1")
        actual_result = {"home_score": 4, "away_score": 2}
        accuracy = 1.0

        # When
        prediction.update_with_actual_result(actual_result=actual_result, accuracy=accuracy)

        # Then
        assert prediction.actual_result == actual_result
        assert prediction.prediction_accuracy == accuracy
        assert isinstance(prediction.updated_at, datetime)

    @pytest.mark.parametrize(
        "home_prob, away_prob, expected",
        [(0.75, 0.25, "home"), (0.1, 0.9, "away"), (0.5, 0.5, None), (None, 0.4, None)],
    )
    def test_get_predicted_winner(self, home_prob, away_prob, expected):
        # Given
        prediction = Prediction(
            id=None,
            game_id=10,
            prediction_type="winner",
            home_win_probability=home_prob,
            away_win_probability=away_prob,
            model_version="v1",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        # When
        result = prediction.get_predicted_winner()

        # Then
        assert result == expected

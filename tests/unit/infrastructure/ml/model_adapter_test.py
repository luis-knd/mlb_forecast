from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pandas as pd
import pytest

from domain.entities.game import Game
from infrastructure.ml.model_adapter import (
    MLModelAdapter,
    MLModelException,
    _create_game_features,
    _create_matchup_features,
    _create_temporal_features,
    _team_stats_to_dict,
    _to_float,
    _to_number,
)


def test_numeric_helpers_and_team_stats_transform():
    # Given
    stats = {
        "hitting_stats": {"games_played": 10, "runs_scored": 50, "batting_average": 0.3},
        "pitching_stats": {"wins": 6, "losses": 4, "runs_allowed": 40, "earned_run_average": 3.1},
    }

    # When
    float_value = _to_float({"x": "1.5"}, "x")
    number_value = _to_number({"x": "2"}, "x")
    transformed = _team_stats_to_dict(stats)

    # Then
    assert float_value == 1.5
    assert number_value == 2.0
    assert transformed["run_differential"] == 10
    assert transformed["win_percentage"] == 0.6


def test_feature_builders_create_expected_keys():
    # Given
    home = {"win_percentage": 0.7, "run_differential": 20, "ops": 0.8, "earned_run_average": 3.5}
    away = {"win_percentage": 0.4, "run_differential": -5, "ops": 0.7, "earned_run_average": 4.1}
    game_date = datetime(2026, 4, 20)

    # When
    matchup = _create_matchup_features(home, away, historical_matchups=[])
    temporal = _create_temporal_features(game_date)
    features = _create_game_features(
        {"hitting_stats": {}, "pitching_stats": {}},
        {"hitting_stats": {}, "pitching_stats": {}},
        game_date,
    )

    # Then
    assert "win_pct_diff" in matchup
    assert "day_of_week" in temporal
    assert "away_runs_scored" in features
    assert "season_progress" in features


def test_static_training_helpers_and_feature_mapping():
    # Given
    df = pd.DataFrame([{"a": 1, "winner": 1, "total_runs": 8}] * 60)

    # When
    frame = MLModelAdapter._to_training_frame(df.to_dict(orient="records"))
    features, winner, total_runs = MLModelAdapter._extract_training_columns(frame)
    split = MLModelAdapter._split_training_data(np.ones((60, 1)), winner, total_runs)
    mapped = MLModelAdapter._map_feature_importance([0.1, 0.2])

    # Then
    assert len(frame) == 60
    assert list(features.columns) == ["a"]
    assert len(split) == 6
    assert "feature_0" in mapped


def test_to_training_frame_raises_for_insufficient_data():
    # Given / When / Then
    with pytest.raises(MLModelException):
        MLModelAdapter._to_training_frame([{"a": 1, "winner": 1, "total_runs": 8}] * 10)


@pytest.fixture
def adapter(monkeypatch, tmp_path):
    monkeypatch.setattr(MLModelAdapter, "_try_load_model", lambda self: None)
    model_adapter = MLModelAdapter()
    model_adapter.model_dir = str(tmp_path)
    return model_adapter


@pytest.mark.asyncio
async def test_train_predict_evaluate_and_version_helpers(adapter, monkeypatch):
    # Given
    historical = [{"f1": 1.0, "winner": 1, "total_runs": 8.0}] * 60
    monkeypatch.setattr(adapter, "save_model", AsyncMock(return_value=True))

    # When
    metrics = await adapter.train(historical)
    performance = await adapter.get_model_performance()
    version = await adapter.get_model_version()

    # Then
    assert metrics["training_samples"] == 60
    assert performance["is_trained"] == 1.0
    assert version.startswith("v1.0_")


@pytest.mark.asyncio
async def test_predict_and_evaluate_error_paths(adapter):
    # Given / When / Then
    with pytest.raises(MLModelException):
        await adapter.predict_game_outcome({}, {}, datetime(2026, 1, 1))

    with pytest.raises(MLModelException):
        await adapter.evaluate_model([])


@pytest.mark.asyncio
async def test_save_load_and_feature_importance(adapter, tmp_path):
    # Given
    adapter.is_trained = True
    filepath = str(Path(tmp_path) / "model_test.pkl")

    # When
    saved = await adapter.save_model(filepath)
    loaded = await adapter.load_model(filepath)
    importance = await adapter.get_feature_importance()

    # Then
    assert saved is True
    assert loaded is True
    assert isinstance(importance, dict)


def test_try_load_model_reads_latest_file(monkeypatch, tmp_path):
    # Given
    original_try_load = MLModelAdapter._try_load_model
    monkeypatch.setattr(MLModelAdapter, "_try_load_model", lambda self: None)
    adapter = MLModelAdapter()
    monkeypatch.setattr(MLModelAdapter, "_try_load_model", original_try_load)

    adapter.model_dir = str(tmp_path)
    adapter.is_trained = True
    latest_file = Path(tmp_path) / "model_latest.pkl"

    import pickle

    with latest_file.open("wb") as file_handle:
        pickle.dump(
            {
                "winner_model": adapter.winner_model,
                "runs_model": adapter.runs_model,
                "scaler": adapter.scaler,
                "model_version": "vX",
                "is_trained": True,
            },
            file_handle,
        )

    # When
    original_try_load(adapter)

    # Then
    assert adapter.model_version == "vX"


def test_create_matchup_features_with_historical_games():
    # Given
    home_stats = {"team_id": 1, "win_percentage": 0.6, "run_differential": 30, "ops": 0.8, "earned_run_average": 3.4}
    away_stats = {"team_id": 2, "win_percentage": 0.4, "run_differential": -10, "ops": 0.7, "earned_run_average": 4.5}
    historical = [
        Game(
            id=1,
            mlb_game_id=1,
            home_team_id=1,
            away_team_id=2,
            game_date=datetime(2026, 1, 1),
            status="completed",
            home_score=5,
            away_score=3,
            winning_team_id=1,
        ),
        Game(
            id=2,
            mlb_game_id=2,
            home_team_id=1,
            away_team_id=2,
            game_date=datetime(2026, 1, 2),
            status="completed",
            home_score=2,
            away_score=4,
            winning_team_id=2,
        ),
    ]

    # When
    features = MLModelAdapter._create_matchup_features(home_stats, away_stats, historical)

    # Then
    assert features["historical_home_win_rate"] == 0.5
    assert features["avg_total_runs_historical"] == 7.0


@pytest.mark.asyncio
async def test_train_raises_wrapped_exception(adapter):
    # Given / When / Then
    with pytest.raises(MLModelException, match="Training error"):
        await adapter.train([{"winner": 1, "total_runs": 8}])


@pytest.mark.asyncio
async def test_predict_success_and_error_wrapping(adapter):
    # Given
    adapter.is_trained = True
    adapter.scaler = AsyncMock()  # type: ignore[assignment]
    adapter.scaler.transform = MagicMock(return_value=np.array([[1.0] * 37]))
    adapter.winner_model = MagicMock()
    adapter.winner_model.predict_proba.return_value = [[0.3, 0.7]]
    adapter.runs_model = MagicMock()
    adapter.runs_model.predict.return_value = [8.2]

    home = {"hitting_stats": {}, "pitching_stats": {}}
    away = {"hitting_stats": {}, "pitching_stats": {}}

    # When
    prediction = await adapter.predict_game_outcome(home, away, datetime(2026, 4, 1))

    # Then
    assert prediction.home_win_probability == 0.7

    # Given error branch
    adapter.scaler.transform.side_effect = RuntimeError("bad scale")

    # When / Then
    with pytest.raises(MLModelException, match="Prediction error"):
        await adapter.predict_game_outcome(home, away, datetime(2026, 4, 1))


@pytest.mark.asyncio
async def test_evaluate_success_and_wrapped_error(adapter):
    # Given
    adapter.is_trained = True
    adapter.scaler.transform = MagicMock(return_value=np.array([[1.0], [1.0]]))
    adapter.winner_model.predict = MagicMock(return_value=np.array([1, 0]))
    adapter.runs_model.predict = MagicMock(return_value=np.array([8.0, 7.0]))

    # When
    metrics = await adapter.evaluate_model(
        [
            {"f1": 1, "winner": 1, "total_runs": 8.0},
            {"f1": 2, "winner": 0, "total_runs": 7.0},
        ]
    )

    # Then
    assert "test_samples" in metrics

    # Given error branch
    adapter.scaler.transform.side_effect = RuntimeError("bad")

    # When / Then
    with pytest.raises(MLModelException, match="Evaluation error"):
        await adapter.evaluate_model(
            [
                {"f1": 1, "winner": 1, "total_runs": 8.0},
                {"f1": 2, "winner": 0, "total_runs": 7.0},
            ]
        )


@pytest.mark.asyncio
async def test_model_misc_paths(adapter):
    # Given
    adapter.is_trained = False

    # When
    perf = await adapter.get_model_performance()
    save_fail = await adapter.save_model("/path/that/does/not/exist/model.pkl")
    load_fail = await adapter.load_model("/path/that/does/not/exist/model.pkl")
    raw_importance = adapter._get_feature_importance()
    mapped = adapter._map_feature_importance(
        [0.1] * len(adapter._map_feature_importance.__globals__["WINNER_FEATURE_NAMES"])
    )

    # Then
    assert perf == {"error": "Model not trained"}
    assert save_fail is False
    assert load_fail is False
    assert raw_importance == {}
    assert "games_played" in mapped

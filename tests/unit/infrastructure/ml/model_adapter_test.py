from datetime import datetime

import numpy as np
import pandas as pd
import pytest

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

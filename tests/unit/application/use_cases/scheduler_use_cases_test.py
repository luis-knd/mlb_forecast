from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from application.use_cases.scheduler_use_cases import (
    _build_team_feature_snapshot,
    _create_game_features_impl,
    _generate_upcoming_predictions_impl,
    _ingest_games_for_date_impl,
    _safe_float,
    _safe_number,
)
from domain.entities.game import Game


def _game_data(*, game_id, home_team_id, away_team_id, game_date, status="scheduled"):
    return SimpleNamespace(
        id=game_id,
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        game_date=game_date,
        status=status,
        scheduled_innings=9,
        home_score=None,
        away_score=None,
        winning_team_id=None,
    )


def _upcoming_game(*, game_id: int | None, home_team_id: int, away_team_id: int, game_date: datetime):
    return SimpleNamespace(id=game_id, home_team_id=home_team_id, away_team_id=away_team_id, game_date=game_date)


def test_safe_number_and_float_return_defaults_for_missing_or_none_values():
    # Given
    source = {"wins": None}

    # When
    wins = _safe_number(source, "wins", default=2.5)
    missing_number = _safe_number(source, "missing", default=3.0)
    missing_float = _safe_float(source, "missing", default=1.2)

    # Then
    assert wins == 2.5
    assert missing_number == 3.0
    assert missing_float == 1.2


def test_build_team_feature_snapshot_computes_percentages_without_dividing_by_zero():
    # Given
    hitting_stats = {"games_played": 0, "runs_scored": 10, "ops": "0.712"}
    pitching_stats = {"wins": 8, "losses": 4, "runs_allowed": 7, "earned_run_average": "3.11"}

    # When
    snapshot = _build_team_feature_snapshot(hitting_stats=hitting_stats, pitching_stats=pitching_stats)

    # Then
    assert snapshot["games_played"] == 0.0
    assert snapshot["win_percentage"] == 8.0
    assert snapshot["run_differential"] == 3.0
    assert snapshot["earned_run_average"] == pytest.approx(3.11)


def test_create_game_features_impl_builds_expected_diffs_and_time_features():
    # Given
    game = Game.create(
        mlb_game_id=1,
        home_team_id=10,
        away_team_id=20,
        game_date=datetime(2026, 3, 21, 19, 0, 0),
        status="scheduled",
    )

    # When
    features = _create_game_features_impl(
        home_team_stats={
            "hitting_stats": {"games_played": 20, "runs_scored": 100, "ops": 0.8},
            "pitching_stats": {"wins": 12, "losses": 8, "runs_allowed": 90, "earned_run_average": 3.2},
        },
        away_team_stats={
            "hitting_stats": {"games_played": 20, "runs_scored": 80, "ops": 0.7},
            "pitching_stats": {"wins": 10, "losses": 10, "runs_allowed": 95, "earned_run_average": 3.8},
        },
        game=game,
    )

    # Then
    assert features["win_pct_diff"] == pytest.approx(0.1)
    assert features["runs_diff_advantage"] == 25.0
    assert features["ops_diff"] == pytest.approx(0.1)
    assert features["era_diff"] == pytest.approx(0.6)
    assert features["is_weekend"] == 1


@pytest.mark.asyncio
async def test_ingest_games_for_date_impl_saves_only_valid_games_and_caches_them():
    # Given
    valid_game = _game_data(
        game_id="1001",
        home_team_id="10",
        away_team_id="20",
        game_date=datetime(2026, 3, 18, 18, 5, 0),
    )
    missing_fields = _game_data(
        game_id=None,
        home_team_id="10",
        away_team_id="20",
        game_date=datetime(2026, 3, 18, 18, 5, 0),
    )
    non_numeric = _game_data(
        game_id="abc",
        home_team_id="10",
        away_team_id="20",
        game_date=datetime(2026, 3, 18, 18, 5, 0),
    )
    mlb_api = AsyncMock()
    mlb_api.get_games_by_date.return_value = [valid_game, missing_fields, non_numeric]
    repository = AsyncMock()
    cache = AsyncMock()

    # When
    games = await _ingest_games_for_date_impl(mlb_api, repository, cache, date(2026, 3, 18))

    # Then
    assert len(games) == 1
    repository.save.assert_awaited_once()
    cache.set.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_upcoming_predictions_impl_skips_existing_and_counts_new_predictions():
    # Given
    game_repository = AsyncMock()
    game_repository.list_upcoming_games.return_value = [
        _upcoming_game(game_id=None, home_team_id=1, away_team_id=2, game_date=datetime(2026, 3, 18)),
        _upcoming_game(game_id=10, home_team_id=1, away_team_id=2, game_date=datetime(2026, 3, 18)),
        _upcoming_game(game_id=11, home_team_id=3, away_team_id=4, game_date=datetime(2026, 3, 19)),
    ]

    prediction_repository = AsyncMock()
    prediction_repository.list_by_game.side_effect = [[{"id": 1}], []]

    team_stats_repository = AsyncMock()
    team_stats_repository.get_by_team_and_season.side_effect = [{"hitting_stats": {}}, {"hitting_stats": {}}]

    predicted = SimpleNamespace(
        game_id=None,
        prediction_type="winner",
        home_win_probability=0.6,
        away_win_probability=0.4,
        model_version="v1",
    )
    ml_model = AsyncMock()
    ml_model.predict_game_outcome.return_value = predicted
    cache = AsyncMock()

    # When
    result = await _generate_upcoming_predictions_impl(
        game_repository=game_repository,
        prediction_repository=prediction_repository,
        team_stats_repository=team_stats_repository,
        ml_model=ml_model,
        cache=cache,
    )

    # Then
    assert result == {"success": True, "predictions_generated": 1, "total_upcoming_games": 3}
    prediction_repository.save.assert_awaited_once_with(predicted)
    cache.set.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_upcoming_predictions_impl_returns_error_when_repository_fails():
    # Given
    game_repository = AsyncMock()
    game_repository.list_upcoming_games.side_effect = RuntimeError("db down")

    # When
    result = await _generate_upcoming_predictions_impl(
        game_repository=game_repository,
        prediction_repository=AsyncMock(),
        team_stats_repository=AsyncMock(),
        ml_model=AsyncMock(),
        cache=AsyncMock(),
    )

    # Then
    assert result == {"success": False, "error": "db down"}

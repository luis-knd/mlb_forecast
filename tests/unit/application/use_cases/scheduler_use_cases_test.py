from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from application.use_cases import scheduler_use_cases as scheduler_module
from application.use_cases.scheduler_use_cases import (
    SchedulerUseCases,
    _build_team_feature_snapshot,
    _create_game_features_impl,
    _generate_upcoming_predictions_impl,
    _ingest_games_for_date_impl,
    _safe_float,
    _safe_number,
)
from domain.entities.game import Game
from domain.entities.team import Team


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


@pytest.mark.asyncio
async def test_generate_upcoming_predictions_impl_skips_prediction_when_team_stats_are_missing():
    # Given
    game_repository = AsyncMock()
    game_repository.list_upcoming_games.return_value = [
        _upcoming_game(game_id=22, home_team_id=5, away_team_id=7, game_date=datetime(2026, 3, 20))
    ]

    prediction_repository = AsyncMock()
    prediction_repository.list_by_game.return_value = []

    team_stats_repository = AsyncMock()
    team_stats_repository.get_by_team_and_season.side_effect = [None, {"hitting_stats": {}}]

    ml_model = AsyncMock()
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
    assert result == {"success": True, "predictions_generated": 0, "total_upcoming_games": 1}
    ml_model.predict_game_outcome.assert_not_awaited()
    prediction_repository.save.assert_not_awaited()
    cache.set.assert_not_awaited()


@pytest.fixture
def scheduler_use_cases_fixture():
    # Given
    return SchedulerUseCases(
        db_session=AsyncMock(),
        cache=AsyncMock(),
        ml_model=AsyncMock(),
        mlb_api=AsyncMock(),
        game_repository=AsyncMock(),
        team_repository=AsyncMock(),
        team_stats_repository=AsyncMock(),
        prediction_repository=AsyncMock(),
    )


@pytest.mark.asyncio
async def test_ingest_daily_games_returns_aggregated_counts(scheduler_use_cases_fixture):
    # Given
    scheduler_use_cases_fixture._ingest_games_for_date = AsyncMock(side_effect=[[1, 2], [3], [4, 5, 6]])

    # When
    result = await scheduler_use_cases_fixture.ingest_daily_games()

    # Then
    assert result == {
        "success": True,
        "total_games": 6,
        "games_today": 2,
        "games_yesterday": 1,
        "games_tomorrow": 3,
    }


@pytest.mark.asyncio
async def test_ingest_daily_games_returns_error_when_inner_ingestion_fails(scheduler_use_cases_fixture):
    # Given
    scheduler_use_cases_fixture._ingest_games_for_date = AsyncMock(side_effect=RuntimeError("calendar unavailable"))

    # When
    result = await scheduler_use_cases_fixture.ingest_daily_games()

    # Then
    assert result == {"success": False, "error": "calendar unavailable"}


@pytest.mark.asyncio
async def test_ingest_team_statistics_skips_invalid_teams_and_missing_stats(scheduler_use_cases_fixture):
    # Given
    valid_team = Team.create(mlb_id=10, name="A", abbreviation="A", city="A", division="E", league="AL")
    valid_team.id = 99
    missing_id_team = Team.create(mlb_id=11, name="B", abbreviation="B", city="B", division="E", league="AL")

    scheduler_use_cases_fixture.team_repository.list_all.return_value = [valid_team, missing_id_team]
    scheduler_use_cases_fixture.mlb_api.get_team_stats.side_effect = [
        {"games_played": 20, "wins": 11, "losses": 9, "runs_scored": 88, "runs_allowed": 80, "ops": 0.75},
    ]

    # When
    result = await scheduler_use_cases_fixture.ingest_team_statistics()

    # Then
    assert result == {"success": True, "teams_updated": 1}
    scheduler_use_cases_fixture.team_stats_repository.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_retrain_ml_model_returns_error_when_not_enough_games(scheduler_use_cases_fixture):
    # Given
    scheduler_use_cases_fixture.game_repository.list_by_status.return_value = [SimpleNamespace()] * 10

    # When
    result = await scheduler_use_cases_fixture.retrain_ml_model()

    # Then
    assert result == {"success": False, "error": "Insufficient historical data for training"}


@pytest.mark.asyncio
async def test_cache_maintenance_returns_before_and_after_stats(scheduler_use_cases_fixture):
    # Given
    scheduler_use_cases_fixture.cache.get_stats.side_effect = [
        {"used_memory": "10MB", "hit_rate": 20},
        {"used_memory": "7MB", "hit_rate": 35},
    ]
    scheduler_use_cases_fixture.cache.clear.return_value = 5

    # When
    result = await scheduler_use_cases_fixture.cache_maintenance()

    # Then
    assert result == {
        "success": True,
        "cleared_predictions": 5,
        "memory_before": "10MB",
        "memory_after": "7MB",
        "hit_rate": 35,
    }


@pytest.mark.asyncio
async def test_ingest_teams_weekly_saves_only_positive_ids(scheduler_use_cases_fixture):
    # Given
    scheduler_use_cases_fixture.mlb_api.get_teams.return_value = [
        SimpleNamespace(id=22, name="X", abbreviation="XX", city="City", division="West", league="NL"),
        SimpleNamespace(id=0, name="Y", abbreviation="YY", city="City", division="West", league="NL"),
    ]

    # When
    result = await scheduler_use_cases_fixture.ingest_teams_weekly()

    # Then
    assert result == {"success": True, "teams_ingested": 1}
    scheduler_use_cases_fixture.team_repository.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_upcoming_predictions_delegates_to_module_impl(scheduler_use_cases_fixture, monkeypatch):
    # Given
    expected = {"success": True, "predictions_generated": 4, "total_upcoming_games": 4}

    async def _fake_generate(**_kwargs):
        return expected

    monkeypatch.setattr(scheduler_module, "_generate_upcoming_predictions_impl", _fake_generate)

    # When
    result = await scheduler_use_cases_fixture.generate_upcoming_predictions()

    # Then
    assert result == expected


@pytest.mark.asyncio
async def test_retrain_ml_model_trains_with_engineered_features(scheduler_use_cases_fixture):
    # Given
    completed_games = [
        SimpleNamespace(
            home_team_id=10,
            away_team_id=20,
            game_date=datetime(2026, 4, 1, 19, 0, 0),
            winning_team_id=10,
            home_score=5,
            away_score=2,
        )
        for _ in range(50)
    ]
    scheduler_use_cases_fixture.game_repository.list_by_status.return_value = completed_games
    scheduler_use_cases_fixture.team_stats_repository.get_by_team_and_season.side_effect = [
        {"hitting_stats": {"games_played": 10, "runs_scored": 40, "ops": 0.8}, "pitching_stats": {"wins": 6}},
        {"hitting_stats": {"games_played": 10, "runs_scored": 30, "ops": 0.7}, "pitching_stats": {"wins": 4}},
    ] * 50
    scheduler_use_cases_fixture.ml_model.train.return_value = {"accuracy": 0.79}

    # When
    result = await scheduler_use_cases_fixture.retrain_ml_model()

    # Then
    assert result == {"success": True, "model_updated": True, "metrics": {"accuracy": 0.79}}
    scheduler_use_cases_fixture.ml_model.train.assert_awaited_once()
    trained_payload = scheduler_use_cases_fixture.ml_model.train.await_args.args[0]
    assert len(trained_payload) == 50
    assert trained_payload[0]["winner"] == 1
    assert trained_payload[0]["total_runs"] == 7


@pytest.mark.asyncio
async def test_retrain_ml_model_returns_error_when_training_raises(scheduler_use_cases_fixture):
    # Given
    completed_games = [
        SimpleNamespace(
            home_team_id=10,
            away_team_id=20,
            game_date=datetime(2026, 4, 1, 19, 0, 0),
            winning_team_id=20,
            home_score=1,
            away_score=3,
        )
        for _ in range(50)
    ]
    scheduler_use_cases_fixture.game_repository.list_by_status.return_value = completed_games
    scheduler_use_cases_fixture.team_stats_repository.get_by_team_and_season.side_effect = [
        {"hitting_stats": {"games_played": 10}, "pitching_stats": {"wins": 6}},
        {"hitting_stats": {"games_played": 10}, "pitching_stats": {"wins": 4}},
    ] * 50
    scheduler_use_cases_fixture.ml_model.train.side_effect = RuntimeError("model training failed")

    # When
    result = await scheduler_use_cases_fixture.retrain_ml_model()

    # Then
    assert result == {"success": False, "error": "model training failed"}


@pytest.mark.asyncio
async def test_ingest_games_for_date_delegates_to_impl_with_dependencies(scheduler_use_cases_fixture, monkeypatch):
    # Given
    expected_games = [SimpleNamespace(id=1), SimpleNamespace(id=2)]

    async def _fake_ingest(*, mlb_api, game_repository, cache, date_obj):
        assert mlb_api is scheduler_use_cases_fixture.mlb_api
        assert game_repository is scheduler_use_cases_fixture.game_repository
        assert cache is scheduler_use_cases_fixture.cache
        assert date_obj == date(2026, 4, 1)
        return expected_games

    monkeypatch.setattr(scheduler_module, "_ingest_games_for_date_impl", _fake_ingest)

    # When
    result = await scheduler_use_cases_fixture._ingest_games_for_date(date(2026, 4, 1))

    # Then
    assert result == expected_games


def test_create_game_features_method_delegates_to_impl(scheduler_use_cases_fixture, monkeypatch):
    # Given
    game = Game.create(
        mlb_game_id=77,
        home_team_id=1,
        away_team_id=2,
        game_date=datetime(2026, 4, 4, 15, 0, 0),
        status="scheduled",
    )

    expected_features = {"home_win_percentage": 0.7}

    def _fake_create(home_team_stats, away_team_stats, game_obj):
        assert home_team_stats == {"hitting_stats": {"games_played": 10}}
        assert away_team_stats == {"hitting_stats": {"games_played": 10}}
        assert game_obj is game
        return expected_features

    monkeypatch.setattr(scheduler_module, "_create_game_features_impl", _fake_create)

    # When
    result = scheduler_use_cases_fixture._create_game_features(
        {"hitting_stats": {"games_played": 10}},
        {"hitting_stats": {"games_played": 10}},
        game,
    )

    # Then
    assert result == expected_features

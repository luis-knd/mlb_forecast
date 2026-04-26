from datetime import date, datetime

import pytest

from application.ports.cache import CachePort
from application.ports.catching_stats_repository import CatchingStatsRepositoryPort
from application.ports.fielding_stats_repository import FieldingStatsRepositoryPort
from application.ports.game_repository import GameRepositoryPort
from application.ports.hitting_stats_repository import HittingStatsRepositoryPort
from application.ports.ml_model import MLModelPort
from application.ports.mlb_api import MLBApiPort
from application.ports.pitching_stats_repository import PitchingStatsRepositoryPort
from application.ports.player_repository import PlayerRepositoryPort
from application.ports.prediction_repository import PredictionRepositoryPort
from application.ports.scheduler import SchedulerPort
from application.ports.team_repository import TeamRepositoryPort
from application.ports.team_stats_repository import TeamStatsRepositoryPort


class _DummyPort:
    pass


@pytest.mark.asyncio
async def test_cache_port_abstract_methods_execute_default_bodies():
    # Given
    port = _DummyPort()

    # When
    get_result = await CachePort.get(port, "k")
    set_result = await CachePort.set(port, "k", "v", ttl=30)
    delete_result = await CachePort.delete(port, "k")
    delete_pattern_result = await CachePort.delete_pattern(port, "mlb:*")
    exists_result = await CachePort.exists(port, "k")
    clear_result = await CachePort.clear(port, pattern="mlb:*")
    get_many_result = await CachePort.get_many(port, ["a", "b"])
    set_many_result = await CachePort.set_many(port, {"a": 1}, ttl=15)
    delete_many_result = await CachePort.delete_many(port, ["a", "b"])
    increment_result = await CachePort.increment(port, "counter", amount=2)
    decrement_result = await CachePort.decrement(port, "counter", amount=1)
    stats_result = await CachePort.get_stats(port)

    # Then
    assert get_result is None
    assert set_result is None
    assert delete_result is None
    assert delete_pattern_result is None
    assert exists_result is None
    assert clear_result is None
    assert get_many_result is None
    assert set_many_result is None
    assert delete_many_result is None
    assert increment_result is None
    assert decrement_result is None
    assert stats_result is None


@pytest.mark.asyncio
async def test_scheduler_port_abstract_methods_execute_default_bodies():
    # Given
    port = _DummyPort()

    # When
    initialize_result = await SchedulerPort.initialize(port)
    start_result = await SchedulerPort.start(port)
    stop_result = await SchedulerPort.stop(port)
    add_job_result = await SchedulerPort.add_job(port, "daily", lambda: None, "cron", hour=1)
    remove_job_result = await SchedulerPort.remove_job(port, "daily")
    get_jobs_result = await SchedulerPort.get_jobs(port)
    get_job_result = await SchedulerPort.get_job(port, "daily")

    # Then
    assert initialize_result is None
    assert start_result is None
    assert stop_result is None
    assert add_job_result is None
    assert remove_job_result is None
    assert get_jobs_result is None
    assert get_job_result is None


@pytest.mark.asyncio
async def test_game_repository_port_abstract_methods_execute_default_bodies():
    # Given
    port = _DummyPort()

    # When
    by_id_result = await GameRepositoryPort.get_by_id(port, 1)
    by_mlb_id_result = await GameRepositoryPort.get_by_mlb_id(port, 100)
    by_date_result = await GameRepositoryPort.list_by_date(port, date(2026, 4, 1))
    by_team_result = await GameRepositoryPort.list_by_team(port, 7, limit=5)
    by_status_result = await GameRepositoryPort.list_by_status(port, "completed", limit=10)
    upcoming_result = await GameRepositoryPort.list_upcoming_games(port, days_ahead=3, limit=15)
    matchups_result = await GameRepositoryPort.list_historical_matchups(port, 1, 2, limit=4)
    save_result = await GameRepositoryPort.save(port, game=None)
    update_result = await GameRepositoryPort.update_game_result(port, 9, 3, 1, status="completed")
    delete_result = await GameRepositoryPort.delete(port, 9)

    # Then
    assert by_id_result is None
    assert by_mlb_id_result is None
    assert by_date_result is None
    assert by_team_result is None
    assert by_status_result is None
    assert upcoming_result is None
    assert matchups_result is None
    assert save_result is None
    assert update_result is None
    assert delete_result is None


@pytest.mark.asyncio
async def test_remaining_core_ports_execute_abstract_default_bodies():
    # Given
    port = _DummyPort()

    # When
    mlb_api_results = [
        await MLBApiPort.get_teams(port),
        await MLBApiPort.get_team_by_id(port, 1),
        await MLBApiPort.get_games_by_date(port, date(2026, 4, 1)),
        await MLBApiPort.get_game_by_id(port, 10),
        await MLBApiPort.get_team_stats(port, 2026, "hitting", 1),
        await MLBApiPort.get_player_by_id(port, 2),
        await MLBApiPort.get_players_by_team(port, 1, season=2026, roster_type="active"),
        await MLBApiPort.get_players_by_sport(port, sport_id=1, season=2026, team_mlb_id=1),
        await MLBApiPort.get_player_stats(port, 2, "season", "hitting", season=2026),
        await MLBApiPort.search_players(port, "Judge"),
    ]
    ml_model_results = [
        await MLModelPort.train(port, []),
        await MLModelPort.predict_game_outcome(port, {}, {}, datetime(2026, 4, 1)),
        await MLModelPort.evaluate_model(port, []),
        await MLModelPort.get_feature_importance(port),
        await MLModelPort.save_model(port, "model.pkl"),
        await MLModelPort.load_model(port, "model.pkl"),
        await MLModelPort.get_model_version(port),
        await MLModelPort.get_model_performance(port),
    ]
    prediction_results = [
        await PredictionRepositoryPort.get_by_id(port, 1),
        await PredictionRepositoryPort.list_by_game(port, 1),
        await PredictionRepositoryPort.list_by_game_and_type(port, 1, "winner"),
        await PredictionRepositoryPort.list_latest_predictions(port, limit=5),
        await PredictionRepositoryPort.list_by_model_version(port, "v1", limit=5),
        await PredictionRepositoryPort.save(port, prediction=None),
        await PredictionRepositoryPort.update_with_actual_result(port, 1, {"winner": "home"}, 0.8),
        await PredictionRepositoryPort.delete(port, 1),
        await PredictionRepositoryPort.get_prediction_accuracy_by_model(port, "v1"),
    ]
    team_results = [
        await TeamRepositoryPort.get_by_id(port, 1),
        await TeamRepositoryPort.get_by_mlb_id(port, 10),
        await TeamRepositoryPort.list_all(port),
        await TeamRepositoryPort.list_by_league(port, "AL"),
        await TeamRepositoryPort.list_by_division(port, "East"),
        await TeamRepositoryPort.list_by_league_and_division(port, "AL", "East"),
        await TeamRepositoryPort.save(port, team=None),
        await TeamRepositoryPort.delete(port, 1),
    ]
    team_stats_results = [
        await TeamStatsRepositoryPort.get_by_id(port, 1),
        await TeamStatsRepositoryPort.get_by_team_and_season(port, 1, 2026),
        await TeamStatsRepositoryPort.list_by_team(port, 1),
        await TeamStatsRepositoryPort.list_by_season(port, 2026),
        await TeamStatsRepositoryPort.list_top_teams_by_stat(port, 2026, "ops", limit=5, descending=True),
        await TeamStatsRepositoryPort.save(port, team_stats=None),
        await TeamStatsRepositoryPort.update_stats(port, 1, {"ops": 0.8}),
        await TeamStatsRepositoryPort.delete(port, 1),
    ]
    player_results = [
        await PlayerRepositoryPort.get_by_id(port, 1),
        await PlayerRepositoryPort.get_by_mlb_id(port, 2),
        await PlayerRepositoryPort.list_by_team(port, 3),
        await PlayerRepositoryPort.list_by_position(port, "P"),
        await PlayerRepositoryPort.list_active_players(port),
        await PlayerRepositoryPort.list_players(port, team_id=3, position="P", active=True, limit=10, offset=0),
        await PlayerRepositoryPort.search_by_name(port, "Soto"),
        await PlayerRepositoryPort.save(port, player=None),
        await PlayerRepositoryPort.update_team(port, 1, 3),
        await PlayerRepositoryPort.delete(port, 1),
    ]

    # Then
    assert all(result is None for result in mlb_api_results)
    assert all(result is None for result in ml_model_results)
    assert all(result is None for result in prediction_results)
    assert all(result is None for result in team_results)
    assert all(result is None for result in team_stats_results)
    assert all(result is None for result in player_results)


@pytest.mark.asyncio
async def test_team_stats_detail_ports_execute_abstract_default_bodies():
    # Given
    port = _DummyPort()

    # When
    hitting_results = [
        await HittingStatsRepositoryPort.get_by_id(port, 1),
        await HittingStatsRepositoryPort.get_by_team_and_season(port, 2, 2026),
        await HittingStatsRepositoryPort.list_by_team(port, 2),
        await HittingStatsRepositoryPort.list_by_season(port, 2026),
        await HittingStatsRepositoryPort.list_top_teams_by_stat(port, 2026, "ops", limit=5),
        await HittingStatsRepositoryPort.save(port, hitting_stats=None),
        await HittingStatsRepositoryPort.update_stats(port, 1, {"ops": 0.78}),
        await HittingStatsRepositoryPort.delete(port, 1),
    ]
    pitching_results = [
        await PitchingStatsRepositoryPort.get_by_id(port, 1),
        await PitchingStatsRepositoryPort.get_by_team_and_season(port, 2, 2026),
        await PitchingStatsRepositoryPort.list_by_team(port, 2),
        await PitchingStatsRepositoryPort.list_by_season(port, 2026),
        await PitchingStatsRepositoryPort.list_top_teams_by_stat(port, 2026, "earned_run_average", limit=5),
        await PitchingStatsRepositoryPort.save(port, pitching_stats=None),
        await PitchingStatsRepositoryPort.update_stats(port, 1, {"earned_run_average": 3.2}),
        await PitchingStatsRepositoryPort.delete(port, 1),
    ]
    fielding_results = [
        await FieldingStatsRepositoryPort.get_by_id(port, 1),
        await FieldingStatsRepositoryPort.get_by_team_and_season(port, 2, 2026),
        await FieldingStatsRepositoryPort.list_by_team(port, 2),
        await FieldingStatsRepositoryPort.list_by_season(port, 2026),
        await FieldingStatsRepositoryPort.list_top_teams_by_stat(port, 2026, "fielding_percentage", limit=5),
        await FieldingStatsRepositoryPort.save(port, fielding_stats=None),
        await FieldingStatsRepositoryPort.update_stats(port, 1, {"errors": 10}),
        await FieldingStatsRepositoryPort.delete(port, 1),
    ]
    catching_results = [
        await CatchingStatsRepositoryPort.get_by_id(port, 1),
        await CatchingStatsRepositoryPort.get_by_team_and_season(port, 2, 2026),
        await CatchingStatsRepositoryPort.list_by_team(port, 2),
        await CatchingStatsRepositoryPort.list_by_season(port, 2026),
        await CatchingStatsRepositoryPort.list_top_teams_by_stat(port, 2026, "caught_stealing", limit=5),
        await CatchingStatsRepositoryPort.save(port, catching_stats=None),
        await CatchingStatsRepositoryPort.update_stats(port, 1, {"passed_balls": 2}),
        await CatchingStatsRepositoryPort.delete(port, 1),
    ]

    # Then
    assert all(result is None for result in hitting_results)
    assert all(result is None for result in pitching_results)
    assert all(result is None for result in fielding_results)
    assert all(result is None for result in catching_results)

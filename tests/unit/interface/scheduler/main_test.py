from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from interface.scheduler import main


@pytest.mark.parametrize(
    "expected_job_ids",
    [
        [
            "ingest_daily_games",
            "ingest_team_statistics",
            "retrain_ml_model",
            "cache_maintenance",
            "generate_upcoming_predictions",
            "ingest_teams_weekly",
        ]
    ],
)
def test_job_definitions_include_expected_ids(expected_job_ids):
    # Given
    scheduler_use_cases = MagicMock()

    # When
    jobs = main._job_definitions(scheduler_use_cases)

    # Then
    assert [job["job_id"] for job in jobs] == expected_job_ids


@pytest.mark.asyncio
async def test_register_jobs_adds_every_defined_job():
    # Given
    scheduler_adapter = AsyncMock()
    scheduler_use_cases = MagicMock()

    # When
    await main._register_jobs(scheduler_adapter, scheduler_use_cases)

    # Then
    assert scheduler_adapter.add_job.await_count == 6


@pytest.mark.asyncio
@patch("interface.scheduler.main.logger")
async def test_load_current_model_logs_warning_when_loading_fails(logger_mock):
    # Given
    ml_model_adapter = AsyncMock()
    ml_model_adapter.load_model.side_effect = RuntimeError("missing model")

    # When
    await main._load_current_model(ml_model_adapter)

    # Then
    logger_mock.warning.assert_called_once()


@pytest.mark.asyncio
@patch("interface.scheduler.main._register_jobs", new_callable=AsyncMock)
@patch("interface.scheduler.main._load_current_model", new_callable=AsyncMock)
@patch("interface.scheduler.main.SchedulerUseCases")
@patch("interface.scheduler.main._build_repositories")
@patch("interface.scheduler.main.SessionLocal")
@patch("interface.scheduler.main._build_adapters")
async def test_setup_scheduler_initializes_and_starts_components(
    build_adapters_mock,
    session_local_mock,
    build_repositories_mock,
    scheduler_use_cases_mock,
    load_current_model_mock,
    register_jobs_mock,
):
    # Given
    cache_adapter = AsyncMock()
    ml_model_adapter = AsyncMock()
    mlb_api_adapter = MagicMock()
    scheduler_adapter = AsyncMock()
    build_adapters_mock.return_value = (cache_adapter, ml_model_adapter, mlb_api_adapter, scheduler_adapter)

    db_session = MagicMock()
    session_local_mock.return_value = db_session

    build_repositories_mock.return_value = (MagicMock(), MagicMock(), MagicMock(), MagicMock())

    scheduler_use_cases = MagicMock()
    scheduler_use_cases_mock.return_value = scheduler_use_cases

    # When
    setup_result = await main.setup_scheduler()

    # Then
    assert setup_result == (scheduler_adapter, cache_adapter)
    cache_adapter.connect.assert_awaited_once()
    scheduler_adapter.initialize.assert_awaited_once()
    register_jobs_mock.assert_awaited_once_with(scheduler_adapter, scheduler_use_cases)
    scheduler_adapter.start.assert_awaited_once()
    load_current_model_mock.assert_awaited_once_with(ml_model_adapter)


@pytest.mark.asyncio
@patch("interface.scheduler.main.logger")
@patch("interface.scheduler.main.setup_scheduler", new_callable=AsyncMock)
@patch("interface.scheduler.main.asyncio.sleep", new_callable=AsyncMock)
async def test_main_handles_keyboard_interrupt(sleep_mock, setup_mock, logger_mock):
    # Given
    scheduler_adapter = AsyncMock()
    cache_adapter = AsyncMock()
    setup_mock.return_value = (scheduler_adapter, cache_adapter)
    sleep_mock.side_effect = KeyboardInterrupt()

    # When
    await main.main()

    # Then
    scheduler_adapter.stop.assert_awaited_once()
    cache_adapter.disconnect.assert_awaited_once()
    logger_mock.info.assert_any_call("⏹️ Interrupt received, shutting down...")


@pytest.mark.asyncio
@patch("interface.scheduler.main.logger")
@patch("interface.scheduler.main.setup_scheduler", new_callable=AsyncMock)
@patch("interface.scheduler.main.asyncio.sleep", new_callable=AsyncMock)
async def test_main_handles_general_exception_and_cleanup(sleep_mock, setup_mock, logger_mock):
    # Given
    scheduler_adapter = AsyncMock()
    cache_adapter = AsyncMock()
    setup_mock.return_value = (scheduler_adapter, cache_adapter)
    sleep_mock.side_effect = RuntimeError("boom")

    # When
    await main.main()

    # Then
    logger_mock.error.assert_called_once()
    scheduler_adapter.stop.assert_awaited_once()
    cache_adapter.disconnect.assert_awaited_once()


def test_build_adapters_and_repositories_helpers(monkeypatch):
    # Given
    fake_cache = MagicMock()
    fake_ml = MagicMock()
    fake_api = MagicMock()
    fake_scheduler = MagicMock()
    monkeypatch.setattr(main, "RedisAdapter", MagicMock(return_value=fake_cache))
    monkeypatch.setattr(main, "MLModelAdapter", MagicMock(return_value=fake_ml))
    monkeypatch.setattr(main, "MLBApiAdapter", MagicMock(return_value=fake_api))
    monkeypatch.setattr(main, "SchedulerAdapter", MagicMock(return_value=fake_scheduler))

    # When
    adapters = main._build_adapters()
    repositories = main._build_repositories(MagicMock())

    # Then
    assert adapters == (fake_cache, fake_ml, fake_api, fake_scheduler)
    assert len(repositories) == 4

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from infrastructure.jobs.scheduler_adapter import SchedulerAdapter, SchedulerException


def _build_adapter_with_mocked_scheduler() -> SchedulerAdapter:
    adapter = SchedulerAdapter()
    adapter.scheduler = MagicMock()
    return adapter


@pytest.mark.asyncio
async def test_start_and_stop_toggle_running_state():
    # Given
    adapter = _build_adapter_with_mocked_scheduler()

    # When
    await adapter.start()
    await adapter.stop()

    # Then
    assert adapter.is_running is False
    adapter.scheduler.start.assert_called_once()
    adapter.scheduler.shutdown.assert_called_once_with(wait=False)


@pytest.mark.asyncio
async def test_add_job_rejects_unknown_trigger_type():
    # Given
    adapter = SchedulerAdapter()

    # When / Then
    with pytest.raises(SchedulerException, match="Unknown trigger type"):
        await adapter.add_job(job_id="job-x", func=lambda: None, trigger_type="unsupported")


@pytest.mark.asyncio
async def test_add_job_passes_expected_job_defaults():
    # Given
    adapter = _build_adapter_with_mocked_scheduler()

    # When
    await adapter.add_job(job_id="interval-job", func=lambda: None, trigger_type="interval", minutes=15)

    # Then
    call_kwargs = adapter.scheduler.add_job.call_args.kwargs
    assert call_kwargs["id"] == "interval-job"
    assert call_kwargs["name"] == "interval-job"
    assert call_kwargs["max_instances"] == 1
    assert call_kwargs["coalesce"] is True
    assert call_kwargs["misfire_grace_time"] == 300


@pytest.mark.asyncio
async def test_get_job_returns_none_when_missing():
    # Given
    adapter = _build_adapter_with_mocked_scheduler()
    adapter.scheduler.get_job.return_value = None

    # When
    job = await adapter.get_job("missing")

    # Then
    assert job is None


@pytest.mark.asyncio
async def test_get_job_returns_serialized_job_details():
    # Given
    adapter = _build_adapter_with_mocked_scheduler()
    adapter.scheduler.get_job.return_value = SimpleNamespace(
        id="job-1",
        name="job one",
        next_run_time=datetime(2026, 3, 18, 12, 0, 0),
        trigger="interval[0:30:00]",
        max_instances=1,
        pending=False,
    )

    # When
    response = await adapter.get_job("job-1")

    # Then
    assert response == {
        "id": "job-1",
        "name": "job one",
        "next_run": "2026-03-18T12:00:00",
        "trigger": "interval[0:30:00]",
        "max_instances": 1,
        "pending": False,
    }


@pytest.mark.asyncio
async def test_remove_job_returns_false_when_scheduler_raises_exception():
    # Given
    adapter = _build_adapter_with_mocked_scheduler()
    adapter.scheduler.remove_job.side_effect = RuntimeError("missing job")

    # When
    removed = await adapter.remove_job("unknown-job")

    # Then
    assert removed is False


@pytest.mark.asyncio
async def test_initialize_start_stop_warning_and_exception_paths(monkeypatch):
    # Given
    adapter = _build_adapter_with_mocked_scheduler()

    # When
    await adapter.initialize()
    await adapter.start()
    await adapter.start()  # already running branch
    await adapter.stop()
    await adapter.stop()  # not running branch

    # Then
    assert adapter.is_running is False

    # Given exception path
    failing = _build_adapter_with_mocked_scheduler()
    failing.scheduler.start.side_effect = RuntimeError("boom")

    # When / Then
    with pytest.raises(SchedulerException):
        await failing.start()


@pytest.mark.asyncio
async def test_add_remove_get_jobs_and_status_paths():
    # Given
    adapter = _build_adapter_with_mocked_scheduler()
    adapter.scheduler.get_jobs.return_value = [
        SimpleNamespace(
            id="j1",
            name="Job 1",
            next_run_time=datetime(2026, 1, 1, 10, 0),
            trigger="interval",
            max_instances=1,
            pending=False,
        )
    ]

    # When
    await adapter.add_job(job_id="cron-job", func=lambda: None, trigger_type="cron", hour=1, minute=0)
    await adapter.add_job(job_id="date-job", func=lambda: None, trigger_type="date", run_date=datetime(2026, 1, 1))
    removed = await adapter.remove_job("j1")
    jobs = await adapter.get_jobs()
    status_info = adapter.get_status()

    # Then
    assert removed is True
    assert len(jobs) == 1
    assert status_info["total_jobs"] == 1
    assert status_info["jobs"] == jobs

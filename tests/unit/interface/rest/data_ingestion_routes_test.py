import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from interface.rest import data_ingestion_routes as data_ingestion_routes_module
from interface.rest.exception_handlers import DomainExceptions
from interface.rest.data_ingestion_routes import get_data_ingestion_use_cases


def test_get_data_ingestion_use_cases_success():
    """
    Verify get_data_ingestion_use_cases initializes correctly.
    """
    mock_db = MagicMock()

    # Should not raise any error now
    use_cases = get_data_ingestion_use_cases(db=mock_db)

    assert "ingest_teams" in use_cases
    assert use_cases["ingest_teams"] is not None


def test_validate_ingestion_params_rejects_invalid_ranges():
    # Given / When / Then
    with pytest.raises(DomainExceptions.InvalidDataError, match="Season must be between"):
        data_ingestion_routes_module._validate_ingestion_params(season=1800, days_back=7)

    with pytest.raises(DomainExceptions.InvalidDataError, match="Days back must be between 1 and 30"):
        data_ingestion_routes_module._validate_ingestion_params(season=datetime.now().year, days_back=0)


def test_count_team_stats_payload_returns_sum_for_all_sections():
    # Given
    payload = {
        "hitting_stats": [1, 2],
        "pitching_stats": [3],
        "fielding_stats": [],
        "catching_stats": [4, 5, 6],
    }

    # When
    total = data_ingestion_routes_module._count_team_stats_payload(payload)

    # Then
    assert total == 6


@pytest.mark.asyncio
async def test_run_ingestion_step_updates_success_and_count():
    # Given
    results = data_ingestion_routes_module._new_ingestion_results()
    errors = []

    async def _executor():
        return ["a", "b", "c"]

    # When
    count = await data_ingestion_routes_module._run_ingestion_step("teams", _executor, results, errors)

    # Then
    assert count == 3
    assert results["teams"]["success"] is True
    assert results["teams"]["count"] == 3
    assert errors == []


@pytest.mark.asyncio
async def test_run_ingestion_step_captures_errors_without_throwing():
    # Given
    results = data_ingestion_routes_module._new_ingestion_results()
    errors = []

    async def _executor():
        raise RuntimeError("step failed")

    # When
    count = await data_ingestion_routes_module._run_ingestion_step("games", _executor, results, errors)

    # Then
    assert count == 0
    assert results["games"]["success"] is False
    assert results["games"]["error"] == "step failed"
    assert errors == ["Games ingestion failed: step failed"]


@pytest.mark.asyncio
async def test_collect_ingestion_results_aggregates_counts_from_all_steps():
    # Given
    use_cases = {
        "ingest_teams": AsyncMock(execute=AsyncMock(return_value=["t1"])),
        "ingest_games": AsyncMock(execute=AsyncMock(return_value=["g1", "g2"])),
        "ingest_all_team_stats": AsyncMock(
            execute=AsyncMock(return_value={"hitting_stats": [1], "pitching_stats": [2], "fielding_stats": [], "catching_stats": [3]})
        ),
    }

    # When
    results, total_records, errors = await data_ingestion_routes_module._collect_ingestion_results(
        use_cases=use_cases,
        season=2026,
        days_back=5,
    )

    # Then
    assert total_records == 5
    assert errors == []
    assert results["teams"]["count"] == 1
    assert results["games"]["count"] == 2
    assert results["team_stats"]["count"] == 3


def test_build_ingestion_response_raises_external_service_error_when_any_step_fails():
    # Given
    start_time = datetime(2026, 4, 25, 10, 0, 0)
    ingestion_results = data_ingestion_routes_module._new_ingestion_results()
    ingestion_results["teams"]["success"] = True
    ingestion_results["teams"]["count"] = 5
    errors = ["Teams ingestion failed: timeout"]

    # When / Then
    with pytest.raises(DomainExceptions.ExternalServiceError, match="Data Ingestion"):
        data_ingestion_routes_module._build_ingestion_response(
            season=2026,
            start_time=start_time,
            ingestion_results=ingestion_results,
            total_records=5,
            errors=errors,
        )


def test_build_ingestion_response_returns_created_payload_on_success():
    # Given
    start_time = datetime(2026, 4, 25, 10, 0, 0)
    ingestion_results = data_ingestion_routes_module._new_ingestion_results()
    ingestion_results["teams"].update({"success": True, "count": 2})
    ingestion_results["games"].update({"success": True, "count": 3})
    ingestion_results["team_stats"].update({"success": True, "count": 4})

    # When
    response = data_ingestion_routes_module._build_ingestion_response(
        season=2026,
        start_time=start_time,
        ingestion_results=ingestion_results,
        total_records=9,
        errors=[],
    )
    payload = json.loads(response.body)

    # Then
    assert response.status_code == 201
    assert payload["status"] == "success"
    assert payload["data"]["teams_ingested"] == 2
    assert payload["data"]["games_ingested"] == 3
    assert payload["data"]["stats_ingested"] == 4


@pytest.mark.asyncio
async def test_ingest_full_data_wraps_mlb_api_related_errors(monkeypatch):
    # Given
    async def _boom_collect(**_kwargs):
        raise RuntimeError("MLB API timeout")

    monkeypatch.setattr(data_ingestion_routes_module, "_collect_ingestion_results", _boom_collect)
    use_cases = {"ingest_teams": AsyncMock(), "ingest_games": AsyncMock(), "ingest_all_team_stats": AsyncMock()}

    # When / Then
    with pytest.raises(DomainExceptions.ExternalServiceError, match="MLB API"):
        await data_ingestion_routes_module.ingest_full_data(season=2026, days_back=7, use_cases=use_cases)

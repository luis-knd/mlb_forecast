import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from domain.value_objects.team_stats_category import TeamStatsCategory
from interface.rest.exception_handlers import DomainExceptions
from interface.rest.team_stats_retrieval_routes import (
    _parse_season_year,
    _resolve_stats_category,
    _validate_season_range,
    get_team_stats,
    get_team_stats_use_cases,
)


def _decode(response) -> dict:
    return json.loads(response.body)


def test_parse_season_year_parses_integer_values():
    # Given / When
    season = _parse_season_year("2024")

    # Then
    assert season == 2024


@pytest.mark.parametrize("season", [None, "abc", "20.5"])
def test_parse_season_year_raises_http_422_for_invalid_values(season):
    # Given / When / Then
    with pytest.raises(HTTPException, match="season must be an integer year"):
        _parse_season_year(season)


@patch("interface.rest.team_stats_retrieval_routes.datetime")
def test_validate_season_range_accepts_window(datetime_mock):
    # Given
    datetime_mock.now.return_value = datetime(2026, 4, 25, 12, 0, 0)

    # When / Then
    _validate_season_range(1996)
    _validate_season_range(2026)


@patch("interface.rest.team_stats_retrieval_routes.datetime")
def test_validate_season_range_rejects_out_of_window(datetime_mock):
    # Given
    datetime_mock.now.return_value = datetime(2026, 4, 25, 12, 0, 0)

    # When / Then
    with pytest.raises(DomainExceptions.InvalidDataError, match="Season must be between 1996 and 2026"):
        _validate_season_range(1995)

    with pytest.raises(DomainExceptions.InvalidDataError, match="Season must be between 1996 and 2026"):
        _validate_season_range(2027)


def test_resolve_stats_category_defaults_to_all_for_empty_values():
    # Given / When / Then
    assert _resolve_stats_category(None) is TeamStatsCategory.ALL
    assert _resolve_stats_category("  ") is TeamStatsCategory.ALL


@pytest.mark.parametrize(
    ("raw_category", "expected"),
    [
        ("hitting", TeamStatsCategory.HITTING),
        ("PITCHING", TeamStatsCategory.PITCHING),
        (" fielding ", TeamStatsCategory.FIELDING),
        ("catching", TeamStatsCategory.CATCHING),
    ],
)
def test_resolve_stats_category_supports_case_and_whitespace(raw_category, expected):
    # Given / When
    category = _resolve_stats_category(raw_category)

    # Then
    assert category is expected


def test_resolve_stats_category_rejects_unknown_values():
    # Given / When / Then
    with pytest.raises(HTTPException, match="category must be one of"):
        _resolve_stats_category("invalid")


@patch("interface.rest.team_stats_retrieval_routes.GetTeamStatsUseCase")
@patch("interface.rest.team_stats_retrieval_routes.TeamStatsRepository")
def test_get_team_stats_use_cases_wires_dependencies(team_stats_repository_cls, get_team_stats_use_case_cls):
    # Given
    db = MagicMock()
    cache_adapter = AsyncMock()
    repository = MagicMock()
    use_case = MagicMock()
    team_stats_repository_cls.return_value = repository
    get_team_stats_use_case_cls.return_value = use_case

    # When
    use_cases = get_team_stats_use_cases(db=db, cache_adapter=cache_adapter)

    # Then
    assert use_cases == {"get_team_stats": use_case}
    team_stats_repository_cls.assert_called_once_with(db)
    get_team_stats_use_case_cls.assert_called_once_with(repository, cache_adapter)


@pytest.mark.asyncio
@patch("interface.rest.team_stats_retrieval_routes._validate_season_range")
@patch("interface.rest.team_stats_retrieval_routes._parse_season_year")
async def test_get_team_stats_rejects_invalid_team_id(parse_season_mock, validate_range_mock):
    # Given
    parse_season_mock.return_value = 2024

    # When / Then
    with pytest.raises(DomainExceptions.InvalidDataError, match="Team ID must be a positive integer"):
        await get_team_stats(team_id=0, season="2024", category="all", use_cases={"get_team_stats": AsyncMock()})

    validate_range_mock.assert_not_called()


@pytest.mark.asyncio
@patch("interface.rest.team_stats_retrieval_routes.to_team_stats_dto")
@patch("interface.rest.team_stats_retrieval_routes._validate_season_range")
@patch("interface.rest.team_stats_retrieval_routes._parse_season_year")
async def test_get_team_stats_returns_success_response(parse_season_mock, validate_range_mock, to_dto_mock):
    # Given
    parse_season_mock.return_value = 2024
    use_case = AsyncMock()
    use_case.execute.return_value = {"stats": "raw"}
    to_dto_mock.return_value = {"stats": "dto"}

    # When
    response = await get_team_stats(
        team_id=7,
        season="2024",
        category="hitting",
        use_cases={"get_team_stats": use_case},
    )

    # Then
    payload = _decode(response)
    assert payload["status"] == "success"
    assert payload["data"] == {"stats": "dto"}
    use_case.execute.assert_awaited_once_with(
        team_id=7,
        season=2024,
        category=TeamStatsCategory.HITTING,
    )
    validate_range_mock.assert_called_once_with(2024)


@pytest.mark.asyncio
@patch("interface.rest.team_stats_retrieval_routes._validate_season_range")
@patch("interface.rest.team_stats_retrieval_routes._parse_season_year")
async def test_get_team_stats_raises_team_not_found_when_use_case_returns_none(parse_season_mock, validate_range_mock):
    # Given
    parse_season_mock.return_value = 2024
    use_case = AsyncMock()
    use_case.execute.return_value = None

    # When / Then
    with pytest.raises(DomainExceptions.TeamNotFoundError):
        await get_team_stats(team_id=7, season="2024", category="all", use_cases={"get_team_stats": use_case})


@pytest.mark.asyncio
@patch("interface.rest.team_stats_retrieval_routes._validate_season_range")
@patch("interface.rest.team_stats_retrieval_routes._parse_season_year")
async def test_get_team_stats_wraps_unexpected_errors_as_external_service_error(parse_season_mock, validate_range_mock):
    # Given
    parse_season_mock.return_value = 2024
    use_case = AsyncMock()
    use_case.execute.side_effect = RuntimeError("db down")

    # When / Then
    with pytest.raises(DomainExceptions.ExternalServiceError, match="db down"):
        await get_team_stats(team_id=7, season="2024", category="all", use_cases={"get_team_stats": use_case})

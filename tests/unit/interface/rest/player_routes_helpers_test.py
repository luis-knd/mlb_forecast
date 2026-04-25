from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from interface.rest import player_routes
from interface.rest.exception_handlers import DomainExceptions


@patch("interface.rest.player_routes.datetime")
def test_validate_ingest_players_request_normalizes_source(datetime_mock):
    # Given
    datetime_mock.now.return_value = datetime(2026, 4, 25, 12, 0, 0)

    # When
    normalized = player_routes._validate_ingest_players_request(
        source=" Team_Roster ",
        season=2026,
        team_id=10,
        sport_id=1,
    )

    # Then
    assert normalized == "team_roster"


@patch("interface.rest.player_routes.datetime")
@pytest.mark.parametrize(
    ("season", "team_id", "sport_id", "expected_message"),
    [
        (1875, 1, 1, "season must be between"),
        (2028, 1, 1, "season must be between"),
        (2026, 0, 1, "teamId must be a positive integer"),
        (2026, 1, 0, "sportId must be a positive integer"),
    ],
)
def test_validate_ingest_players_request_rejects_invalid_inputs(
    datetime_mock,
    season,
    team_id,
    sport_id,
    expected_message,
):
    # Given
    datetime_mock.now.return_value = datetime(2026, 4, 25, 12, 0, 0)

    # When / Then
    with pytest.raises(DomainExceptions.InvalidDataError, match=expected_message):
        player_routes._validate_ingest_players_request(
            source="sport_players",
            season=season,
            team_id=team_id,
            sport_id=sport_id,
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("source", ["search", "all", "team_roster"])
async def test_resolve_team_mlb_id_for_ingestion_returns_none_when_not_applicable(source):
    # Given
    use_cases = {"get_team": AsyncMock()}
    team_id = None if source == "team_roster" else 15

    # When
    resolved = await player_routes._resolve_team_mlb_id_for_ingestion(source, team_id, use_cases)

    # Then
    assert resolved is None
    use_cases["get_team"].execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_resolve_team_mlb_id_for_ingestion_returns_team_mlb_id_when_source_uses_team():
    # Given
    team = type("TeamStub", (), {"mlb_id": 119})()
    use_cases = {"get_team": AsyncMock()}
    use_cases["get_team"].execute.return_value = team

    # When
    resolved = await player_routes._resolve_team_mlb_id_for_ingestion("sport_players", 12, use_cases)

    # Then
    assert resolved == 119
    use_cases["get_team"].execute.assert_awaited_once_with(team_id=12)


@pytest.mark.asyncio
async def test_ingest_players_from_source_maps_value_error_to_domain_error():
    # Given
    ingest_use_case = AsyncMock()
    ingest_use_case.execute.side_effect = ValueError("source not supported")
    use_cases = {"ingest_players_by_source": ingest_use_case}

    # When / Then
    with pytest.raises(DomainExceptions.InvalidDataError, match="source not supported"):
        await player_routes._ingest_players_from_source(
            source="search",
            season=2026,
            team_mlb_id=None,
            roster_type="active",
            sport_id=1,
            query="ohtani",
            use_cases=use_cases,
        )


@pytest.mark.asyncio
async def test_ingest_players_from_source_delegates_arguments_to_use_case():
    # Given
    ingest_use_case = AsyncMock()
    ingest_use_case.execute.return_value = ["p1", "p2"]
    use_cases = {"ingest_players_by_source": ingest_use_case}

    # When
    result = await player_routes._ingest_players_from_source(
        source="search",
        season=2026,
        team_mlb_id=None,
        roster_type="active",
        sport_id=1,
        query="judge",
        use_cases=use_cases,
    )

    # Then
    assert result == ["p1", "p2"]
    ingest_use_case.execute.assert_awaited_once_with(
        source="search",
        season=2026,
        team_mlb_id=None,
        roster_type="active",
        sport_id=1,
        query="judge",
    )


@patch("interface.rest.player_routes.datetime")
def test_build_ingestion_result_calculates_summary(datetime_mock):
    # Given
    start = datetime(2026, 4, 25, 12, 0, 0)
    end = datetime(2026, 4, 25, 12, 0, 3)
    datetime_mock.now.return_value = end

    # When
    result = player_routes._build_ingestion_result(players=[1, 2, 3], start_time=start)

    # Then
    assert result.operation == "player_ingestion"
    assert result.records_processed == 3
    assert result.records_created == 3
    assert result.records_updated == 0
    assert result.duration_seconds == 3.0
    assert result.timestamp == end

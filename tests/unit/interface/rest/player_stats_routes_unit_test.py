import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from domain.entities.player import Player
from domain.entities.player_stats_records import PlayerStatsGroupRecord, PlayerStatsHistoryRecord
from interface.rest import player_stats_routes
from interface.rest.exception_handlers import DomainExceptions


def _decode_response(response) -> dict:
    return json.loads(response.body.decode())


@pytest.fixture
def sample_player() -> Player:
    player = Player.create(
        mlb_id=660271,
        first_name="Shohei",
        last_name="Ohtani",
        position="DH",
        bats="L",
        throws="R",
        active=True,
        current_team_id=1,
    )
    player.id = 7
    return player


@patch("interface.rest.player_stats_routes.MLBApiAdapter")
@patch("interface.rest.player_stats_routes.PlayerStatsRepository")
@patch("interface.rest.player_stats_routes.TeamRepository")
@patch("interface.rest.player_stats_routes.PlayerRepository")
@patch("interface.rest.player_stats_routes.GetPlayerUseCase")
@patch("interface.rest.player_stats_routes.GetPersistedPlayerSeasonStatsUseCase")
@patch("interface.rest.player_stats_routes.GetPersistedPlayerCareerStatsUseCase")
@patch("interface.rest.player_stats_routes.GetPersistedPlayerYearByYearStatsUseCase")
@patch("interface.rest.player_stats_routes.GetPersistedPlayerGameLogsUseCase")
@patch("interface.rest.player_stats_routes.GetPersistedPlayerStatSplitsUseCase")
@patch("interface.rest.player_stats_routes.IngestPlayerSeasonStatsUseCase")
@patch("interface.rest.player_stats_routes.IngestPlayerStatsHistoryUseCase")
def test_get_persisted_player_stats_use_cases_wires_dependencies(
    mock_ingest_history_cls,
    mock_ingest_season_cls,
    mock_get_splits_cls,
    mock_get_logs_cls,
    mock_get_year_by_year_cls,
    mock_get_career_cls,
    mock_get_season_cls,
    mock_get_player_cls,
    mock_player_repository_cls,
    mock_team_repository_cls,
    mock_player_stats_repository_cls,
    mock_mlb_api_adapter_cls,
):
    # Given
    mock_db = MagicMock()
    mock_cache = AsyncMock()

    # When
    use_cases = player_stats_routes.get_persisted_player_stats_use_cases(db=mock_db, cache=mock_cache)

    # Then
    assert set(use_cases) == {
        "get_player",
        "get_season_stats",
        "get_career_stats",
        "get_year_by_year_stats",
        "get_game_logs",
        "get_stat_splits",
        "ingest_season_stats",
        "ingest_history_stats",
    }
    mock_player_repository_cls.assert_called_once_with(mock_db)
    mock_team_repository_cls.assert_called_once_with(mock_db)
    mock_player_stats_repository_cls.assert_called_once_with(mock_db)
    mock_mlb_api_adapter_cls.assert_called_once_with()
    mock_get_player_cls.assert_called_once()
    mock_get_season_cls.assert_called_once()
    mock_get_career_cls.assert_called_once()
    mock_get_year_by_year_cls.assert_called_once()
    mock_get_logs_cls.assert_called_once()
    mock_get_splits_cls.assert_called_once()
    mock_ingest_season_cls.assert_called_once()
    mock_ingest_history_cls.assert_called_once()


@pytest.mark.asyncio
async def test_get_persisted_player_season_stats_returns_success_response(sample_player):
    # Given
    use_cases = {
        "get_player": AsyncMock(),
        "get_season_stats": AsyncMock(),
    }
    use_cases["get_player"].execute.return_value = sample_player
    use_cases["get_season_stats"].execute.return_value = [
        PlayerStatsGroupRecord.create(7, 1, 2025, "R", "hitting", {"hits": 5})
    ]

    # When
    response = await player_stats_routes.get_persisted_player_season_stats(
        player_id=7,
        season=2025,
        group="hitting",
        game_type="R",
        use_cases=use_cases,
    )

    # Then
    body = _decode_response(response)
    assert body["status"] == "success"
    assert body["data"]["stats"] == "season"
    assert body["data"]["records"][0]["metrics"]["hits"] == 5


@pytest.mark.asyncio
async def test_get_persisted_player_career_stats_returns_not_found_response_for_empty_records(sample_player):
    # Given
    use_cases = {
        "get_player": AsyncMock(),
        "get_career_stats": AsyncMock(),
    }
    use_cases["get_player"].execute.return_value = sample_player
    use_cases["get_career_stats"].execute.return_value = []

    # When
    response = await player_stats_routes.get_persisted_player_career_stats(
        player_id=7,
        group="all",
        game_type="R",
        use_cases=use_cases,
    )

    # Then
    body = _decode_response(response)
    assert body["status"] == "error"
    assert body["code"] == 404


@pytest.mark.asyncio
async def test_get_persisted_player_career_stats_returns_success_response(sample_player):
    # Given
    use_cases = {
        "get_player": AsyncMock(),
        "get_career_stats": AsyncMock(),
    }
    use_cases["get_player"].execute.return_value = sample_player
    use_cases["get_career_stats"].execute.return_value = [
        PlayerStatsGroupRecord.create(7, 1, 0, "R", "hitting", {"hits": 100})
    ]

    # When
    response = await player_stats_routes.get_persisted_player_career_stats(
        player_id=7,
        group="hitting",
        game_type="R",
        use_cases=use_cases,
    )

    # Then
    body = _decode_response(response)
    assert body["status"] == "success"
    assert body["data"]["stats"] == "career"


@pytest.mark.asyncio
async def test_get_persisted_player_career_stats_translates_value_error(sample_player):
    # Given
    use_cases = {
        "get_player": AsyncMock(),
        "get_career_stats": AsyncMock(),
    }
    use_cases["get_player"].execute.return_value = sample_player
    use_cases["get_career_stats"].execute.side_effect = ValueError("bad group")

    # When / Then
    with pytest.raises(DomainExceptions.InvalidDataError, match="bad group"):
        await player_stats_routes.get_persisted_player_career_stats(
            player_id=7,
            group="bad",
            game_type="R",
            use_cases=use_cases,
        )


@pytest.mark.asyncio
async def test_get_persisted_player_game_logs_rejects_non_positive_player_id():
    # Given / When / Then
    with pytest.raises(DomainExceptions.InvalidDataError, match="player_id must be a positive integer"):
        await player_stats_routes.get_persisted_player_game_logs(
            player_id=0,
            season=2025,
            group="all",
            game_type="R",
            days_back=None,
            limit=None,
            use_cases={"get_player": AsyncMock(), "get_game_logs": AsyncMock()},
        )


@pytest.mark.asyncio
async def test_get_persisted_player_season_stats_translates_value_error(sample_player):
    # Given
    use_cases = {
        "get_player": AsyncMock(),
        "get_season_stats": AsyncMock(),
    }
    use_cases["get_player"].execute.return_value = sample_player
    use_cases["get_season_stats"].execute.side_effect = ValueError("bad season")

    # When / Then
    with pytest.raises(DomainExceptions.InvalidDataError, match="bad season"):
        await player_stats_routes.get_persisted_player_season_stats(
            player_id=7,
            season=2025,
            group="hitting",
            game_type="R",
            use_cases=use_cases,
        )


@pytest.mark.asyncio
async def test_get_persisted_player_season_stats_returns_not_found_response_when_records_are_missing(sample_player):
    # Given
    use_cases = {
        "get_player": AsyncMock(),
        "get_season_stats": AsyncMock(),
    }
    use_cases["get_player"].execute.return_value = sample_player
    use_cases["get_season_stats"].execute.return_value = []

    # When
    response = await player_stats_routes.get_persisted_player_season_stats(
        player_id=7,
        season=2025,
        group="hitting",
        game_type="R",
        use_cases=use_cases,
    )

    # Then
    body = _decode_response(response)
    assert body["code"] == 404


@pytest.mark.asyncio
async def test_get_persisted_player_year_by_year_stats_covers_success_not_found_and_value_error(sample_player):
    # Given
    success_use_cases = {
        "get_player": AsyncMock(),
        "get_year_by_year_stats": AsyncMock(),
    }
    success_use_cases["get_player"].execute.return_value = sample_player
    success_use_cases["get_year_by_year_stats"].execute.return_value = [
        PlayerStatsGroupRecord.create(7, 1, 2025, "R", "hitting", {"hits": 20})
    ]

    # When
    success_response = await player_stats_routes.get_persisted_player_year_by_year_stats(
        player_id=7,
        group="hitting",
        game_type="R",
        use_cases=success_use_cases,
    )

    # Then
    success_body = _decode_response(success_response)
    assert success_body["status"] == "success"
    assert success_body["data"]["stats"] == "yearByYear"

    not_found_use_cases = {
        "get_player": AsyncMock(),
        "get_year_by_year_stats": AsyncMock(),
    }
    not_found_use_cases["get_player"].execute.return_value = sample_player
    not_found_use_cases["get_year_by_year_stats"].execute.return_value = []
    not_found_response = await player_stats_routes.get_persisted_player_year_by_year_stats(
        player_id=7,
        group="hitting",
        game_type="R",
        use_cases=not_found_use_cases,
    )
    assert _decode_response(not_found_response)["code"] == 404

    error_use_cases = {
        "get_player": AsyncMock(),
        "get_year_by_year_stats": AsyncMock(),
    }
    error_use_cases["get_player"].execute.return_value = sample_player
    error_use_cases["get_year_by_year_stats"].execute.side_effect = ValueError("bad year")
    with pytest.raises(DomainExceptions.InvalidDataError, match="bad year"):
        await player_stats_routes.get_persisted_player_year_by_year_stats(
            player_id=7,
            group="hitting",
            game_type="R",
            use_cases=error_use_cases,
        )


@pytest.mark.asyncio
async def test_get_persisted_player_game_logs_translates_value_error_and_returns_not_found(sample_player):
    # Given
    error_use_cases = {
        "get_player": AsyncMock(),
        "get_game_logs": AsyncMock(),
    }
    error_use_cases["get_player"].execute.return_value = sample_player
    error_use_cases["get_game_logs"].execute.side_effect = ValueError("bad window")

    # When / Then
    with pytest.raises(DomainExceptions.InvalidDataError, match="bad window"):
        await player_stats_routes.get_persisted_player_game_logs(
            player_id=7,
            season=2025,
            group="hitting",
            game_type="R",
            days_back=5,
            limit=10,
            use_cases=error_use_cases,
        )

    not_found_use_cases = {
        "get_player": AsyncMock(),
        "get_game_logs": AsyncMock(),
    }
    not_found_use_cases["get_player"].execute.return_value = sample_player
    not_found_use_cases["get_game_logs"].execute.return_value = []
    response = await player_stats_routes.get_persisted_player_game_logs(
        player_id=7,
        season=2025,
        group="hitting",
        game_type="R",
        days_back=5,
        limit=10,
        use_cases=not_found_use_cases,
    )
    assert _decode_response(response)["code"] == 404


@pytest.mark.asyncio
async def test_get_persisted_player_stat_splits_returns_success_response(sample_player):
    # Given
    use_cases = {
        "get_player": AsyncMock(),
        "get_stat_splits": AsyncMock(),
    }
    use_cases["get_player"].execute.return_value = sample_player
    use_cases["get_stat_splits"].execute.return_value = [
        PlayerStatsHistoryRecord.create(7, 1, 2025, "R", "hitting", "statSplits", "home", {"hits": 4})
    ]

    # When
    response = await player_stats_routes.get_persisted_player_stat_splits(
        player_id=7,
        season=2025,
        group="all",
        game_type="R",
        limit=10,
        use_cases=use_cases,
    )

    # Then
    body = _decode_response(response)
    assert body["status"] == "success"
    assert body["data"]["stats"] == "statSplits"
    assert body["data"]["records"][0]["external_reference"] == "home"


@pytest.mark.asyncio
async def test_get_persisted_player_stat_splits_translates_value_error_and_returns_not_found(sample_player):
    # Given
    error_use_cases = {
        "get_player": AsyncMock(),
        "get_stat_splits": AsyncMock(),
    }
    error_use_cases["get_player"].execute.return_value = sample_player
    error_use_cases["get_stat_splits"].execute.side_effect = ValueError("bad splits")

    # When / Then
    with pytest.raises(DomainExceptions.InvalidDataError, match="bad splits"):
        await player_stats_routes.get_persisted_player_stat_splits(
            player_id=7,
            season=2025,
            group="all",
            game_type="R",
            limit=10,
            use_cases=error_use_cases,
        )

    not_found_use_cases = {
        "get_player": AsyncMock(),
        "get_stat_splits": AsyncMock(),
    }
    not_found_use_cases["get_player"].execute.return_value = sample_player
    not_found_use_cases["get_stat_splits"].execute.return_value = []
    response = await player_stats_routes.get_persisted_player_stat_splits(
        player_id=7,
        season=2025,
        group="all",
        game_type="R",
        limit=10,
        use_cases=not_found_use_cases,
    )
    assert _decode_response(response)["code"] == 404


@pytest.mark.asyncio
async def test_ingest_persisted_player_season_stats_forwards_params():
    # Given
    use_cases = {"ingest_season_stats": AsyncMock()}
    use_cases["ingest_season_stats"].execute.return_value = {"operation": "player_stats_seasonal_ingestion"}

    # When
    response = await player_stats_routes.ingest_persisted_player_season_stats(
        season=2025,
        group="hitting",
        game_type="R",
        player_id=7,
        team_id=None,
        force_refresh=True,
        use_cases=use_cases,
    )

    # Then
    body = _decode_response(response)
    assert body["status"] == "success"
    assert body["code"] == 201
    use_cases["ingest_season_stats"].execute.assert_awaited_once_with(
        season=2025,
        group="hitting",
        game_type="R",
        player_id=7,
        team_id=None,
        force_refresh=True,
    )


@pytest.mark.asyncio
async def test_ingest_persisted_player_season_stats_translates_value_error():
    # Given
    use_cases = {"ingest_season_stats": AsyncMock()}
    use_cases["ingest_season_stats"].execute.side_effect = ValueError("bad ingest")

    # When / Then
    with pytest.raises(DomainExceptions.InvalidDataError, match="bad ingest"):
        await player_stats_routes.ingest_persisted_player_season_stats(
            season=2025,
            group="all",
            game_type="R",
            player_id=7,
            team_id=None,
            force_refresh=False,
            use_cases=use_cases,
        )


@pytest.mark.asyncio
async def test_ingest_persisted_player_history_stats_translates_value_error():
    # Given
    use_cases = {"ingest_history_stats": AsyncMock()}
    use_cases["ingest_history_stats"].execute.side_effect = ValueError("bad request")

    # When / Then
    with pytest.raises(DomainExceptions.InvalidDataError, match="bad request"):
        await player_stats_routes.ingest_persisted_player_stats_history(
            season=2025,
            group="hitting",
            game_type="R",
            player_id=7,
            team_id=None,
            days_back=7,
            force_refresh=False,
            use_cases=use_cases,
        )


@pytest.mark.asyncio
async def test_ingest_persisted_player_history_stats_returns_created_response():
    # Given
    use_cases = {"ingest_history_stats": AsyncMock()}
    use_cases["ingest_history_stats"].execute.return_value = {"operation": "player_stats_history_ingestion"}

    # When
    response = await player_stats_routes.ingest_persisted_player_stats_history(
        season=2025,
        group="hitting",
        game_type="R",
        player_id=7,
        team_id=None,
        days_back=7,
        force_refresh=False,
        use_cases=use_cases,
    )

    # Then
    body = _decode_response(response)
    assert body["code"] == 201
    assert body["data"]["operation"] == "player_stats_history_ingestion"

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from domain.entities.player import Player
from domain.entities.team import Team
from interface.rest import player_routes
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


@pytest.fixture
def sample_team() -> Team:
    team = Team.create(
        mlb_id=119,
        name="Los Angeles Dodgers",
        abbreviation="LAD",
        city="Los Angeles",
        division="National League West",
        league="National League",
        venue_name="Dodger Stadium",
    )
    team.id = 1
    return team


@patch("interface.rest.player_routes.GetPlayerStatsUseCase")
@patch("interface.rest.player_routes.IngestPlayersBySourceUseCase")
@patch("interface.rest.player_routes.GetPlayerByMlbIdUseCase")
@patch("interface.rest.player_routes.GetTeamUseCase")
@patch("interface.rest.player_routes.GetPlayerUseCase")
@patch("interface.rest.player_routes.ListPlayersUseCase")
@patch("interface.rest.player_routes.MLBApiAdapter")
@patch("interface.rest.player_routes.CachedTeamRepository")
@patch("interface.rest.player_routes.TeamRepository")
@patch("interface.rest.player_routes.PlayerRepository")
def test_get_player_use_cases_wires_dependencies(
    mock_player_repository_cls,
    mock_team_repository_cls,
    mock_cached_team_repository_cls,
    mock_mlb_api_adapter_cls,
    mock_list_players_use_case_cls,
    mock_get_player_use_case_cls,
    mock_get_team_use_case_cls,
    mock_get_player_by_mlb_id_use_case_cls,
    mock_ingest_players_by_source_use_case_cls,
    mock_get_player_stats_use_case_cls,
):
    # Given
    mock_db = MagicMock()
    mock_cache = AsyncMock()
    player_repository = MagicMock()
    team_repository = MagicMock()
    cached_team_repository = MagicMock()
    mlb_api_adapter = MagicMock()
    list_players_use_case = MagicMock()
    get_player_use_case = MagicMock()
    get_team_use_case = MagicMock()
    get_player_by_mlb_id_use_case = MagicMock()
    ingest_players_by_source_use_case = MagicMock()
    get_player_stats_use_case = MagicMock()

    mock_player_repository_cls.return_value = player_repository
    mock_team_repository_cls.return_value = team_repository
    mock_cached_team_repository_cls.return_value = cached_team_repository
    mock_mlb_api_adapter_cls.return_value = mlb_api_adapter
    mock_list_players_use_case_cls.return_value = list_players_use_case
    mock_get_player_use_case_cls.return_value = get_player_use_case
    mock_get_team_use_case_cls.return_value = get_team_use_case
    mock_get_player_by_mlb_id_use_case_cls.return_value = get_player_by_mlb_id_use_case
    mock_ingest_players_by_source_use_case_cls.return_value = ingest_players_by_source_use_case
    mock_get_player_stats_use_case_cls.return_value = get_player_stats_use_case

    # When
    use_cases = player_routes.get_player_use_cases(db=mock_db, cache=mock_cache)

    # Then
    assert use_cases == {
        "list_players": list_players_use_case,
        "get_player": get_player_use_case,
        "get_team": get_team_use_case,
        "get_player_by_mlb_id": get_player_by_mlb_id_use_case,
        "ingest_players_by_source": ingest_players_by_source_use_case,
        "get_player_stats": get_player_stats_use_case,
    }
    mock_player_repository_cls.assert_called_once_with(mock_db)
    mock_team_repository_cls.assert_called_once_with(mock_db)
    mock_cached_team_repository_cls.assert_called_once_with(team_repository, mock_cache)
    mock_mlb_api_adapter_cls.assert_called_once_with()
    mock_list_players_use_case_cls.assert_called_once_with(player_repository, mock_cache)
    mock_get_player_use_case_cls.assert_called_once_with(player_repository, mock_cache)
    mock_get_team_use_case_cls.assert_called_once_with(cached_team_repository)
    mock_get_player_by_mlb_id_use_case_cls.assert_called_once_with(player_repository, mock_cache)
    mock_ingest_players_by_source_use_case_cls.assert_called_once_with(
        player_repository,
        cached_team_repository,
        mlb_api_adapter,
        mock_cache,
    )
    mock_get_player_stats_use_case_cls.assert_called_once_with(
        mlb_api_adapter,
        mock_cache,
        all_groups_concurrency=player_routes.settings.MLB_PLAYER_STATS_ALL_GROUPS_CONCURRENCY,
    )


@pytest.mark.asyncio
async def test_list_players_returns_success_response(sample_player):
    # Given
    use_cases = {"list_players": AsyncMock()}
    use_cases["list_players"].execute.return_value = [sample_player]

    # When
    response = await player_routes.list_players(
        team_id=1,
        position="DH",
        name="ohtani",
        active=True,
        limit=10,
        offset=5,
        use_cases=use_cases,
    )

    # Then
    body = _decode_response(response)
    assert body["status"] == "success"
    assert body["data"][0]["id"] == 7
    assert body["data"][0]["mlb_id"] == 660271
    use_cases["list_players"].execute.assert_awaited_once_with(
        team_id=1,
        position="DH",
        name="ohtani",
        active=True,
        limit=10,
        offset=5,
    )


@pytest.mark.asyncio
async def test_list_players_rejects_non_positive_team_id():
    # Given, When, Then
    with pytest.raises(DomainExceptions.InvalidDataError, match="team_id must be a positive integer"):
        await player_routes.list_players(team_id=0, use_cases={"list_players": AsyncMock()})


@pytest.mark.asyncio
async def test_get_player_returns_success_response(sample_player):
    # Given
    use_cases = {"get_player_by_mlb_id": AsyncMock()}
    use_cases["get_player_by_mlb_id"].execute.return_value = sample_player

    # When
    response = await player_routes.get_player(player_id=660271, use_cases=use_cases)

    # Then
    body = _decode_response(response)
    assert body["status"] == "success"
    assert body["data"]["full_name"] == "Shohei Ohtani"
    use_cases["get_player_by_mlb_id"].execute.assert_awaited_once_with(mlb_player_id=660271)


@pytest.mark.asyncio
async def test_get_player_rejects_non_positive_player_id():
    # Given / When / Then
    with pytest.raises(DomainExceptions.InvalidDataError, match="player_id must be a positive integer"):
        await player_routes.get_player(player_id=0, use_cases={"get_player_by_mlb_id": AsyncMock()})


@pytest.mark.asyncio
async def test_get_player_raises_not_found_for_unknown_player():
    # Given
    use_cases = {"get_player_by_mlb_id": AsyncMock()}
    use_cases["get_player_by_mlb_id"].execute.return_value = None

    # When / Then
    with pytest.raises(DomainExceptions.PlayerNotFoundError):
        await player_routes.get_player(player_id=660271, use_cases=use_cases)


@pytest.mark.asyncio
async def test_get_player_stats_returns_success_response(sample_player):
    # Given
    use_cases = {
        "get_player": AsyncMock(),
        "get_player_stats": AsyncMock(),
    }
    use_cases["get_player"].execute.return_value = sample_player
    use_cases["get_player_stats"].execute.return_value = {
        "player_id": sample_player.mlb_id,
        "stats": "season",
        "group": "hitting",
        "season": 2025,
        "stats_data": [{"group": {"displayName": "hitting"}}],
    }

    # When
    response = await player_routes.get_player_stats(
        player_id=sample_player.id,
        stats="season",
        group="hitting",
        season=2025,
        game_type=None,
        days_back=None,
        use_cases=use_cases,
    )

    # Then
    body = _decode_response(response)
    assert body["status"] == "success"
    assert body["data"]["player_id"] == sample_player.id
    assert body["data"]["stats"] == "season"
    use_cases["get_player"].execute.assert_awaited_once_with(player_id=sample_player.id)
    use_cases["get_player_stats"].execute.assert_awaited_once_with(
        mlb_player_id=sample_player.mlb_id,
        stats="season",
        group="hitting",
        season=2025,
        game_type=None,
        days_back=None,
    )


@pytest.mark.asyncio
async def test_get_player_stats_rejects_non_positive_player_id():
    # Given / When / Then
    with pytest.raises(DomainExceptions.InvalidDataError, match="player_id must be a positive integer"):
        await player_routes.get_player_stats(
            player_id=0,
            stats="season",
            group="hitting",
            use_cases={"get_player": AsyncMock(), "get_player_stats": AsyncMock()},
        )


@pytest.mark.asyncio
async def test_get_player_stats_raises_not_found_for_unknown_internal_player():
    # Given
    use_cases = {
        "get_player": AsyncMock(),
        "get_player_stats": AsyncMock(),
    }
    use_cases["get_player"].execute.return_value = None

    # When / Then
    with pytest.raises(DomainExceptions.PlayerNotFoundError):
        await player_routes.get_player_stats(
            player_id=7,
            stats="season",
            group="hitting",
            use_cases=use_cases,
        )


@pytest.mark.asyncio
async def test_get_player_stats_translates_value_error_to_invalid_data_error(sample_player):
    # Given
    use_cases = {
        "get_player": AsyncMock(),
        "get_player_stats": AsyncMock(),
    }
    use_cases["get_player"].execute.return_value = sample_player
    use_cases["get_player_stats"].execute.side_effect = ValueError("group must be valid")

    # When / Then
    with pytest.raises(DomainExceptions.InvalidDataError, match="group must be valid"):
        await player_routes.get_player_stats(
            player_id=sample_player.id,
            stats="season",
            group="invalid",
            use_cases=use_cases,
        )


@pytest.mark.asyncio
async def test_get_player_stats_returns_not_found_response_when_stats_are_missing(sample_player):
    # Given
    use_cases = {
        "get_player": AsyncMock(),
        "get_player_stats": AsyncMock(),
    }
    use_cases["get_player"].execute.return_value = sample_player
    use_cases["get_player_stats"].execute.return_value = None

    # When
    response = await player_routes.get_player_stats(
        player_id=sample_player.id,
        stats="season",
        group="hitting",
        use_cases=use_cases,
    )

    # Then
    body = _decode_response(response)
    assert body["status"] == "error"
    assert body["message"] == "Resource not found"
    assert body["errors"] == [f"Player stats with ID {sample_player.id} not found"]


@pytest.mark.asyncio
async def test_ingest_players_resolves_internal_team_id_before_ingesting(sample_player, sample_team):
    # Given
    use_cases = {
        "get_team": AsyncMock(),
        "ingest_players_by_source": AsyncMock(),
    }
    use_cases["get_team"].execute.return_value = sample_team
    use_cases["ingest_players_by_source"].execute.return_value = [sample_player]

    # When
    response = await player_routes.ingest_players(
        source=" TEAM_ROSTER ",
        season=2025,
        team_id=sample_team.id,
        roster_type="active",
        sport_id=1,
        query=None,
        use_cases=use_cases,
    )

    # Then
    body = _decode_response(response)
    assert body["status"] == "success"
    assert body["data"]["ingestion_summary"]["records_processed"] == 1
    assert body["data"]["sample_players"][0]["mlb_id"] == sample_player.mlb_id
    use_cases["get_team"].execute.assert_awaited_once_with(team_id=sample_team.id)
    use_cases["ingest_players_by_source"].execute.assert_awaited_once_with(
        source=" TEAM_ROSTER ",
        season=2025,
        team_mlb_id=sample_team.mlb_id,
        roster_type="active",
        sport_id=1,
        query=None,
    )


@pytest.mark.asyncio
async def test_ingest_players_ignores_team_id_for_search_source(sample_player):
    # Given
    use_cases = {
        "get_team": AsyncMock(),
        "ingest_players_by_source": AsyncMock(),
    }
    use_cases["ingest_players_by_source"].execute.return_value = [sample_player]

    # When
    response = await player_routes.ingest_players(
        source="search",
        season=2025,
        team_id=1,
        roster_type="active",
        sport_id=1,
        query="ohtani",
        use_cases=use_cases,
    )

    # Then
    body = _decode_response(response)
    assert body["status"] == "success"
    use_cases["get_team"].execute.assert_not_called()
    use_cases["ingest_players_by_source"].execute.assert_awaited_once_with(
        source="search",
        season=2025,
        team_mlb_id=None,
        roster_type="active",
        sport_id=1,
        query="ohtani",
    )


@pytest.mark.asyncio
async def test_ingest_players_rejects_out_of_range_season():
    # Given / When / Then
    with pytest.raises(DomainExceptions.InvalidDataError, match="season must be between 1876 and"):
        await player_routes.ingest_players(
            source="sport_players",
            season=1800,
            use_cases={"get_team": AsyncMock(), "ingest_players_by_source": AsyncMock()},
        )


@pytest.mark.asyncio
async def test_ingest_players_rejects_non_positive_team_id():
    # Given / When / Then
    with pytest.raises(DomainExceptions.InvalidDataError, match="teamId must be a positive integer"):
        await player_routes.ingest_players(
            source="sport_players",
            season=None,
            team_id=0,
            roster_type="active",
            sport_id=1,
            query=None,
            use_cases={"get_team": AsyncMock(), "ingest_players_by_source": AsyncMock()},
        )


@pytest.mark.asyncio
async def test_ingest_players_rejects_non_positive_sport_id():
    # Given / When / Then
    with pytest.raises(DomainExceptions.InvalidDataError, match="sportId must be a positive integer"):
        await player_routes.ingest_players(
            source="sport_players",
            season=None,
            team_id=None,
            roster_type="active",
            sport_id=0,
            query=None,
            use_cases={"get_team": AsyncMock(), "ingest_players_by_source": AsyncMock()},
        )


@pytest.mark.asyncio
async def test_ingest_players_raises_not_found_for_unknown_internal_team():
    # Given
    use_cases = {
        "get_team": AsyncMock(),
        "ingest_players_by_source": AsyncMock(),
    }
    use_cases["get_team"].execute.side_effect = DomainExceptions.TeamNotFoundError(99)

    # When / Then
    with pytest.raises(DomainExceptions.TeamNotFoundError):
        await player_routes.ingest_players(
            source="team_roster",
            season=2025,
            team_id=99,
            roster_type="active",
            sport_id=1,
            query=None,
            use_cases=use_cases,
        )


@pytest.mark.asyncio
async def test_ingest_players_translates_value_error_to_invalid_data_error():
    # Given
    use_cases = {
        "get_team": AsyncMock(),
        "ingest_players_by_source": AsyncMock(),
    }
    use_cases["ingest_players_by_source"].execute.side_effect = ValueError("source must be valid")

    # When / Then
    with pytest.raises(DomainExceptions.InvalidDataError, match="source must be valid"):
        await player_routes.ingest_players(
            source="invalid",
            season=2025,
            team_id=None,
            roster_type="active",
            sport_id=1,
            query=None,
            use_cases=use_cases,
        )

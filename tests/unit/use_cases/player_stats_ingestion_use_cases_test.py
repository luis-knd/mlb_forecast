from unittest.mock import AsyncMock

import pytest

from application.use_cases.player_stats_ingestion_use_cases import (
    IngestPlayerSeasonStatsUseCase,
    IngestPlayerStatsHistoryUseCase,
)
from domain.entities.player import Player
from domain.entities.team import Team


def _build_player() -> Player:
    player = Player.create(
        mlb_id=660271,
        first_name="Shohei",
        last_name="Ohtani",
        position="DH",
        bats="L",
        throws="R",
        active=True,
        current_team_id=5,
    )
    player.id = 7
    return player


def _build_team() -> Team:
    team = Team.create(
        mlb_id=119,
        name="Los Angeles Dodgers",
        abbreviation="LAD",
        city="Los Angeles",
        division="National League West",
        league="National League",
    )
    team.id = 5
    return team


@pytest.fixture
def mock_cache() -> AsyncMock:
    cache = AsyncMock()
    cache.clear.return_value = 0
    return cache


@pytest.fixture
def mock_player_repository() -> AsyncMock:
    repository = AsyncMock()
    repository.get_by_id.return_value = _build_player()
    repository.list_by_team.return_value = [_build_player()]
    return repository


@pytest.fixture
def mock_team_repository() -> AsyncMock:
    repository = AsyncMock()
    repository.get_by_mlb_id.return_value = _build_team()
    return repository


@pytest.fixture
def mock_player_stats_repository() -> AsyncMock:
    repository = AsyncMock()
    repository.list_group_records.return_value = []
    repository.replace_group_records.side_effect = lambda **kwargs: kwargs["records"]
    repository.list_history_records.return_value = []
    repository.replace_history_records.side_effect = lambda **kwargs: kwargs["records"]
    return repository


@pytest.fixture
def mock_mlb_api() -> AsyncMock:
    api = AsyncMock()
    api.get_player_stats.side_effect = [
        {
            "stats_data": [
                {
                    "splits": [
                        {"team": {"id": 119}, "stat": {"hits": 3, "plateAppearances": 10, "avg": 0.3}},
                        {"team": {"id": 147}, "stat": {"hits": 2, "plateAppearances": 8, "avg": 0.25}},
                    ]
                }
            ]
        },
        {
            "stats_data": [
                {
                    "splits": [
                        {"team": {"id": 119}, "stat": {"ops": 0.95}},
                        {"team": {"id": 147}, "stat": {"ops": 0.7}},
                    ]
                }
            ]
        },
    ]
    return api


@pytest.mark.asyncio
async def test_ingest_player_season_stats_replaces_all_team_splits(
    mock_player_repository,
    mock_team_repository,
    mock_player_stats_repository,
    mock_mlb_api,
    mock_cache,
):
    # Given
    use_case = IngestPlayerSeasonStatsUseCase(
        mock_player_repository,
        mock_team_repository,
        mock_player_stats_repository,
        mock_mlb_api,
        mock_cache,
    )

    # When
    result = await use_case.execute(season=2025, group="hitting", player_id=7)

    # Then
    assert result["group_records_upserted"] == 2
    mock_player_stats_repository.replace_group_records.assert_awaited_once()
    replaced_records = mock_player_stats_repository.replace_group_records.await_args.kwargs["records"]
    assert [record.team_id for record in replaced_records] == [5, 5]
    assert replaced_records[0].metrics["ops"] == 0.95
    mock_cache.clear.assert_awaited_once_with(pattern="player_stats:persisted:player=7:*")


@pytest.mark.asyncio
async def test_ingest_player_season_stats_skips_historical_records_when_data_exists(
    mock_player_repository,
    mock_team_repository,
    mock_player_stats_repository,
    mock_cache,
):
    # Given
    mock_player_stats_repository.list_group_records.return_value = [AsyncMock()]
    mock_mlb_api = AsyncMock()
    use_case = IngestPlayerSeasonStatsUseCase(
        mock_player_repository,
        mock_team_repository,
        mock_player_stats_repository,
        mock_mlb_api,
        mock_cache,
    )

    # When
    result = await use_case.execute(season=2024, group="hitting", player_id=7)

    # Then
    assert result["group_records_upserted"] == 0
    assert result["group_records_skipped"] == 1
    mock_mlb_api.get_player_stats.assert_not_called()


@pytest.mark.asyncio
async def test_ingest_player_history_stats_replaces_game_logs_and_stat_splits(
    mock_player_repository,
    mock_team_repository,
    mock_player_stats_repository,
    mock_cache,
):
    # Given
    mock_mlb_api = AsyncMock()
    mock_mlb_api.get_player_stats.side_effect = [
        {
            "stats_data": [
                {"splits": [{"team": {"id": 119}, "date": "2025-03-20", "game": {"gamePk": 1}, "stat": {"hits": 2}}]}
            ]
        },
        {"stats_data": [{"splits": [{"team": {"id": 119}, "split": {"code": "home"}, "stat": {"hits": 4}}]}]},
    ]
    use_case = IngestPlayerStatsHistoryUseCase(
        mock_player_repository,
        mock_team_repository,
        mock_player_stats_repository,
        mock_mlb_api,
        mock_cache,
    )

    # When
    result = await use_case.execute(season=2025, group="hitting", player_id=7, days_back=7)

    # Then
    assert result["history_records_replaced"] == 2
    assert mock_player_stats_repository.replace_history_records.await_count == 2
    first_call = mock_player_stats_repository.replace_history_records.await_args_list[0]
    second_call = mock_player_stats_repository.replace_history_records.await_args_list[1]
    assert first_call.kwargs["stat_type"] == "gameLog"
    assert second_call.kwargs["stat_type"] == "statSplits"


@pytest.mark.asyncio
async def test_ingest_player_stats_use_cases_validate_target_selector(
    mock_player_repository,
    mock_team_repository,
    mock_player_stats_repository,
    mock_cache,
):
    # Given
    mock_mlb_api = AsyncMock()
    season_use_case = IngestPlayerSeasonStatsUseCase(
        mock_player_repository,
        mock_team_repository,
        mock_player_stats_repository,
        mock_mlb_api,
        mock_cache,
    )
    history_use_case = IngestPlayerStatsHistoryUseCase(
        mock_player_repository,
        mock_team_repository,
        mock_player_stats_repository,
        mock_mlb_api,
        mock_cache,
    )

    # When / Then
    with pytest.raises(ValueError, match="Exactly one of playerId or teamId must be provided"):
        await season_use_case.execute(season=2025, player_id=7, team_id=5)

    with pytest.raises(ValueError, match="Exactly one of playerId or teamId must be provided"):
        await history_use_case.execute(season=2025)

    with pytest.raises(ValueError, match="season must be greater than or equal"):
        await season_use_case.execute(season=1800, player_id=7)

    with pytest.raises(ValueError, match="season must be greater than or equal"):
        await history_use_case.execute(season=1800, player_id=7)


@pytest.mark.asyncio
async def test_ingestion_base_resolves_team_targets_and_fallback_team_ids(
    mock_player_repository,
    mock_team_repository,
    mock_player_stats_repository,
    mock_cache,
):
    # Given
    mock_mlb_api = AsyncMock()
    use_case = IngestPlayerSeasonStatsUseCase(
        mock_player_repository,
        mock_team_repository,
        mock_player_stats_repository,
        mock_mlb_api,
        mock_cache,
    )
    player = _build_player()
    mock_team_repository.get_by_mlb_id.return_value = None

    # When
    players = await use_case._resolve_target_players(player_id=None, team_id=5)
    fallback_with_missing_team = await use_case._resolve_internal_team_id(player, {"team": {"id": 119}})
    fallback_without_team = await use_case._resolve_internal_team_id(player, {})

    # Then
    assert len(players) == 1
    assert players[0].id == 7
    assert fallback_with_missing_team == player.current_team_id
    assert fallback_without_team == player.current_team_id


@pytest.mark.asyncio
async def test_ingest_player_season_stats_handles_empty_player_or_missing_payloads(
    mock_player_repository,
    mock_team_repository,
    mock_player_stats_repository,
    mock_cache,
):
    # Given
    player_without_id = _build_player()
    player_without_id.id = None
    missing_team_player = _build_player()
    missing_team_player.current_team_id = None
    mock_mlb_api = AsyncMock()
    mock_mlb_api.get_player_stats.side_effect = [
        None,
        {"stats_data": [{"splits": [{"team": {"id": 119}, "stat": {"hits": 1}}]}]},
        {"stats_data": []},
    ]
    mock_team_repository.get_by_mlb_id.return_value = None
    use_case = IngestPlayerSeasonStatsUseCase(
        mock_player_repository,
        mock_team_repository,
        mock_player_stats_repository,
        mock_mlb_api,
        mock_cache,
    )

    # When
    no_id_result = await use_case._ingest_one_group(player_without_id, 2025, "R", "hitting", False)
    missing_payload_result = await use_case._ingest_one_group(_build_player(), 2025, "R", "hitting", True)
    no_group_records_result = await use_case._ingest_one_group(missing_team_player, 2025, "R", "hitting", True)
    records_without_player = await use_case._build_group_records(
        player_without_id,
        2025,
        "R",
        "hitting",
        {"stats_data": []},
        {},
    )

    # Then
    assert no_id_result == 0
    assert missing_payload_result == 0
    assert no_group_records_result == 0
    assert records_without_player == []


@pytest.mark.asyncio
async def test_ingest_player_history_stats_skips_historical_contexts_when_records_exist(
    mock_player_repository,
    mock_team_repository,
    mock_player_stats_repository,
    mock_cache,
):
    # Given
    mock_player_stats_repository.list_history_records.return_value = [AsyncMock()]
    mock_mlb_api = AsyncMock()
    use_case = IngestPlayerStatsHistoryUseCase(
        mock_player_repository,
        mock_team_repository,
        mock_player_stats_repository,
        mock_mlb_api,
        mock_cache,
    )

    # When
    result = await use_case.execute(season=2024, group="hitting", player_id=7)

    # Then
    assert result["history_contexts_skipped"] == 2
    mock_mlb_api.get_player_stats.assert_not_called()


@pytest.mark.asyncio
async def test_build_history_records_returns_empty_for_missing_player_id_or_payload(
    mock_player_repository,
    mock_team_repository,
    mock_player_stats_repository,
    mock_cache,
):
    # Given
    mock_mlb_api = AsyncMock()
    use_case = IngestPlayerStatsHistoryUseCase(
        mock_player_repository,
        mock_team_repository,
        mock_player_stats_repository,
        mock_mlb_api,
        mock_cache,
    )
    player_without_id = _build_player()
    player_without_id.id = None

    # When
    records_without_player = await use_case._build_history_records(
        player_without_id,
        2025,
        "R",
        "hitting",
        "gameLog",
        {},
    )
    records_without_payload = await use_case._build_history_records(
        _build_player(),
        2025,
        "R",
        "hitting",
        "gameLog",
        None,
    )
    group_history_without_player = await use_case._ingest_group_history(
        player_without_id,
        2025,
        "R",
        "hitting",
        None,
        True,
    )

    # Then
    assert records_without_player == []
    assert records_without_payload == []
    assert group_history_without_player == 0

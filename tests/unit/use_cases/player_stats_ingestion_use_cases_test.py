from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from application.use_cases.player_stats_ingestion_use_cases import (
    IngestPlayerSeasonStatsUseCase,
    IngestPlayerStatsHistoryUseCase,
    _index_splits_by_team,
    _should_refresh_existing_records,
)
from domain.entities.player import Player
from domain.entities.team import Team


def _build_player(*, current_team_id: int | None = 5, player_id: int | None = 7) -> Player:
    player = Player.create(
        mlb_id=660271,
        first_name="Shohei",
        last_name="Ohtani",
        position="DH",
        bats="L",
        throws="R",
        active=True,
        current_team_id=current_team_id,
    )
    player.id = player_id
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


def _stats_response(*splits: dict) -> dict:
    return {"stats_data": [{"splits": list(splits)}]}


def _build_season_use_case(
    mock_player_repository: AsyncMock,
    mock_team_repository: AsyncMock,
    mock_player_stats_repository: AsyncMock,
    mock_cache: AsyncMock,
    mlb_api: AsyncMock | None = None,
) -> IngestPlayerSeasonStatsUseCase:
    return IngestPlayerSeasonStatsUseCase(
        mock_player_repository,
        mock_team_repository,
        mock_player_stats_repository,
        mlb_api or AsyncMock(),
        mock_cache,
    )


def _build_history_use_case(
    mock_player_repository: AsyncMock,
    mock_team_repository: AsyncMock,
    mock_player_stats_repository: AsyncMock,
    mock_cache: AsyncMock,
    mlb_api: AsyncMock | None = None,
) -> IngestPlayerStatsHistoryUseCase:
    return IngestPlayerStatsHistoryUseCase(
        mock_player_repository,
        mock_team_repository,
        mock_player_stats_repository,
        mlb_api or AsyncMock(),
        mock_cache,
    )


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
        _stats_response(
            {"team": {"id": 119}, "stat": {"hits": 3, "plateAppearances": 10, "avg": 0.3}},
            {"team": {"id": 147}, "stat": {"hits": 2, "plateAppearances": 8, "avg": 0.25}},
        ),
        _stats_response(
            {"team": {"id": 119}, "stat": {"ops": 0.95}},
            {"team": {"id": 147}, "stat": {"ops": 0.7}},
        ),
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
    use_case = _build_season_use_case(
        mock_player_repository,
        mock_team_repository,
        mock_player_stats_repository,
        mock_cache,
        mock_mlb_api,
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
async def test_ingest_player_history_stats_replaces_game_logs_and_stat_splits(
    mock_player_repository,
    mock_team_repository,
    mock_player_stats_repository,
    mock_cache,
):
    # Given
    mock_mlb_api = AsyncMock()
    mock_mlb_api.get_player_stats.side_effect = [
        _stats_response({"team": {"id": 119}, "date": "2025-03-20", "game": {"gamePk": 1}, "stat": {"hits": 2}}),
        _stats_response({"team": {"id": 119}, "split": {"code": "home"}, "stat": {"hits": 4}}),
    ]
    use_case = _build_history_use_case(
        mock_player_repository,
        mock_team_repository,
        mock_player_stats_repository,
        mock_cache,
        mock_mlb_api,
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
async def test_ingest_player_season_stats_skips_existing_closed_season_records(
    mock_player_repository,
    mock_team_repository,
    mock_player_stats_repository,
    mock_cache,
):
    # Given
    closed_season = datetime.now().year - 1
    mock_player_stats_repository.list_group_records.return_value = [AsyncMock()]
    mock_mlb_api = AsyncMock()
    use_case = _build_season_use_case(
        mock_player_repository,
        mock_team_repository,
        mock_player_stats_repository,
        mock_cache,
        mock_mlb_api,
    )

    # When
    result = await use_case.execute(season=closed_season, group="hitting", player_id=7)

    # Then
    assert result["group_records_upserted"] == 0
    assert result["group_records_skipped"] == 1
    mock_mlb_api.get_player_stats.assert_not_called()
    mock_player_stats_repository.replace_group_records.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("use_case_kind", "execute_kwargs", "message"),
    [
        (
            "season",
            {"season": 2025, "player_id": 7, "team_id": 5},
            "Exactly one of playerId or teamId must be provided",
        ),
        (
            "history",
            {"season": 2025},
            "Exactly one of playerId or teamId must be provided",
        ),
        (
            "season",
            {"season": 1800, "player_id": 7},
            "season must be greater than or equal",
        ),
        (
            "history",
            {"season": 1800, "player_id": 7},
            "season must be greater than or equal",
        ),
    ],
    ids=[
        "season-requires-single-target",
        "history-requires-single-target",
        "season-rejects-old-year",
        "history-rejects-old-year",
    ],
)
async def test_ingestion_use_cases_validate_inputs(
    use_case_kind,
    execute_kwargs,
    message,
    mock_player_repository,
    mock_team_repository,
    mock_player_stats_repository,
    mock_cache,
):
    # Given
    use_case = (
        _build_season_use_case(
            mock_player_repository,
            mock_team_repository,
            mock_player_stats_repository,
            mock_cache,
        )
        if use_case_kind == "season"
        else _build_history_use_case(
            mock_player_repository,
            mock_team_repository,
            mock_player_stats_repository,
            mock_cache,
        )
    )

    # When / Then
    with pytest.raises(ValueError, match=message):
        await use_case.execute(**execute_kwargs)


@pytest.mark.asyncio
async def test_ingestion_base_resolves_team_targets_and_fallback_team_ids(
    mock_player_repository,
    mock_team_repository,
    mock_player_stats_repository,
    mock_cache,
):
    # Given
    use_case = _build_season_use_case(
        mock_player_repository,
        mock_team_repository,
        mock_player_stats_repository,
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
@pytest.mark.parametrize(
    ("scenario", "expected_api_calls"),
    [
        ("player-without-id", 0),
        ("missing-season-payload", 1),
        ("missing-internal-team", 2),
    ],
    ids=["player-without-id", "missing-season-payload", "missing-internal-team"],
)
async def test_ingest_one_group_returns_zero_for_non_persistable_scenarios(
    scenario,
    expected_api_calls,
    mock_player_repository,
    mock_team_repository,
    mock_player_stats_repository,
    mock_cache,
):
    # Given
    mock_mlb_api = AsyncMock()
    use_case = _build_season_use_case(
        mock_player_repository,
        mock_team_repository,
        mock_player_stats_repository,
        mock_cache,
        mock_mlb_api,
    )

    if scenario == "player-without-id":
        player = _build_player(player_id=None)
    elif scenario == "missing-season-payload":
        player = _build_player()
        mock_mlb_api.get_player_stats.side_effect = [None]
    else:
        player = _build_player(current_team_id=None)
        mock_team_repository.get_by_mlb_id.return_value = None
        mock_mlb_api.get_player_stats.side_effect = [
            _stats_response({"team": {"id": 119}, "stat": {"hits": 1}}),
            _stats_response(),
        ]

    # When
    result = await use_case._ingest_one_group(player, 2025, "R", "hitting", scenario != "player-without-id")

    # Then
    assert result == 0
    assert mock_mlb_api.get_player_stats.await_count == expected_api_calls
    mock_player_stats_repository.replace_group_records.assert_not_called()


@pytest.mark.asyncio
async def test_build_group_records_returns_empty_when_player_has_no_id(
    mock_player_repository,
    mock_team_repository,
    mock_player_stats_repository,
    mock_cache,
):
    # Given
    use_case = _build_season_use_case(
        mock_player_repository,
        mock_team_repository,
        mock_player_stats_repository,
        mock_cache,
    )

    # When
    records = await use_case._build_group_records(
        _build_player(player_id=None),
        2025,
        "R",
        "hitting",
        _stats_response(),
        {},
    )

    # Then
    assert records == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("player_id", "stats_response"),
    [
        (None, {}),
        (7, None),
    ],
    ids=["missing-player-id", "missing-payload"],
)
async def test_build_history_records_returns_empty_for_missing_inputs(
    player_id,
    stats_response,
    mock_player_repository,
    mock_team_repository,
    mock_player_stats_repository,
    mock_cache,
):
    # Given
    use_case = _build_history_use_case(
        mock_player_repository,
        mock_team_repository,
        mock_player_stats_repository,
        mock_cache,
    )

    # When
    records = await use_case._build_history_records(
        _build_player(player_id=player_id),
        2025,
        "R",
        "hitting",
        "gameLog",
        stats_response,
    )

    # Then
    assert records == []


@pytest.mark.asyncio
async def test_ingest_group_history_returns_zero_when_player_has_no_id(
    mock_player_repository,
    mock_team_repository,
    mock_player_stats_repository,
    mock_cache,
):
    # Given
    use_case = _build_history_use_case(
        mock_player_repository,
        mock_team_repository,
        mock_player_stats_repository,
        mock_cache,
    )

    # When
    result = await use_case._ingest_group_history(_build_player(player_id=None), 2025, "R", "hitting", None, True)

    # Then
    assert result == 0


def test_index_splits_by_team_returns_expected_mapping():
    # Given
    indexed_payload = _stats_response({"team": {"id": 119}, "stat": {"hits": 2}}, {"stat": {"hits": 1}})

    # When
    indexed_splits = _index_splits_by_team(indexed_payload)

    # Then
    assert indexed_splits[119]["stat"]["hits"] == 2
    assert indexed_splits[None]["stat"]["hits"] == 1
    assert _index_splits_by_team(None) == {}


@pytest.mark.parametrize(
    ("existing_records", "season", "force_refresh", "expected"),
    [
        ([], 2025, False, True),
        ([object()], 2025, True, True),
        ([object()], datetime.now().year - 1, False, False),
        ([object()], datetime.now().year, False, True),
    ],
    ids=[
        "refreshes-when-empty",
        "refreshes-when-forced",
        "skips-closed-season-with-data",
        "refreshes-current-season-with-data",
    ],
)
def test_should_refresh_existing_records(existing_records, season, force_refresh, expected):
    # Given / When / Then
    assert _should_refresh_existing_records(existing_records, season, force_refresh) is expected


@pytest.mark.asyncio
async def test_ingest_player_season_stats_refreshes_current_season_even_when_records_exist(
    mock_player_repository,
    mock_team_repository,
    mock_player_stats_repository,
    mock_cache,
):
    # Given
    current_year = datetime.now().year
    mock_player_stats_repository.list_group_records.return_value = [AsyncMock()]
    mock_mlb_api = AsyncMock()
    mock_mlb_api.get_player_stats.side_effect = [
        _stats_response({"team": {"id": 119}, "stat": {"hits": 3, "plateAppearances": 10}}),
        _stats_response({"team": {"id": 119}, "stat": {"ops": 0.95}}),
    ]
    use_case = _build_season_use_case(
        mock_player_repository,
        mock_team_repository,
        mock_player_stats_repository,
        mock_cache,
        mock_mlb_api,
    )

    # When
    result = await use_case.execute(season=current_year, group="hitting", player_id=7)

    # Then
    assert result["group_records_upserted"] == 1
    assert result["group_records_skipped"] == 0
    assert mock_mlb_api.get_player_stats.await_count == 2
    mock_player_stats_repository.replace_group_records.assert_awaited_once()


@pytest.mark.asyncio
async def test_ingest_player_season_stats_returns_zero_when_team_has_no_players(
    mock_team_repository,
    mock_player_stats_repository,
    mock_cache,
):
    # Given
    mock_player_repository = AsyncMock()
    mock_player_repository.list_by_team.return_value = []
    mock_mlb_api = AsyncMock()
    use_case = _build_season_use_case(
        mock_player_repository,
        mock_team_repository,
        mock_player_stats_repository,
        mock_cache,
        mock_mlb_api,
    )

    # When
    result = await use_case.execute(season=2025, group="hitting", team_id=999)

    # Then
    assert result == {
        "operation": "player_stats_seasonal_ingestion",
        "players_processed": 0,
        "group_records_upserted": 0,
        "group_records_skipped": 0,
        "season": 2025,
        "group": "hitting",
        "game_type": "R",
    }
    mock_mlb_api.get_player_stats.assert_not_called()
    mock_cache.clear.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("group", "expected_skipped"),
    [
        ("hitting", 2),
        ("all", 10),
    ],
    ids=["single-group", "all-groups"],
)
async def test_ingest_player_history_stats_skips_existing_historical_contexts(
    group,
    expected_skipped,
    mock_player_repository,
    mock_team_repository,
    mock_player_stats_repository,
    mock_cache,
):
    # Given
    closed_season = datetime.now().year - 1
    mock_player_stats_repository.list_history_records.return_value = [AsyncMock()]
    mock_mlb_api = AsyncMock()
    use_case = _build_history_use_case(
        mock_player_repository,
        mock_team_repository,
        mock_player_stats_repository,
        mock_cache,
        mock_mlb_api,
    )

    # When
    result = await use_case.execute(season=closed_season, group=group, player_id=7)

    # Then
    assert result["history_records_replaced"] == 0
    assert result["history_contexts_skipped"] == expected_skipped
    mock_mlb_api.get_player_stats.assert_not_called()


@pytest.mark.asyncio
async def test_ingest_player_history_force_refresh_reloads_closed_season_records(
    mock_player_repository,
    mock_team_repository,
    mock_player_stats_repository,
    mock_cache,
):
    # Given
    closed_season = datetime.now().year - 1
    mock_player_stats_repository.list_history_records.return_value = [AsyncMock()]
    mock_mlb_api = AsyncMock()
    mock_mlb_api.get_player_stats.side_effect = [
        _stats_response({"team": {"id": 119}, "date": "2025-03-20", "game": {"gamePk": 1}}),
        _stats_response({"team": {"id": 119}, "split": {"code": "home"}, "stat": {"hits": 4}}),
    ]
    use_case = _build_history_use_case(
        mock_player_repository,
        mock_team_repository,
        mock_player_stats_repository,
        mock_cache,
        mock_mlb_api,
    )

    # When
    result = await use_case.execute(season=closed_season, group="hitting", player_id=7, force_refresh=True)

    # Then
    assert result["history_records_replaced"] == 2
    assert result["history_contexts_skipped"] == 0
    assert mock_mlb_api.get_player_stats.await_count == 2
    assert mock_player_stats_repository.replace_history_records.await_count == 2
    mock_cache.clear.assert_awaited_once_with(pattern="player_stats:persisted:player=7:*")

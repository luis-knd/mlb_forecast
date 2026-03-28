from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from tests.unit.use_cases.player_stats_test_support_test import build_history_use_case, build_player, stats_response


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
        stats_response({"team": {"id": 119}, "date": "2025-03-20", "game": {"gamePk": 1}, "stat": {"hits": 2}}),
        stats_response({"team": {"id": 119}, "split": {"code": "home"}, "stat": {"hits": 4}}),
    ]
    use_case = build_history_use_case(
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
@pytest.mark.parametrize(
    ("player_id", "stats_response_payload"),
    [
        (None, {}),
        (7, None),
    ],
    ids=["missing-player-id", "missing-payload"],
)
async def test_build_history_records_returns_empty_for_missing_inputs(
    player_id,
    stats_response_payload,
    mock_player_repository,
    mock_team_repository,
    mock_player_stats_repository,
    mock_cache,
):
    # Given
    use_case = build_history_use_case(
        mock_player_repository,
        mock_team_repository,
        mock_player_stats_repository,
        mock_cache,
    )

    # When
    records = await use_case._build_history_records(
        build_player(player_id=player_id),
        2025,
        "R",
        "hitting",
        "gameLog",
        stats_response_payload,
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
    use_case = build_history_use_case(
        mock_player_repository,
        mock_team_repository,
        mock_player_stats_repository,
        mock_cache,
    )

    # When
    result = await use_case._ingest_group_history(build_player(player_id=None), 2025, "R", "hitting", None, True)

    # Then
    assert result == 0


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
    use_case = build_history_use_case(
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
async def test_ingest_group_history_replaces_empty_payloads_when_refresh_is_required(
    mock_player_repository,
    mock_team_repository,
    mock_player_stats_repository,
    mock_cache,
):
    # Given
    mock_mlb_api = AsyncMock()
    mock_mlb_api.get_player_stats.side_effect = [None, None]
    use_case = build_history_use_case(
        mock_player_repository,
        mock_team_repository,
        mock_player_stats_repository,
        mock_cache,
        mock_mlb_api,
    )

    # When
    replaced = await use_case._ingest_group_history(build_player(), 2025, "R", "hitting", 7, True)

    # Then
    assert replaced == 0
    assert mock_mlb_api.get_player_stats.await_count == 2
    assert mock_player_stats_repository.replace_history_records.await_count == 2
    for call in mock_player_stats_repository.replace_history_records.await_args_list:
        assert call.kwargs["records"] == []


@pytest.mark.asyncio
async def test_ingest_player_history_does_not_count_skips_for_current_season_without_replacements(
    mock_player_repository,
    mock_team_repository,
    mock_player_stats_repository,
    mock_cache,
):
    # Given
    current_year = datetime.now().year
    mock_mlb_api = AsyncMock()
    mock_mlb_api.get_player_stats.side_effect = [None, None]
    use_case = build_history_use_case(
        mock_player_repository,
        mock_team_repository,
        mock_player_stats_repository,
        mock_cache,
        mock_mlb_api,
    )

    # When
    result = await use_case.execute(season=current_year, group="hitting", player_id=7)

    # Then
    assert result["history_records_replaced"] == 0
    assert result["history_contexts_skipped"] == 0
    mock_cache.clear.assert_not_awaited()


@pytest.mark.asyncio
async def test_build_history_records_keeps_index_order_and_resolved_team_ids(
    mock_player_repository,
    mock_team_repository,
    mock_player_stats_repository,
    mock_cache,
):
    # Given
    use_case = build_history_use_case(
        mock_player_repository,
        mock_team_repository,
        mock_player_stats_repository,
        mock_cache,
    )
    stats_payload = stats_response(
        {"team": {"id": 119}, "date": "2025-03-20", "game": {"gamePk": 1}, "stat": {"hits": 2}},
        {"date": "2025-03-21", "split": {"code": "home"}, "stat": {"hits": 1}},
    )

    # When
    records = await use_case._build_history_records(build_player(), 2025, "R", "hitting", "gameLog", stats_payload)

    # Then
    assert [record.external_reference for record in records] == ["1", "2025-03-21"]
    assert [record.team_id for record in records] == [5, 5]


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
        stats_response({"team": {"id": 119}, "date": "2025-03-20", "game": {"gamePk": 1}}),
        stats_response({"team": {"id": 119}, "split": {"code": "home"}, "stat": {"hits": 4}}),
    ]
    use_case = build_history_use_case(
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


@pytest.mark.asyncio
async def test_ingest_group_history_deduplicates_exact_duplicate_records_before_persisting(
    mock_player_repository,
    mock_team_repository,
    mock_player_stats_repository,
    mock_cache,
):
    # Given
    duplicate_payload = {
        "team": {"id": 119},
        "date": "2025-03-20",
        "game": {"gamePk": 822839},
        "stat": {"gamesStarted": 1, "putOuts": 3},
    }
    mock_mlb_api = AsyncMock()
    mock_mlb_api.get_player_stats.side_effect = [stats_response(duplicate_payload, duplicate_payload), None]
    use_case = build_history_use_case(
        mock_player_repository,
        mock_team_repository,
        mock_player_stats_repository,
        mock_cache,
        mock_mlb_api,
    )

    # When
    replaced = await use_case._ingest_group_history(build_player(), 2025, "R", "fielding", None, True)

    # Then
    assert replaced == 1
    replace_call = mock_player_stats_repository.replace_history_records.await_args_list[0]
    assert len(replace_call.kwargs["records"]) == 1


@pytest.mark.asyncio
async def test_ingest_group_history_keeps_distinct_rows_with_same_game_pk(
    mock_player_repository,
    mock_team_repository,
    mock_player_stats_repository,
    mock_cache,
):
    # Given
    first_payload = {
        "team": {"id": 119},
        "date": "2025-03-20",
        "game": {"gamePk": 822839},
        "stat": {"gamesStarted": 1, "putOuts": 3},
    }
    second_payload = {
        "team": {"id": 119},
        "date": "2025-03-20",
        "game": {"gamePk": 822839},
        "stat": {"gamesStarted": 0, "putOuts": 0},
    }
    mock_mlb_api = AsyncMock()
    mock_mlb_api.get_player_stats.side_effect = [stats_response(first_payload, second_payload), None]
    use_case = build_history_use_case(
        mock_player_repository,
        mock_team_repository,
        mock_player_stats_repository,
        mock_cache,
        mock_mlb_api,
    )

    # When
    replaced = await use_case._ingest_group_history(build_player(), 2025, "R", "fielding", None, True)

    # Then
    assert replaced == 2
    replace_call = mock_player_stats_repository.replace_history_records.await_args_list[0]
    assert len(replace_call.kwargs["records"]) == 2
    assert [record.external_reference for record in replace_call.kwargs["records"]] == ["822839", "822839"]
    assert replace_call.kwargs["records"][0].history_entry_key != replace_call.kwargs["records"][1].history_entry_key

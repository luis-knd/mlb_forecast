from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from application.use_cases.player_stats_read_use_cases import (
    PLAYER_STATS_READ_TTL_SECONDS,
    GetPersistedPlayerCareerStatsUseCase,
    GetPersistedPlayerGameLogsUseCase,
    GetPersistedPlayerSeasonStatsUseCase,
    GetPersistedPlayerStatSplitsUseCase,
    GetPersistedPlayerYearByYearStatsUseCase,
    _build_cache_key,
    _filter_group,
    _get_cached_or_load,
    _sort_group_records,
    _sort_history_records,
)
from domain.entities.player_stats_records import PlayerStatsGroupRecord, PlayerStatsHistoryRecord


def _group_record(stat_group: str, season: int, team_id: int | None, metrics: dict) -> PlayerStatsGroupRecord:
    return PlayerStatsGroupRecord.create(
        player_id=7,
        team_id=team_id,
        season=season,
        game_type="R",
        stat_group=stat_group,
        metrics=metrics,
    )


def _history_record(
    stat_group: str,
    external_reference: str,
    event_date: datetime | None,
    *,
    stat_type: str | None = None,
) -> PlayerStatsHistoryRecord:
    return PlayerStatsHistoryRecord.create(
        player_id=7,
        team_id=11,
        season=2025,
        game_type="R",
        stat_group=stat_group,
        stat_type=stat_type or ("gameLog" if event_date is not None else "statSplits"),
        external_reference=external_reference,
        payload={"sample": True},
        event_date=event_date,
    )


@pytest.fixture
def mock_cache() -> AsyncMock:
    cache = AsyncMock()
    cache.get.return_value = None
    cache.set.return_value = True
    return cache


@pytest.fixture
def mock_repository() -> AsyncMock:
    return AsyncMock()


@pytest.mark.parametrize(
    ("season", "days_back", "limit", "expected"),
    [
        (
            2025,
            7,
            25,
            "player_stats:persisted:player=7:stats=gameLog:group=hitting:gameType=R:season=2025:daysBack=7:limit=25",
        ),
        (
            None,
            None,
            None,
            "player_stats:persisted:player=7:stats=career:group=all:gameType=R:season=all:daysBack=none:limit=none",
        ),
    ],
)
def test_build_cache_key_uses_expected_defaults(season, days_back, limit, expected):
    # Given / When
    cache_key = _build_cache_key(
        player_id=7,
        stats="gameLog" if season is not None else "career",
        group="hitting" if season is not None else "all",
        game_type="R",
        season=season,
        days_back=days_back,
        limit=limit,
    )

    # Then
    assert cache_key == expected


@pytest.mark.asyncio
async def test_get_cached_or_load_returns_cached_value_without_loading():
    # Given
    cache = AsyncMock()
    cache.get.return_value = ["cached"]
    loader = AsyncMock(return_value=["loaded"])

    # When
    result = await _get_cached_or_load(cache, "player_stats:key", loader)

    # Then
    assert result == ["cached"]
    loader.assert_not_awaited()
    cache.set.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_cached_or_load_stores_loaded_value_on_cache_miss():
    # Given
    cache = AsyncMock()
    cache.get.return_value = None
    loader = AsyncMock(return_value=["loaded"])

    # When
    result = await _get_cached_or_load(cache, "player_stats:key", loader)

    # Then
    assert result == ["loaded"]
    cache.get.assert_awaited_once_with("player_stats:key")
    loader.assert_awaited_once_with()
    cache.set.assert_awaited_once_with("player_stats:key", ["loaded"], ttl=PLAYER_STATS_READ_TTL_SECONDS)


def test_read_helpers_filter_and_sort_records_deterministically():
    # Given
    group_records = [
        _group_record("pitching", 2025, 10, {"wins": 1}),
        _group_record("hitting", 2025, 12, {"hits": 3}),
        _group_record("hitting", 2025, None, {"hits": 4}),
        _group_record("hitting", 2024, 11, {"hits": 5}),
    ]
    history_records = [
        _history_record("hitting", "missing-date", None, stat_type="statSplits"),
        _history_record("hitting", "dated-b", datetime(2025, 3, 20), stat_type="statSplits"),
        _history_record("hitting", "dated-a", datetime(2025, 3, 20), stat_type="statSplits"),
        _history_record("hitting", "dated-c", datetime(2025, 3, 10), stat_type="statSplits"),
    ]

    # When
    all_groups = _filter_group(group_records, "all")
    filtered_groups = _filter_group(group_records, "hitting")
    sorted_groups = _sort_group_records(group_records)
    sorted_history = _sort_history_records(history_records)

    # Then
    assert all_groups is group_records
    assert [(record.season, record.team_id) for record in filtered_groups] == [(2025, 12), (2025, None), (2024, 11)]
    assert [(record.season, record.stat_group, record.team_id) for record in sorted_groups] == [
        (2025, "pitching", 10),
        (2025, "hitting", 12),
        (2025, "hitting", None),
        (2024, "hitting", 11),
    ]
    assert [record.external_reference for record in sorted_history] == [
        "dated-b",
        "dated-a",
        "dated-c",
        "missing-date",
    ]


@pytest.mark.asyncio
async def test_get_persisted_player_season_stats_uses_cache_when_available(mock_repository):
    # Given
    cached_records = [_group_record("hitting", 2025, 11, {"hits": 5})]
    cache = AsyncMock()
    cache.get.return_value = cached_records
    use_case = GetPersistedPlayerSeasonStatsUseCase(mock_repository, cache)

    # When
    result = await use_case.execute(player_id=7, season=2025, group="hitting", game_type="R")

    # Then
    assert result == cached_records
    mock_repository.list_group_records.assert_not_called()
    cache.set.assert_not_called()


@pytest.mark.asyncio
async def test_get_persisted_player_season_stats_filters_and_sorts_records(mock_repository, mock_cache):
    # Given
    mock_repository.list_group_records.return_value = [
        _group_record("pitching", 2025, 11, {"wins": 1}),
        _group_record("hitting", 2025, 12, {"hits": 3}),
        _group_record("hitting", 2025, 11, {"hits": 5}),
    ]
    use_case = GetPersistedPlayerSeasonStatsUseCase(mock_repository, mock_cache)

    # When
    result = await use_case.execute(player_id=7, season=2025, group="hitting", game_type="R")

    # Then
    assert [record.team_id for record in result] == [12, 11]
    mock_repository.list_group_records.assert_awaited_once_with(player_id=7, season=2025, game_type="R")
    mock_cache.set.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_persisted_player_season_stats_normalizes_default_game_type_and_validates_season(
    mock_repository,
    mock_cache,
):
    # Given
    mock_repository.list_group_records.return_value = [_group_record("hitting", 2025, 11, {"hits": 5})]
    use_case = GetPersistedPlayerSeasonStatsUseCase(mock_repository, mock_cache)

    # When
    result = await use_case.execute(player_id=7, season=2025, group="all", game_type=None)

    # Then
    assert len(result) == 1
    assert result[0].stat_group == "hitting"
    mock_repository.list_group_records.assert_awaited_once_with(player_id=7, season=2025, game_type="R")

    with pytest.raises(ValueError, match="season must be greater than or equal"):
        await use_case.execute(player_id=7, season=1800, group="all", game_type="R")


@pytest.mark.asyncio
async def test_get_persisted_player_career_stats_aggregates_records_by_group(mock_repository, mock_cache):
    # Given
    mock_repository.list_group_records.return_value = [
        _group_record("hitting", 2024, 11, {"hits": 100, "plate_appearances": 400, "batting_average": 0.25}),
        _group_record("hitting", 2025, 11, {"hits": 40, "plate_appearances": 120, "batting_average": 0.2}),
        _group_record("pitching", 2025, 11, {"wins": 2, "innings_pitched": 10.0, "earned_run_average": 3.0}),
    ]
    use_case = GetPersistedPlayerCareerStatsUseCase(mock_repository, mock_cache)

    # When
    result = await use_case.execute(player_id=7, group="all", game_type="R")

    # Then
    assert [record.stat_group for record in result] == ["pitching", "hitting"]
    assert result[1].metrics["hits"] == 140


@pytest.mark.asyncio
async def test_get_persisted_player_career_stats_filters_specific_group_and_skips_missing_groups(
    mock_repository,
    mock_cache,
):
    # Given
    mock_repository.list_group_records.return_value = [
        _group_record("hitting", 2024, 11, {"hits": 100, "plate_appearances": 400, "batting_average": 0.25}),
        _group_record("pitching", 2025, 11, {"wins": 2, "innings_pitched": 10.0, "earned_run_average": 3.0}),
    ]
    use_case = GetPersistedPlayerCareerStatsUseCase(mock_repository, mock_cache)

    # When
    result = await use_case.execute(player_id=7, group="hitting", game_type=None)

    # Then
    assert len(result) == 1
    assert result[0].stat_group == "hitting"
    mock_repository.list_group_records.assert_awaited_once_with(player_id=7, game_type="R")


@pytest.mark.asyncio
async def test_get_persisted_player_career_stats_returns_empty_when_repository_has_no_records(
    mock_repository,
    mock_cache,
):
    # Given
    mock_repository.list_group_records.return_value = []
    use_case = GetPersistedPlayerCareerStatsUseCase(mock_repository, mock_cache)

    # When
    result = await use_case.execute(player_id=7, group="all", game_type="R")

    # Then
    assert result == []
    mock_cache.set.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_persisted_player_year_by_year_stats_aggregates_multi_team_seasons(mock_repository, mock_cache):
    # Given
    mock_repository.list_group_records.return_value = [
        _group_record("hitting", 2024, 11, {"hits": 100, "plate_appearances": 400, "batting_average": 0.25}),
        _group_record("hitting", 2024, 12, {"hits": 50, "plate_appearances": 200, "batting_average": 0.35}),
        _group_record("hitting", 2025, 11, {"hits": 40, "plate_appearances": 120, "batting_average": 0.2}),
    ]
    use_case = GetPersistedPlayerYearByYearStatsUseCase(mock_repository, mock_cache)

    # When
    result = await use_case.execute(player_id=7, group="hitting", game_type="R")

    # Then
    assert [record.season for record in result] == [2025, 2024]
    assert result[1].metrics["hits"] == 150


@pytest.mark.asyncio
async def test_get_persisted_player_year_by_year_stats_aggregates_all_groups(mock_repository, mock_cache):
    # Given
    mock_repository.list_group_records.return_value = [
        _group_record("hitting", 2025, 11, {"hits": 40, "plate_appearances": 120, "batting_average": 0.2}),
        _group_record("pitching", 2024, 11, {"wins": 3, "innings_pitched": 20.0, "earned_run_average": 2.5}),
    ]
    use_case = GetPersistedPlayerYearByYearStatsUseCase(mock_repository, mock_cache)

    # When
    result = await use_case.execute(player_id=7, group="all", game_type="R")

    # Then
    assert [(record.season, record.stat_group) for record in result] == [(2025, "hitting"), (2024, "pitching")]


@pytest.mark.asyncio
async def test_get_persisted_player_game_logs_applies_days_back_and_limit(mock_repository, mock_cache):
    # Given
    now = datetime.now(UTC).replace(tzinfo=None)
    mock_repository.list_history_records.return_value = [
        _history_record("hitting", "recent", now - timedelta(days=1), stat_type="gameLog"),
        _history_record("hitting", "old", now - timedelta(days=8), stat_type="gameLog"),
    ]
    use_case = GetPersistedPlayerGameLogsUseCase(mock_repository, mock_cache)

    # When
    result = await use_case.execute(player_id=7, season=2025, group="hitting", game_type="R", days_back=5, limit=50)

    # Then
    assert [record.external_reference for record in result] == ["recent"]
    mock_repository.list_history_records.assert_awaited_once_with(
        player_id=7,
        stat_type="gameLog",
        season=2025,
        game_type="R",
        stat_group="hitting",
        limit=50,
    )


@pytest.mark.asyncio
async def test_history_read_use_cases_use_none_group_when_all_is_requested(mock_repository, mock_cache):
    # Given
    mock_repository.list_history_records.return_value = []
    game_logs_use_case = GetPersistedPlayerGameLogsUseCase(mock_repository, mock_cache)
    stat_splits_use_case = GetPersistedPlayerStatSplitsUseCase(mock_repository, mock_cache)

    # When
    game_log_records = await game_logs_use_case.execute(
        player_id=7,
        season=2025,
        group="all",
        game_type="R",
        days_back=None,
        limit=5,
    )
    stat_split_records = await stat_splits_use_case.execute(
        player_id=7,
        season=2025,
        group="all",
        game_type="R",
        limit=3,
    )

    # Then
    assert game_log_records == []
    assert stat_split_records == []
    assert mock_repository.list_history_records.await_args_list[0].kwargs["stat_group"] is None
    assert mock_repository.list_history_records.await_args_list[1].kwargs["stat_group"] is None


@pytest.mark.asyncio
async def test_get_persisted_player_stat_splits_filters_specific_group_and_sorts_records(mock_repository, mock_cache):
    # Given
    recent_date = datetime(2025, 3, 20)
    old_date = datetime(2025, 3, 10)
    split_one = _history_record("hitting", "b", old_date, stat_type="statSplits")
    split_two = _history_record("hitting", "a", recent_date, stat_type="statSplits")
    mock_repository.list_history_records.return_value = [split_one, split_two]
    use_case = GetPersistedPlayerStatSplitsUseCase(mock_repository, mock_cache)

    # When
    result = await use_case.execute(player_id=7, season=2025, group="hitting", game_type="R", limit=10)

    # Then
    assert [record.external_reference for record in result] == ["a", "b"]
    mock_repository.list_history_records.assert_awaited_once_with(
        player_id=7,
        stat_type="statSplits",
        season=2025,
        game_type="R",
        stat_group="hitting",
        limit=10,
    )

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from application.use_cases.player_stats_ingestion_use_cases import (
    _group_splits_by_team,
    _should_refresh_existing_records,
    _validate_season,
    _validate_target_selector,
)
from tests.unit.use_cases.player_stats_test_support_test import (
    build_history_use_case,
    build_player,
    build_season_use_case,
    stats_response,
)


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
    use_case_factory = build_season_use_case if use_case_kind == "season" else build_history_use_case
    use_case = use_case_factory(
        mock_player_repository,
        mock_team_repository,
        mock_player_stats_repository,
        mock_cache,
    )

    # When / Then
    with pytest.raises(ValueError, match=message):
        await use_case.execute(**execute_kwargs)


@pytest.mark.parametrize(
    ("player_id", "team_id"),
    [
        (7, None),
        (None, 5),
    ],
    ids=["player-target", "team-target"],
)
def test_validate_target_selector_accepts_exactly_one_target(player_id, team_id):
    # Given / When / Then
    assert _validate_target_selector(player_id=player_id, team_id=team_id) is None


@pytest.mark.parametrize(
    ("player_id", "team_id"),
    [
        (None, None),
        (7, 5),
    ],
    ids=["missing-both-targets", "selecting-both-targets"],
)
def test_validate_target_selector_rejects_invalid_target_combinations(player_id, team_id):
    # Given / When / Then
    with pytest.raises(ValueError, match=r"^Exactly one of playerId or teamId must be provided$"):
        _validate_target_selector(player_id=player_id, team_id=team_id)


def test_validate_season_accepts_mlb_foundation_year_boundary():
    # Given / When / Then
    assert _validate_season(1876) is None


@pytest.mark.asyncio
async def test_ingestion_base_resolves_team_targets_and_fallback_team_ids(
    mock_player_repository,
    mock_team_repository,
    mock_player_stats_repository,
    mock_cache,
):
    # Given
    use_case = build_season_use_case(
        mock_player_repository,
        mock_team_repository,
        mock_player_stats_repository,
        mock_cache,
    )
    player = build_player()
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
async def test_ingestion_base_returns_empty_when_requested_player_does_not_exist(
    mock_team_repository,
    mock_player_stats_repository,
    mock_cache,
):
    # Given
    mock_player_repository = AsyncMock()
    mock_player_repository.get_by_id.return_value = None
    use_case = build_season_use_case(
        mock_player_repository,
        mock_team_repository,
        mock_player_stats_repository,
        mock_cache,
    )

    # When
    players = await use_case._resolve_target_players(player_id=999, team_id=None)

    # Then
    assert players == []
    mock_player_repository.get_by_id.assert_awaited_once_with(999)


@pytest.mark.asyncio
async def test_ingestion_base_resolves_internal_team_id_from_known_external_team(
    mock_player_repository,
    mock_team_repository,
    mock_player_stats_repository,
    mock_cache,
):
    # Given
    use_case = build_season_use_case(
        mock_player_repository,
        mock_team_repository,
        mock_player_stats_repository,
        mock_cache,
    )
    player = build_player(current_team_id=9)

    # When
    internal_team_id = await use_case._resolve_internal_team_id(player, {"team": {"id": 119}})

    # Then
    assert internal_team_id == 5
    mock_team_repository.get_by_mlb_id.assert_awaited_once_with(119)


def test_group_splits_by_team_returns_expected_mapping():
    # Given
    grouped_payload = stats_response(
        {"team": {"id": 119}, "stat": {"hits": 2}},
        {"team": {"id": 119}, "stat": {"hits": 3}},
        {"stat": {"hits": 1}},
    )

    # When
    grouped_splits = _group_splits_by_team(grouped_payload)

    # Then
    assert [split["stat"]["hits"] for split in grouped_splits[119]] == [2, 3]
    assert grouped_splits[None][0]["stat"]["hits"] == 1
    assert _group_splits_by_team(None) == {}


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

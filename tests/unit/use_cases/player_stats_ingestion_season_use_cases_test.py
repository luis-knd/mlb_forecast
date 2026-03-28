from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from tests.unit.use_cases.player_stats_test_support_test import (
    build_player,
    build_season_use_case,
    build_team,
    stats_response,
)


@pytest.mark.asyncio
async def test_ingest_player_season_stats_replaces_all_team_splits(
    mock_player_repository,
    mock_team_repository,
    mock_player_stats_repository,
    mock_mlb_api,
    mock_cache,
):
    # Given
    use_case = build_season_use_case(
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
    use_case = build_season_use_case(
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
    use_case = build_season_use_case(
        mock_player_repository,
        mock_team_repository,
        mock_player_stats_repository,
        mock_cache,
        mock_mlb_api,
    )

    if scenario == "player-without-id":
        player = build_player(player_id=None)
    elif scenario == "missing-season-payload":
        player = build_player()
        mock_mlb_api.get_player_stats.side_effect = [None]
    else:
        player = build_player(current_team_id=None)
        mock_team_repository.get_by_mlb_id.return_value = None
        mock_mlb_api.get_player_stats.side_effect = [
            stats_response({"team": {"id": 119}, "stat": {"hits": 1}}),
            stats_response(),
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
    use_case = build_season_use_case(
        mock_player_repository,
        mock_team_repository,
        mock_player_stats_repository,
        mock_cache,
    )

    # When
    records = await use_case._build_group_records(
        build_player(player_id=None),
        2025,
        "R",
        "hitting",
        stats_response(),
        {},
    )

    # Then
    assert records == []


@pytest.mark.asyncio
async def test_fetch_group_payloads_returns_empty_advanced_mapping_when_advanced_stats_are_missing(
    mock_player_repository,
    mock_team_repository,
    mock_player_stats_repository,
    mock_cache,
):
    # Given
    expected_response = stats_response({"team": {"id": 119}, "stat": {"hits": 2}})
    mock_mlb_api = AsyncMock()
    mock_mlb_api.get_player_stats.side_effect = [expected_response, None]
    use_case = build_season_use_case(
        mock_player_repository,
        mock_team_repository,
        mock_player_stats_repository,
        mock_cache,
        mock_mlb_api,
    )

    # When
    season_response, advanced_splits_by_team = await use_case._fetch_group_payloads(660271, 2025, "R", "hitting")

    # Then
    assert season_response == expected_response
    assert advanced_splits_by_team == {}


@pytest.mark.asyncio
async def test_build_group_records_merges_matching_advanced_split_and_skips_unresolved_team(
    mock_player_repository,
    mock_team_repository,
    mock_player_stats_repository,
    mock_cache,
):
    # Given
    player = build_player(current_team_id=None)
    mock_team_repository.get_by_mlb_id.side_effect = [build_team(), None]
    use_case = build_season_use_case(
        mock_player_repository,
        mock_team_repository,
        mock_player_stats_repository,
        mock_cache,
    )
    season_response = stats_response(
        {"team": {"id": 119}, "stat": {"hits": 3, "plateAppearances": 10, "avg": 0.3}},
        {"team": {"id": 147}, "stat": {"hits": 1, "plateAppearances": 4, "avg": 0.2}},
    )
    advanced_splits_by_team = {
        119: [{"team": {"id": 119}, "stat": {"ops": 0.95}}],
        147: [{"team": {"id": 147}, "stat": {"ops": 0.7}}],
    }

    # When
    records = await use_case._build_group_records(
        player,
        2025,
        "R",
        "hitting",
        season_response,
        advanced_splits_by_team,
    )

    # Then
    assert len(records) == 1
    assert records[0].team_id == 5
    assert records[0].metrics["hits"] == 3
    assert records[0].metrics["ops"] == 0.95
    assert records[0].raw_payload["seasonAdvanced"] == advanced_splits_by_team[119][0]


@pytest.mark.asyncio
async def test_build_group_records_uses_base_metrics_when_no_advanced_split_matches(
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
    season_response = stats_response({"team": {"id": 119}, "stat": {"hits": 3, "plateAppearances": 10, "avg": 0.3}})

    # When
    records = await use_case._build_group_records(
        build_player(),
        2025,
        "R",
        "hitting",
        season_response,
        {},
    )

    # Then
    assert len(records) == 1
    assert records[0].metrics["hits"] == 3
    assert records[0].metrics["batting_average"] == 0.3
    assert "ops" in records[0].metrics
    assert records[0].metrics["ops"] == 0.0
    assert records[0].raw_payload["seasonAdvanced"] is None


@pytest.mark.asyncio
async def test_build_group_records_aggregates_duplicate_team_splits_into_one_record(
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
    season_response = stats_response(
        {
            "team": {"id": 119},
            "stat": {
                "gamesPlayed": 91,
                "gamesStarted": 89,
                "putOuts": 164,
                "assists": 5,
                "errors": 2,
                "chances": 171,
                "fielding": 0.988,
                "rangeFactorPerGame": 1.86,
                "rangeFactorPer9Inn": 1.95,
                "innings": 779.2,
            },
        },
        {
            "team": {"id": 119},
            "stat": {
                "gamesPlayed": 4,
                "gamesStarted": 4,
                "putOuts": 0,
                "assists": 0,
                "errors": 0,
                "chances": 0,
                "fielding": 0.0,
                "rangeFactorPerGame": 0.0,
                "rangeFactorPer9Inn": 0.0,
                "innings": 0.0,
            },
        },
    )

    # When
    records = await use_case._build_group_records(
        build_player(),
        2025,
        "R",
        "fielding",
        season_response,
        {},
    )

    # Then
    assert len(records) == 1
    assert records[0].team_id == 5
    assert records[0].metrics["games_played"] == 95
    assert records[0].metrics["games_started"] == 93
    assert records[0].metrics["putouts"] == 164
    assert records[0].metrics["assists"] == 5
    assert records[0].metrics["errors"] == 2
    assert records[0].metrics["total_chances"] == 171
    assert records[0].metrics["fielding_percentage"] == 0.988
    assert isinstance(records[0].raw_payload["season"], list)
    assert len(records[0].raw_payload["season"]) == 2


@pytest.mark.asyncio
async def test_ingest_player_season_stats_processes_all_groups_for_team_target(
    mock_team_repository,
    mock_player_stats_repository,
    mock_cache,
):
    # Given
    mock_player_repository = AsyncMock()
    mock_player_repository.list_by_team.return_value = [build_player()]
    mock_mlb_api = AsyncMock()
    mock_mlb_api.get_player_stats.side_effect = [
        stats_response({"team": {"id": 119}, "stat": {"hits": 3, "plateAppearances": 10, "avg": 0.3}}),
        stats_response({"team": {"id": 119}, "stat": {"ops": 0.95}}),
        stats_response({"team": {"id": 119}, "stat": {"wins": 1, "inningsPitched": 5.0, "era": 2.0}}),
        stats_response({"team": {"id": 119}, "stat": {"whip": 0.9}}),
        stats_response({"team": {"id": 119}, "stat": {"gamesPlayed": 1, "chances": 4, "fielding": 1.0}}),
        stats_response({"team": {"id": 119}, "stat": {"rangeFactorPerGame": 2.0}}),
        stats_response({"team": {"id": 119}, "stat": {"gamesPlayed": 1, "stolenBases": 0, "avg": 0.2}}),
        stats_response({"team": {"id": 119}, "stat": {"ops": 0.5}}),
        stats_response(
            {"team": {"id": 119}, "stat": {"gamesPlayed": 1, "opportunities": 2, "stolenBasePercentage": 0.5}}
        ),
        stats_response({"team": {"id": 119}, "stat": {"stolenBasePercentage": 0.5}}),
    ]
    use_case = build_season_use_case(
        mock_player_repository,
        mock_team_repository,
        mock_player_stats_repository,
        mock_cache,
        mock_mlb_api,
    )

    # When
    result = await use_case.execute(season=2025, group="all", team_id=9)

    # Then
    assert result["players_processed"] == 1
    assert result["group_records_upserted"] == 5
    assert result["group_records_skipped"] == 0
    assert mock_player_stats_repository.replace_group_records.await_count == 5
    mock_cache.clear.assert_awaited_once_with(pattern="player_stats:persisted:player=7:*")


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
        stats_response({"team": {"id": 119}, "stat": {"hits": 3, "plateAppearances": 10}}),
        stats_response({"team": {"id": 119}, "stat": {"ops": 0.95}}),
    ]
    use_case = build_season_use_case(
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
    use_case = build_season_use_case(
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

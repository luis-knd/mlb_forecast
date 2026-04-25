import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from application.use_cases.team_stats_ingestion_use_cases import (
    IngestAllTeamStatsUseCase,
    IngestTeamCatchingStatsUseCase,
    IngestTeamFieldingStatsUseCase,
    IngestTeamHittingStatsUseCase,
    IngestTeamPitchingStatsUseCase,
    _build_team_mapping,
    _iter_team_stat_splits,
)


def _team(team_id: int | None, mlb_id: int) -> SimpleNamespace:
    return SimpleNamespace(id=team_id, mlb_id=mlb_id)


def _stats_payload(*, mlb_team_id: int, stat: dict) -> dict:
    return {"stats": [{"splits": [{"team": {"id": mlb_team_id}, "stat": stat}]}]}


def test_build_team_mapping_filters_out_teams_without_internal_id():
    # Given
    teams = [_team(team_id=10, mlb_id=119), _team(team_id=None, mlb_id=121)]

    # When
    mapping = _build_team_mapping(teams)

    # Then
    assert mapping == {119: 10}


def test_iter_team_stat_splits_yields_only_known_mlb_teams():
    # Given
    stats_data = {
        "stats": [
            {
                "splits": [
                    {"team": {"id": 119}, "stat": {"wins": 10}},
                    {"team": {"id": 130}, "stat": {"wins": 5}},
                ]
            }
        ]
    }

    # When
    splits = list(_iter_team_stat_splits(stats_data, team_mapping={119: 1}))

    # Then
    assert splits == [(1, {"wins": 10})]


def test_hitting_execute_returns_empty_when_api_returns_no_payload():
    # Given
    use_case = IngestTeamHittingStatsUseCase(
        hitting_stats_repository=AsyncMock(),
        team_repository=AsyncMock(list_all=AsyncMock(return_value=[_team(1, 119)])),
        mlb_api=AsyncMock(get_team_stats=AsyncMock(return_value=None)),
    )

    # When
    result = asyncio.run(use_case.execute(season=2026))

    # Then
    assert result == []


def test_hitting_execute_skips_zero_rows_and_saves_valid_rows():
    # Given
    repository = AsyncMock()
    repository.save.side_effect = lambda entity: entity
    use_case = IngestTeamHittingStatsUseCase(
        hitting_stats_repository=repository,
        team_repository=AsyncMock(list_all=AsyncMock(return_value=[_team(1, 119)])),
        mlb_api=AsyncMock(
            get_team_stats=AsyncMock(
                return_value={
                    "stats": [
                        {
                            "splits": [
                                {"team": {"id": 119}, "stat": {"gamesPlayed": "0", "atBats": "0"}},
                                {
                                    "team": {"id": 119},
                                    "stat": {
                                        "gamesPlayed": "12",
                                        "atBats": "100",
                                        "hits": "25",
                                        "avg": "0.250",
                                    },
                                },
                            ]
                        }
                    ]
                }
            )
        ),
    )

    # When
    result = asyncio.run(use_case.execute(season=2026))

    # Then
    assert len(result) == 1
    assert result[0].team_id == 1
    assert result[0].games_played == 12
    repository.save.assert_awaited_once()


def test_hitting_safe_converters_return_zero_for_invalid_values():
    # Given
    use_case = IngestTeamHittingStatsUseCase(AsyncMock(), AsyncMock(), AsyncMock())

    # When / Then
    assert use_case._safe_int_conversion("bad") == 0
    assert use_case._safe_int_conversion(None) == 0
    assert use_case._safe_float_conversion("bad") == 0.0
    assert use_case._safe_float_conversion("") == 0.0


def test_pitching_execute_skips_rows_with_zero_games_played():
    # Given
    repository = AsyncMock()
    repository.save.side_effect = lambda entity: entity
    stats_payload = {
        "stats": [
            {
                "splits": [
                    {"team": {"id": 119}, "stat": {"gamesPlayed": "0"}},
                    {"team": {"id": 119}, "stat": {"gamesPlayed": "5", "wins": "3", "era": "3.10"}},
                ]
            }
        ]
    }
    use_case = IngestTeamPitchingStatsUseCase(
        pitching_stats_repository=repository,
        team_repository=AsyncMock(list_all=AsyncMock(return_value=[_team(7, 119)])),
        mlb_api=AsyncMock(get_team_stats=AsyncMock(return_value=stats_payload)),
    )

    # When
    result = asyncio.run(use_case.execute(season=2026))

    # Then
    assert len(result) == 1
    assert result[0].team_id == 7
    assert result[0].wins == 3
    repository.save.assert_awaited_once()


def test_pitching_build_stats_maps_int_and_float_fields():
    # Given
    use_case = IngestTeamPitchingStatsUseCase(AsyncMock(), AsyncMock(), AsyncMock())

    # When
    stats = use_case._build_pitching_stats(
        team_id=12,
        season=2026,
        stat_data={"gamesPlayed": "11", "wins": "8", "runs": "40", "era": "2.98", "whip": "1.03"},
    )

    # Then
    assert stats.team_id == 12
    assert stats.games_played == 11
    assert stats.wins == 8
    assert stats.runs_allowed == 40
    assert stats.earned_run_average == pytest.approx(2.98)
    assert stats.whip == pytest.approx(1.03)


def test_fielding_execute_saves_valid_row():
    # Given
    repository = AsyncMock()
    repository.save.side_effect = lambda entity: entity
    use_case = IngestTeamFieldingStatsUseCase(
        fielding_stats_repository=repository,
        team_repository=AsyncMock(list_all=AsyncMock(return_value=[_team(9, 119)])),
        mlb_api=AsyncMock(
            get_team_stats=AsyncMock(
                return_value=_stats_payload(
                    mlb_team_id=119,
                    stat={"gamesPlayed": "20", "fielding": "0.989", "errors": "4", "innings": "180.0"},
                )
            )
        ),
    )

    # When
    result = asyncio.run(use_case.execute(season=2026))

    # Then
    assert len(result) == 1
    assert result[0].team_id == 9
    assert result[0].games_played == 20
    assert result[0].errors == 4
    assert result[0].fielding_percentage == pytest.approx(0.989)


def test_catching_execute_saves_valid_row():
    # Given
    repository = AsyncMock()
    repository.save.side_effect = lambda entity: entity
    use_case = IngestTeamCatchingStatsUseCase(
        catching_stats_repository=repository,
        team_repository=AsyncMock(list_all=AsyncMock(return_value=[_team(3, 119)])),
        mlb_api=AsyncMock(
            get_team_stats=AsyncMock(
                return_value=_stats_payload(
                    mlb_team_id=119,
                    stat={
                        "gamesPlayed": "15",
                        "passedBall": "2",
                        "stolenBases": "11",
                        "caughtStealing": "4",
                        "strikeoutWalkRatio": "1.50",
                    },
                )
            )
        ),
    )

    # When
    result = asyncio.run(use_case.execute(season=2026))

    # Then
    assert len(result) == 1
    assert result[0].team_id == 3
    assert result[0].games_played == 15
    assert result[0].passed_balls == 2
    assert result[0].strikeout_walk_ratio == pytest.approx(1.5)


def test_ingest_all_team_stats_aggregates_all_child_results():
    # Given
    hitting_use_case = AsyncMock(execute=AsyncMock(return_value=["h1"]))
    pitching_use_case = AsyncMock(execute=AsyncMock(return_value=["p1"]))
    fielding_use_case = AsyncMock(execute=AsyncMock(return_value=["f1"]))
    catching_use_case = AsyncMock(execute=AsyncMock(return_value=["c1"]))

    use_case = IngestAllTeamStatsUseCase(
        hitting_stats_use_case=hitting_use_case,
        pitching_stats_use_case=pitching_use_case,
        fielding_stats_use_case=fielding_use_case,
        catching_stats_use_case=catching_use_case,
    )

    # When
    result = asyncio.run(use_case.execute(season=2026))

    # Then
    assert result == {
        "hitting_stats": ["h1"],
        "pitching_stats": ["p1"],
        "fielding_stats": ["f1"],
        "catching_stats": ["c1"],
    }

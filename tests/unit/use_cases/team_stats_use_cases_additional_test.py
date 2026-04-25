import asyncio
from unittest.mock import AsyncMock

from application.use_cases.team_stats_use_cases import (
    GetTeamStatsUseCase,
    IngestTeamStatsUseCase,
    ListTeamStatsBySeason,
    ListTopTeamsByStatUseCase,
    UpdateTeamStatsUseCase,
)
from domain.entities.team import Team
from domain.entities.team_stats import TeamStats
from domain.value_objects.team_stats_category import TeamStatsCategory


def _team(*, team_id: int | None, mlb_id: int) -> Team:
    team = Team.create(
        mlb_id=mlb_id,
        name=f"Team {mlb_id}",
        abbreviation=f"T{mlb_id}",
        city="City",
        division="Division",
        league="League",
        venue_name="Venue",
    )
    team.id = team_id
    return team


def test_get_team_stats_use_case_returns_cached_payload():
    # Given
    cache = AsyncMock(get=AsyncMock(return_value={"cached": True}), set=AsyncMock())
    repository = AsyncMock()
    use_case = GetTeamStatsUseCase(repository, cache)

    # When
    result = asyncio.run(use_case.execute(team_id=9, season=2026, category=TeamStatsCategory.ALL))

    # Then
    assert result == {"cached": True}
    repository.get_by_team_and_season.assert_not_awaited()


def test_get_team_stats_use_case_filters_categories_and_caches_result():
    # Given
    team_stats = {
        "hitting_stats": {"ops": 0.812},
        "pitching": {"era": 3.2},
        "fielding_stats": {"errors": 55},
        "catching": {"passed_balls": 7},
    }
    cache = AsyncMock(get=AsyncMock(return_value=None), set=AsyncMock())
    repository = AsyncMock(get_by_team_and_season=AsyncMock(return_value=team_stats))
    use_case = GetTeamStatsUseCase(repository, cache)

    # When
    result = asyncio.run(use_case.execute(team_id=9, season=2026, category=TeamStatsCategory.HITTING))

    # Then
    assert result["hitting_stats"] == {"ops": 0.812}
    assert result["pitching"] is None
    assert result["fielding_stats"] is None
    assert result["catching"] is None
    cache.set.assert_awaited_once()


def test_get_team_stats_use_case_returns_none_when_repository_has_no_data():
    # Given
    cache = AsyncMock(get=AsyncMock(return_value=None), set=AsyncMock())
    repository = AsyncMock(get_by_team_and_season=AsyncMock(return_value=None))
    use_case = GetTeamStatsUseCase(repository, cache)

    # When
    result = asyncio.run(use_case.execute(team_id=9, season=2026, category=TeamStatsCategory.ALL))

    # Then
    assert result is None
    cache.set.assert_not_awaited()


def test_list_and_top_team_stats_delegate_to_repository():
    # Given
    repository = AsyncMock(
        list_by_season=AsyncMock(return_value=["season-stats"]),
        list_top_teams_by_stat=AsyncMock(return_value=["top-stats"]),
    )

    # When
    by_season = asyncio.run(ListTeamStatsBySeason(repository).execute(season=2026))
    top = asyncio.run(
        ListTopTeamsByStatUseCase(repository).execute(season=2026, stat_name="wins", limit=5, descending=False)
    )

    # Then
    assert by_season == ["season-stats"]
    assert top == ["top-stats"]
    repository.list_by_season.assert_awaited_once_with(2026)
    repository.list_top_teams_by_stat.assert_awaited_once_with(2026, "wins", 5, False)


def test_ingest_team_stats_skips_missing_api_data_and_teams_without_id():
    # Given
    team_stats_repository = AsyncMock(save=AsyncMock(side_effect=lambda stats: stats))
    team_repository = AsyncMock(
        list_all=AsyncMock(return_value=[_team(team_id=1, mlb_id=119), _team(team_id=None, mlb_id=121)])
    )

    mlb_api = AsyncMock()
    mlb_api.get_team_stats.side_effect = [
        {"games_played": 20, "wins": 12, "losses": 8, "runs_scored": 100},
        {"games_played": 21, "wins": 10, "losses": 11, "runs_scored": 95},
    ]

    use_case = IngestTeamStatsUseCase(team_stats_repository, team_repository, mlb_api)

    # When
    result = asyncio.run(use_case.execute(season=2026))

    # Then
    assert len(result) == 1
    assert result[0].team_id == 1
    team_stats_repository.save.assert_awaited_once()


def test_update_team_stats_updates_calculated_fields_and_saves():
    # Given
    existing = TeamStats.create(team_id=1, season=2026, runs_scored=120, runs_allowed=100)
    existing.id = 7

    repository = AsyncMock(
        update_stats=AsyncMock(return_value=existing),
        save=AsyncMock(side_effect=lambda stats: stats),
    )
    use_case = UpdateTeamStatsUseCase(repository)

    # When
    result = asyncio.run(use_case.execute(stats_id=7, updated_stats={"runs_scored": 120, "runs_allowed": 100}))

    # Then
    assert result is existing
    assert result.run_differential == 20
    repository.save.assert_awaited_once_with(existing)


def test_update_team_stats_returns_none_when_repository_update_fails():
    # Given
    repository = AsyncMock(update_stats=AsyncMock(return_value=None), save=AsyncMock())
    use_case = UpdateTeamStatsUseCase(repository)

    # When
    result = asyncio.run(use_case.execute(stats_id=99, updated_stats={"wins": 1}))

    # Then
    assert result is None
    repository.save.assert_not_awaited()

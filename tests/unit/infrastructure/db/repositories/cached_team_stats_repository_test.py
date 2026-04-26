from unittest.mock import AsyncMock

import pytest

from domain.entities.team_stats import TeamStats
from infrastructure.db.repositories.cached_team_stats_repository import CachedTeamStatsRepository


@pytest.fixture
def repository():
    repo = AsyncMock()
    cache = AsyncMock()
    return CachedTeamStatsRepository(repo, cache), repo, cache


@pytest.fixture
def team_stats():
    return TeamStats.create(team_id=7, season=2026, wins=90, losses=72)


@pytest.mark.asyncio
async def test_list_methods_use_cache_and_store_on_miss(repository, team_stats):
    # Given
    cached_repo, repo, cache = repository
    cache.get.side_effect = [None, None, None]
    repo.list_by_team.return_value = [team_stats]
    repo.list_by_season.return_value = [team_stats]
    repo.list_top_teams_by_stat.return_value = [team_stats]

    # When
    by_team = await cached_repo.list_by_team(7)
    by_season = await cached_repo.list_by_season(2026)
    top = await cached_repo.list_top_teams_by_stat(2026, "wins", 5, True)

    # Then
    assert len(by_team) == 1
    assert len(by_season) == 1
    assert len(top) == 1
    assert cache.set.await_count == 3


@pytest.mark.asyncio
async def test_update_and_delete_invalidate_related_keys(repository, team_stats):
    # Given
    cached_repo, repo, cache = repository
    team_stats.id = 11
    repo.update_stats.return_value = team_stats
    repo.delete.return_value = True
    cache.get.return_value = None
    repo.get_by_id.return_value = team_stats

    # When
    updated = await cached_repo.update_stats(11, {"wins": 91})
    deleted = await cached_repo.delete(11)

    # Then
    assert updated is team_stats
    assert deleted is True
    cache.delete.assert_any_await("team_stats:id:11")
    cache.delete.assert_any_await("team_stats:7:2026")
    cache.clear.assert_any_await(pattern="team_stats:top:2026:*")

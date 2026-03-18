from unittest.mock import AsyncMock, MagicMock

import pytest

from domain.entities.team_stats import TeamStats
from infrastructure.db.repositories.cached_team_stats_repository import CachedTeamStatsRepository


@pytest.fixture
def mock_repository():
    return MagicMock()


@pytest.fixture
def mock_cache():
    cache = MagicMock()
    cache.get = AsyncMock()
    cache.set = AsyncMock()
    cache.delete = AsyncMock()
    cache.clear = AsyncMock()
    return cache


@pytest.fixture
def cached_repo(mock_repository, mock_cache):
    return CachedTeamStatsRepository(mock_repository, mock_cache)


@pytest.fixture
def sample_team_stats():
    return TeamStats(
        id=1,
        team_id=10,
        season=2023,
        games_played=162,
        wins=90,
        losses=72,
        runs_scored=700,
        runs_allowed=600,
        hits=1400,
        home_runs=200,
        batting_average=0.250,
        on_base_percentage=0.320,
        slugging_percentage=0.420,
        ops=0.740,
        stolen_bases=100,
        earned_run_average=3.50,
        whip=1.20,
        home_runs_allowed=180,
        fielding_percentage=0.985,
        errors=80,
        double_plays=140,
        run_differential=100,
        pythagorean_expectation=0.583,
    )


@pytest.mark.asyncio
async def test_get_by_id_cache_hit(cached_repo, mock_cache, sample_team_stats):
    # Setup
    mock_cache.get.return_value = sample_team_stats

    # Execute
    result = await cached_repo.get_by_id(1)

    # Assert
    assert result == sample_team_stats
    mock_cache.get.assert_called_once_with("team_stats:id:1")
    cached_repo.repository.get_by_id.assert_not_called()


@pytest.mark.asyncio
async def test_get_by_id_cache_miss(cached_repo, mock_cache, sample_team_stats):
    # Setup
    mock_cache.get.return_value = None
    cached_repo.repository.get_by_id = AsyncMock(return_value=sample_team_stats)

    # Execute
    result = await cached_repo.get_by_id(1)

    # Assert
    assert result == sample_team_stats
    mock_cache.get.assert_called_once_with("team_stats:id:1")
    cached_repo.repository.get_by_id.assert_called_once_with(1)
    mock_cache.set.assert_called_once_with("team_stats:id:1", sample_team_stats, ttl=3600)


@pytest.mark.asyncio
async def test_save_invalidates_cache(cached_repo, mock_cache, sample_team_stats):
    # Setup
    cached_repo.repository.save = AsyncMock(return_value=sample_team_stats)

    # Execute
    await cached_repo.save(sample_team_stats)

    # Assert
    cached_repo.repository.save.assert_called_once_with(sample_team_stats)
    mock_cache.delete.assert_any_call("team_stats:id:1")
    mock_cache.delete.assert_any_call("team_stats:10:2023")
    mock_cache.clear.assert_called_once_with(pattern="team_stats:top:2023:*")


@pytest.mark.asyncio
async def test_delete_invalidates_cache(cached_repo, mock_cache, sample_team_stats):
    # Setup
    cached_repo.get_by_id = AsyncMock(return_value=sample_team_stats)
    cached_repo.repository.delete = AsyncMock(return_value=True)

    # Execute
    result = await cached_repo.delete(1)

    # Assert
    assert result is True
    mock_cache.delete.assert_any_call("team_stats:id:1")
    mock_cache.delete.assert_any_call("team_stats:10:2023")

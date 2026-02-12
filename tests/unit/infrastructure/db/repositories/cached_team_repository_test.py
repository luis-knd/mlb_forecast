from unittest.mock import AsyncMock

import pytest

from src.domain.entities.team import Team
from src.infrastructure.db.repositories.cached_team_repository import CachedTeamRepository


class TestCachedTeamRepository:
    @pytest.fixture
    def mock_repo(self):
        return AsyncMock()

    @pytest.fixture
    def mock_cache(self):
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_repo, mock_cache):
        return CachedTeamRepository(mock_repo, mock_cache)

    @pytest.fixture
    def sample_team(self):
        return Team.create(
            mlb_id=1,
            name="Team A",
            abbreviation="TA",
            city="City A",
            division="Div A",
            league="Lg A",
            venue_name="Venue A",
        )

    @pytest.mark.asyncio
    async def test_get_by_id_returns_cached(self, repo, mock_cache, mock_repo, sample_team):
        mock_cache.get.return_value = sample_team

        result = await repo.get_by_id(1)

        assert result == sample_team
        mock_cache.get.assert_called_once_with("teams:id:1")
        mock_repo.get_by_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_by_id_fetches_and_caches(self, repo, mock_cache, mock_repo, sample_team):
        mock_cache.get.return_value = None
        mock_repo.get_by_id.return_value = sample_team

        result = await repo.get_by_id(1)

        assert result == sample_team
        mock_repo.get_by_id.assert_called_once_with(1)
        mock_cache.set.assert_called_once()
        args = mock_cache.set.call_args
        assert args[0][0] == "teams:id:1"
        assert args[0][1] == sample_team

    @pytest.mark.asyncio
    async def test_list_all_returns_cached(self, repo, mock_cache, mock_repo, sample_team):
        mock_cache.get.return_value = [sample_team]

        result = await repo.list_all()

        assert result == [sample_team]
        mock_cache.get.assert_called_once_with("teams:list:all:all")
        mock_repo.list_all.assert_not_called()

    @pytest.mark.asyncio
    async def test_save_invalidates_cache(self, repo, mock_cache, mock_repo, sample_team):
        mock_repo.save.return_value = sample_team
        # Ensure sample_team has an id set for cache key construction
        sample_team.id = 100

        await repo.save(sample_team)

        mock_cache.delete.assert_any_call("teams:id:100")
        mock_cache.delete.assert_any_call("teams:mlb_id:1")
        mock_cache.delete_pattern.assert_called_once_with("teams:list:*")

    @pytest.mark.asyncio
    async def test_delete_invalidates_cache(self, repo, mock_cache, mock_repo, sample_team):
        mock_repo.get_by_id.return_value = sample_team
        mock_repo.delete.return_value = True
        sample_team.id = 100

        await repo.delete(100)

        mock_cache.delete.assert_any_call("teams:id:100")
        mock_cache.delete.assert_any_call("teams:mlb_id:1")
        mock_cache.delete_pattern.assert_called_once_with("teams:list:*")

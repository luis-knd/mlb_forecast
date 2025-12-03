from unittest.mock import AsyncMock

import pytest

from src.application.use_cases.team_use_cases import VALID_DIVISIONS, VALID_LEAGUES, ListTeamsUseCase
from src.domain.entities.team import Team
from src.interface.rest.exception_handlers import DomainExceptions


class TestListTeamsUseCase:
    """Unit tests for ListTeamsUseCase with mocked dependencies"""

    @pytest.fixture
    def mock_repository(self):
        return AsyncMock()

    @pytest.fixture
    def mock_cache(self):
        cache = AsyncMock()
        cache.get.return_value = None  # Cache miss
        return cache

    @pytest.fixture
    def use_case(self, mock_repository, mock_cache):
        return ListTeamsUseCase(mock_repository, mock_cache)

    @pytest.fixture
    def american_west_teams(self):
        return [
            Team.create(
                133,
                "Oakland Athletics",
                "OAK",
                "Oakland",
                "American League West",
                "American League",
                "Oakland Coliseum",
            ),
            Team.create(
                136, "Seattle Mariners", "SEA", "Seattle", "American League West", "American League", "T-Mobile Park"
            ),
        ]

    @pytest.mark.asyncio
    async def test_execute_with_combined_filters(self, mock_repository, mock_cache, american_west_teams):
        use_case = ListTeamsUseCase(mock_repository, mock_cache)

        # Given
        mock_repository.list_by_league_and_division.return_value = american_west_teams

        # When
        result = await use_case.execute(league="American", division="West")

        # Then
        mock_repository.list_by_league_and_division.assert_called_once_with("American", "West")
        assert len(result) == 2
        assert all("American League" in team.league and "West" in team.division for team in result)

    @pytest.mark.asyncio
    async def test_execute_league_filter_only(self, mock_repository, mock_cache):
        # Given
        mock_teams = [
            Team.create(
                133,
                "Oakland Athletics",
                "OAK",
                "Oakland",
                "American League West",
                "American League",
                "Oakland Coliseum",
            )
        ]
        mock_repository.list_by_league.return_value = mock_teams
        use_case = ListTeamsUseCase(mock_repository, mock_cache)

        # When
        result = await use_case.execute(league="American")

        # Then
        mock_repository.list_by_league.assert_called_once_with("American")
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_execute_division_filter_only(self, mock_repository, mock_cache):
        # Given
        mock_teams = [
            Team.create(
                133,
                "Oakland Athletics",
                "OAK",
                "Oakland",
                "American League West",
                "American League",
                "Oakland Coliseum",
            )
        ]
        mock_repository.list_by_division.return_value = mock_teams
        use_case = ListTeamsUseCase(mock_repository, mock_cache)

        # When
        result = await use_case.execute(division="West")

        # Then
        mock_repository.list_by_division.assert_called_once_with("West")
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_execute_no_filters(self, mock_repository, mock_cache, american_west_teams):
        # Given
        mock_repository.list_all.return_value = american_west_teams
        use_case = ListTeamsUseCase(mock_repository, mock_cache)

        # When
        result = await use_case.execute()

        # Then
        mock_repository.list_all.assert_called_once()
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_league_normalization(self, mock_repository, mock_cache):
        # Given
        mock_teams = []
        mock_repository.list_by_league.return_value = mock_teams
        use_case = ListTeamsUseCase(mock_repository, mock_cache)

        # When
        await use_case.execute(league="american")

        # Then
        mock_repository.list_by_league.assert_called_once_with("American")

    @pytest.mark.asyncio
    async def test_invalid_league_raises_error(self, mock_repository, mock_cache):
        # Given
        use_case = ListTeamsUseCase(mock_repository, mock_cache)
        expected_error = f"Invalid league: `Invalid League`. Expected one of these values: {VALID_LEAGUES}"

        # When, Then
        with pytest.raises(DomainExceptions.InvalidDataError, match=expected_error):
            await use_case.execute(league="Invalid League")

    @pytest.mark.asyncio
    async def test_invalid_division_raises_error(self, mock_repository, mock_cache):
        # Given
        use_case = ListTeamsUseCase(mock_repository, mock_cache)
        expected_error = f"Invalid division: `Invalid Division`. Expected one of these values: {VALID_DIVISIONS}"

        # When, Then
        with pytest.raises(DomainExceptions.InvalidDataError, match=expected_error):
            await use_case.execute(division="Invalid Division")

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_data(self, mock_repository, mock_cache, american_west_teams):
        # Given
        mock_cache.get.return_value = american_west_teams
        use_case = ListTeamsUseCase(mock_repository, mock_cache)

        # When
        result = await use_case.execute(league="American", division="West")

        # Then
        mock_cache.get.assert_called_once_with("teams:list:American:West")
        mock_repository.list_by_league_and_division.assert_not_called()
        assert result == american_west_teams

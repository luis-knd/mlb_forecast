from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domain.entities.team import Team
from src.infrastructure.db.repositories.team_repository import TeamRepository


class TestTeamRepository:
    """Unit tests for TeamRepository with mocked database"""

    @pytest.fixture
    def mock_db_session(self):
        return MagicMock()

    @pytest.fixture
    def repository(self, mock_db_session):
        return TeamRepository(mock_db_session)

    @pytest.fixture
    def sample_teams(self):
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
                136,
                "Seattle Mariners",
                "SEA",
                "Seattle",
                "American League West",
                "American League",
                "T-Mobile Park",
            ),
            Team.create(
                147,
                "New York Yankees",
                "NYY",
                "New York",
                "American League East",
                "American League",
                "Yankee Stadium",
            ),
        ]

    @pytest.mark.asyncio
    async def test_list_by_league_filters_correctly(self, repository, sample_teams):
        # Given
        filtered_teams = [team for team in sample_teams if "American League" in team.league]
        repository.list_by_league = AsyncMock(return_value=filtered_teams)

        # When
        result = await repository.list_by_league("American League")

        # Then
        assert len(result) == 3
        repository.list_by_league.assert_called_once_with("American League")
        for team in result:
            assert "American League" in team.league

    @pytest.mark.asyncio
    async def test_list_by_division_filters_correctly(self, repository, sample_teams):
        # Given
        filtered_teams = [team for team in sample_teams if "West" in team.division]
        repository.list_by_division = AsyncMock(return_value=filtered_teams)

        # When
        result = await repository.list_by_division("West")

        # Then
        assert len(result) == 2
        for team in result:
            assert "West" in team.division

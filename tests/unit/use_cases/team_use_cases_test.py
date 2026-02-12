from unittest.mock import AsyncMock

import pytest

from src.application.dto.mlb_api_response import MLBTeamDTO
from src.application.use_cases.team_use_cases import (
    VALID_DIVISIONS,
    VALID_LEAGUES,
    GetTeamUseCase,
    IngestTeamsUseCase,
    ListTeamsUseCase,
)
from src.domain.entities.team import Team
from src.interface.rest.exception_handlers import DomainExceptions


class TestListTeamsUseCase:
    """Unit tests for ListTeamsUseCase with mocked dependencies"""

    @pytest.fixture
    def mock_repository(self):
        return AsyncMock()

    @pytest.fixture
    def use_case(self, mock_repository):
        return ListTeamsUseCase(mock_repository)

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
    async def test_execute_with_combined_filters(self, mock_repository, american_west_teams):
        use_case = ListTeamsUseCase(mock_repository)

        # Given
        mock_repository.list_by_league_and_division.return_value = american_west_teams

        # When
        result = await use_case.execute(league="American", division="West")

        # Then
        mock_repository.list_by_league_and_division.assert_called_once_with("American", "West")
        assert len(result) == 2
        assert all("American League" in team.league and "West" in team.division for team in result)

    @pytest.mark.asyncio
    async def test_execute_league_filter_only(self, mock_repository):
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
        use_case = ListTeamsUseCase(mock_repository)

        # When
        result = await use_case.execute(league="American")

        # Then
        mock_repository.list_by_league.assert_called_once_with("American")
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_execute_division_filter_only(self, mock_repository):
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
        use_case = ListTeamsUseCase(mock_repository)

        # When
        result = await use_case.execute(division="West")

        # Then
        mock_repository.list_by_division.assert_called_once_with("West")
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_execute_no_filters(self, mock_repository, american_west_teams):
        # Given
        mock_repository.list_all.return_value = american_west_teams
        use_case = ListTeamsUseCase(mock_repository)

        # When
        result = await use_case.execute()

        # Then
        mock_repository.list_all.assert_called_once()
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_league_normalization(self, mock_repository):
        # Given
        mock_teams = []
        mock_repository.list_by_league.return_value = mock_teams
        use_case = ListTeamsUseCase(mock_repository)

        # When
        await use_case.execute(league="american")

        # Then
        mock_repository.list_by_league.assert_called_once_with("American")

    @pytest.mark.asyncio
    async def test_invalid_league_raises_error(self, mock_repository):
        # Given
        use_case = ListTeamsUseCase(mock_repository)
        expected_error = f"Invalid league: `Invalid League`. Expected one of these values: {VALID_LEAGUES}"

        # When, Then
        with pytest.raises(DomainExceptions.InvalidDataError, match=expected_error):
            await use_case.execute(league="Invalid League")

    @pytest.mark.asyncio
    async def test_invalid_division_raises_error(self, mock_repository):
        # Given
        use_case = ListTeamsUseCase(mock_repository)
        expected_error = f"Invalid division: `Invalid Division`. Expected one of these values: {VALID_DIVISIONS}"

        # When, Then
        with pytest.raises(DomainExceptions.InvalidDataError, match=expected_error):
            await use_case.execute(division="Invalid Division")


class TestGetTeamUseCase:
    """Unit tests for GetTeamUseCase"""

    @pytest.fixture
    def mock_repository(self):
        return AsyncMock()

    @pytest.fixture
    def use_case(self, mock_repository):
        return GetTeamUseCase(mock_repository)

    @pytest.mark.asyncio
    async def test_execute_returns_team(self, mock_repository, use_case):
        # Given
        team = Team.create(1, "Team", "TM", "City", "Div", "Lg", "Venue")
        mock_repository.get_by_id.return_value = team

        # When
        result = await use_case.execute(1)

        # Then
        assert result == team
        mock_repository.get_by_id.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_execute_raises_error_invalid_id(self, use_case):
        # When, Then
        with pytest.raises(DomainExceptions.InvalidDataError, match="Invalid team ID"):
            await use_case.execute(0)

    @pytest.mark.asyncio
    async def test_execute_raises_error_not_found(self, mock_repository, use_case):
        # Given
        mock_repository.get_by_id.return_value = None

        # When, Then
        with pytest.raises(DomainExceptions.TeamNotFoundError):
            await use_case.execute(999)


class TestIngestTeamsUseCase:
    """Unit tests for IngestTeamsUseCase"""

    @pytest.fixture
    def mock_repository(self):
        return AsyncMock()

    @pytest.fixture
    def mock_mlb_api(self):
        return AsyncMock()

    @pytest.fixture
    def use_case(self, mock_repository, mock_mlb_api):
        return IngestTeamsUseCase(mock_repository, mock_mlb_api)

    @pytest.mark.asyncio
    async def test_execute_ingests_teams(self, mock_repository, mock_mlb_api, use_case):
        # Given
        mlb_teams_dto = [
            MLBTeamDTO(
                id=1,
                name="Team 1",
                abbreviation="T1",
                city="City 1",
                division="Div 1",
                league="Lg 1",
                venue_name="Venue 1",
            )
        ]
        mock_mlb_api.get_teams.return_value = mlb_teams_dto

        saved_team = Team.create(1, "Team 1", "T1", "City 1", "Div 1", "Lg 1", "Venue 1")
        mock_repository.save.return_value = saved_team

        # When
        result = await use_case.execute()

        # Then
        mock_mlb_api.get_teams.assert_called_once()
        mock_repository.save.assert_called_once()
        assert len(result) == 1
        assert result[0] == saved_team

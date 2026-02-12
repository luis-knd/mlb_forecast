from datetime import date, datetime
from unittest.mock import AsyncMock

import pytest

from src.application.dto.mlb_api_response import MLBGameDTO
from src.application.use_cases.game_use_cases import IngestGamesUseCase
from src.domain.entities.game import Game
from src.domain.entities.team import Team


class TestIngestGamesUseCase:
    """Unit tests for IngestGamesUseCase"""

    @pytest.fixture
    def mock_game_repository(self):
        return AsyncMock()

    @pytest.fixture
    def mock_team_repository(self):
        return AsyncMock()

    @pytest.fixture
    def mock_mlb_api(self):
        return AsyncMock()

    @pytest.fixture
    def mock_cache(self):
        return AsyncMock()

    @pytest.fixture
    def use_case(self, mock_game_repository, mock_team_repository, mock_mlb_api, mock_cache):
        return IngestGamesUseCase(mock_game_repository, mock_team_repository, mock_mlb_api, mock_cache)

    @pytest.mark.asyncio
    async def test_execute_ingests_games_successfully(
        self, use_case, mock_mlb_api, mock_team_repository, mock_game_repository, mock_cache
    ):
        # Given
        game_date = date(2025, 6, 4)

        # Mock MLB API response with DTOs
        mlb_game_dto = MLBGameDTO(
            id=12345,
            home_team_id=101,
            away_team_id=102,
            game_date=datetime(2025, 6, 4, 19, 0),
            status="Final",
            scheduled_innings=9,
            home_score=5,
            away_score=3,
            winning_team_id=101,
        )
        mock_mlb_api.get_games_by_date.return_value = [mlb_game_dto]

        # Mock Team Repository responses
        home_team = Team(
            id=1,
            mlb_id=101,
            name="Home Team",
            abbreviation="HT",
            city="City",
            division="Div",
            league="Lg",
            venue_name="Venue",
        )
        away_team = Team(
            id=2,
            mlb_id=102,
            name="Away Team",
            abbreviation="AT",
            city="City",
            division="Div",
            league="Lg",
            venue_name="Venue",
        )

        mock_team_repository.get_by_mlb_id.side_effect = lambda mlb_id: {101: home_team, 102: away_team}.get(mlb_id)

        # Mock Game Repository save
        expected_game = Game.create(
            mlb_game_id=12345,
            home_team_id=1,
            away_team_id=2,
            game_date=datetime(2025, 6, 4, 19, 0),
            status="Final",
            scheduled_innings=9,
            home_score=5,
            away_score=3,
        )
        expected_game.winning_team_id = 1

        mock_game_repository.save.return_value = expected_game

        # When
        result = await use_case.execute(game_date=game_date)

        # Then
        mock_mlb_api.get_games_by_date.assert_called_once_with(game_date)
        assert mock_team_repository.get_by_mlb_id.call_count == 2
        mock_game_repository.save.assert_called_once()
        mock_cache.clear.assert_called_once_with(pattern="games:*")

        # Verify the game passed to save matches expected
        saved_game_arg = mock_game_repository.save.call_args[0][0]
        assert saved_game_arg.mlb_game_id == 12345
        assert saved_game_arg.home_team_id == 1
        assert saved_game_arg.away_team_id == 2
        assert saved_game_arg.winning_team_id == 1
        assert len(result) == 1

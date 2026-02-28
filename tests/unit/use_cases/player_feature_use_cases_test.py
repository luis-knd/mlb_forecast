from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from src.application.dto.mlb_api_response import MLBPlayerDTO
from src.application.use_cases.player_use_cases import (
    GetPlayerByMlbIdUseCase,
    GetPlayerStatsUseCase,
    IngestPlayersBySourceUseCase,
    ListPlayersUseCase,
)
from src.domain.entities.player import Player
from src.domain.entities.team import Team


@pytest.fixture
def sample_player() -> Player:
    return Player(
        id=10,
        mlb_id=660271,
        first_name="Shohei",
        last_name="Ohtani",
        position="DH",
        bats="L",
        throws="R",
        birth_date=datetime(1994, 7, 5, tzinfo=timezone.utc),
        active=True,
        current_team_id=1,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_cache() -> AsyncMock:
    cache = AsyncMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock(return_value=True)
    cache.clear = AsyncMock(return_value=0)
    return cache


class TestGetPlayerByMlbIdUseCase:
    @pytest.mark.asyncio
    async def test_returns_cached_player(self, sample_player):
        # Given
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=sample_player)
        player_repository = AsyncMock()
        use_case = GetPlayerByMlbIdUseCase(player_repository, cache)

        # When
        result = await use_case.execute(mlb_player_id=660271)

        # Then
        assert result is sample_player
        cache.get.assert_called_once_with("players:mlb_id:660271")
        player_repository.get_by_mlb_id.assert_not_called()


class TestListPlayersUseCase:
    @pytest.mark.asyncio
    async def test_lists_players_with_filters_and_sets_cache(
        self,
        sample_player,
        mock_cache,
    ):
        # Given
        player_repository = AsyncMock()
        player_repository.list_players = AsyncMock(return_value=[sample_player])
        use_case = ListPlayersUseCase(player_repository, mock_cache)

        # When
        result = await use_case.execute(
            team_id=1,
            position="DH",
            name="sho",
            active=True,
            limit=20,
            offset=0,
        )

        # Then
        assert result == [sample_player]
        player_repository.list_players.assert_called_once_with(
            team_id=1,
            position="DH",
            name="sho",
            active=True,
            limit=20,
            offset=0,
        )
        mock_cache.set.assert_called_once()


class TestGetPlayerStatsUseCase:
    @pytest.mark.asyncio
    async def test_raises_error_for_invalid_stats_type(self, mock_cache):
        # Given
        mlb_api = AsyncMock()
        use_case = GetPlayerStatsUseCase(mlb_api, mock_cache)

        # When / Then
        with pytest.raises(ValueError, match="stats must be one of"):
            await use_case.execute(
                mlb_player_id=660271,
                stats="invalid",
                group="hitting",
            )

    @pytest.mark.asyncio
    async def test_fetches_stats_and_caches_response(self, mock_cache):
        # Given
        mlb_api = AsyncMock()
        mlb_api.get_player_stats = AsyncMock(return_value={"player_id": 660271, "stats_data": [{"x": 1}]})
        use_case = GetPlayerStatsUseCase(mlb_api, mock_cache)

        # When
        result = await use_case.execute(
            mlb_player_id=660271,
            stats="season",
            group="hitting",
            season=2025,
            game_type="r",
            days_back=30,
        )

        # Then
        assert result is not None
        mlb_api.get_player_stats.assert_called_once_with(
            mlb_player_id=660271,
            stats="season",
            group="hitting",
            season=2025,
            game_type="R",
            days_back=30,
        )
        mock_cache.set.assert_called_once()


class TestIngestPlayersBySourceUseCase:
    @pytest.mark.asyncio
    async def test_requires_team_id_for_team_roster_source(self, mock_cache):
        # Given
        player_repository = AsyncMock()
        team_repository = AsyncMock()
        mlb_api = AsyncMock()
        use_case = IngestPlayersBySourceUseCase(
            player_repository,
            team_repository,
            mlb_api,
            mock_cache,
        )

        # When / Then
        with pytest.raises(ValueError, match="teamId is required"):
            await use_case.execute(source="team_roster")

    @pytest.mark.asyncio
    async def test_ingests_players_from_search_source(self, mock_cache):
        # Given
        player_repository = AsyncMock()
        player_repository.save = AsyncMock(side_effect=lambda player: player)

        team_repository = AsyncMock()
        team = Team.create(
            mlb_id=119,
            name="Los Angeles Dodgers",
            abbreviation="LAD",
            city="Los Angeles",
            division="National League West",
            league="National League",
        )
        team.id = 1
        team_repository.get_by_mlb_id = AsyncMock(return_value=team)

        mlb_api = AsyncMock()
        mlb_api.search_players = AsyncMock(
            return_value=[
                MLBPlayerDTO(
                    id=660271,
                    first_name="Shohei",
                    last_name="Ohtani",
                    position="DH",
                    bats="L",
                    throws="R",
                    birth_date=None,
                    active=True,
                    current_team_id=119,
                )
            ]
        )

        use_case = IngestPlayersBySourceUseCase(
            player_repository,
            team_repository,
            mlb_api,
            mock_cache,
        )

        # When
        result = await use_case.execute(source="search", query="ohtani")

        # Then
        assert len(result) == 1
        assert isinstance(result[0], Player)
        mlb_api.search_players.assert_called_once_with(query="ohtani")
        assert mock_cache.clear.await_count == 2

    @pytest.mark.asyncio
    async def test_filters_sport_players_by_team_id_when_team_filter_is_provided(self, mock_cache):
        # Given
        player_repository = AsyncMock()
        player_repository.save = AsyncMock(side_effect=lambda player: player)

        team_repository = AsyncMock()
        team = Team.create(
            mlb_id=133,
            name="Athletics",
            abbreviation="ATH",
            city="West Sacramento",
            division="American League West",
            league="American League",
        )
        team.id = 3
        team_repository.get_by_mlb_id = AsyncMock(return_value=team)

        mlb_api = AsyncMock()
        mlb_api.get_players_by_sport = AsyncMock(
            return_value=[
                MLBPlayerDTO(
                    id=1,
                    first_name="Pitcher",
                    last_name="One",
                    position="P",
                    bats="R",
                    throws="R",
                    birth_date=None,
                    active=True,
                    current_team_id=133,
                ),
                MLBPlayerDTO(
                    id=2,
                    first_name="Infielder",
                    last_name="Two",
                    position="SS",
                    bats="R",
                    throws="R",
                    birth_date=None,
                    active=True,
                    current_team_id=147,
                ),
            ]
        )

        use_case = IngestPlayersBySourceUseCase(
            player_repository,
            team_repository,
            mlb_api,
            mock_cache,
        )

        # When
        result = await use_case.execute(source="sport_players", sport_id=1, season=2025, team_mlb_id=133)

        # Then
        assert len(result) == 1
        assert result[0].mlb_id == 1
        assert result[0].current_team_id == 3
        mlb_api.get_players_by_sport.assert_called_once_with(sport_id=1, season=2025, team_mlb_id=133)
        team_repository.get_by_mlb_id.assert_called_once_with(133)
        assert player_repository.save.await_count == 1

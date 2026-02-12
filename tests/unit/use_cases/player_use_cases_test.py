from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from src.application.dto.mlb_api_response import MLBPlayerDTO
from src.application.use_cases.player_use_cases import (
    GetPlayerUseCase,
    IngestPlayersUseCase,
    ListPlayersByPositionUseCase,
    ListPlayersByTeamUseCase,
    SearchPlayersUseCase,
)
from src.domain.entities.player import Player
from src.domain.entities.team import Team


@pytest.fixture
def sample_player() -> Player:
    return Player(
        id=42,
        mlb_id=777,
        first_name="Chris",
        last_name="Taylor",
        position="SS",
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


class TestGetPlayerUseCase:
    @pytest.mark.asyncio
    async def test_returns_cached_player(self, sample_player):
        # Given
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=sample_player)
        player_repository = AsyncMock()
        use_case = GetPlayerUseCase(player_repository, cache)

        # When
        result = await use_case.execute(player_id=sample_player.id)

        # Then
        cache.get.assert_called_once_with(f"players:id:{sample_player.id}")
        player_repository.get_by_id.assert_not_called()
        assert result is sample_player

    @pytest.mark.asyncio
    async def test_fetches_from_repository_when_cache_misses(self, sample_player, mock_cache):
        # Given
        player_repository = AsyncMock()
        player_repository.get_by_id = AsyncMock(return_value=sample_player)
        use_case = GetPlayerUseCase(player_repository, mock_cache)

        # When
        result = await use_case.execute(player_id=sample_player.id)

        # Then
        mock_cache.get.assert_called_once_with(f"players:id:{sample_player.id}")
        player_repository.get_by_id.assert_called_once_with(sample_player.id)
        mock_cache.set.assert_called_once_with(f"players:id:{sample_player.id}", sample_player, ttl=3600)
        assert result is sample_player

    @pytest.mark.asyncio
    async def test_returns_none_when_repository_misses(self, mock_cache):
        # Given
        player_repository = AsyncMock()
        player_repository.get_by_id = AsyncMock(return_value=None)
        use_case = GetPlayerUseCase(player_repository, mock_cache)

        # When
        result = await use_case.execute(player_id=999)

        # Then
        assert result is None
        mock_cache.set.assert_not_called()


class TestListPlayersByTeamUseCase:
    @pytest.mark.asyncio
    async def test_uses_cache_when_available(self, sample_player):
        # Given
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=[sample_player])
        player_repository = AsyncMock()
        use_case = ListPlayersByTeamUseCase(player_repository, cache)

        # When
        result = await use_case.execute(team_id=12)

        # Then
        cache.get.assert_called_once_with("players:team:12")
        player_repository.list_by_team.assert_not_called()
        assert result == [sample_player]

    @pytest.mark.asyncio
    async def test_fetches_players_and_populates_cache(self, sample_player, mock_cache):
        # Given
        player_repository = AsyncMock()
        player_repository.list_by_team = AsyncMock(return_value=[sample_player])
        use_case = ListPlayersByTeamUseCase(player_repository, mock_cache)

        # When
        result = await use_case.execute(team_id=7)

        # Then
        mock_cache.get.assert_called_once_with("players:team:7")
        player_repository.list_by_team.assert_called_once_with(7)
        mock_cache.set.assert_called_once_with("players:team:7", [sample_player], ttl=3600)
        assert result == [sample_player]


class TestListPlayersByPositionUseCase:
    @pytest.mark.asyncio
    async def test_returns_cached_players(self, sample_player):
        # Given
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=[sample_player])
        player_repository = AsyncMock()
        use_case = ListPlayersByPositionUseCase(player_repository, cache)

        # When
        result = await use_case.execute(position="RF")

        # Then
        cache.get.assert_called_once_with("players:position:RF")
        player_repository.list_by_position.assert_not_called()
        assert result == [sample_player]

    @pytest.mark.asyncio
    async def test_query_and_cache_players(self, sample_player, mock_cache):
        # Given
        player_repository = AsyncMock()
        player_repository.list_by_position = AsyncMock(return_value=[sample_player])
        use_case = ListPlayersByPositionUseCase(player_repository, mock_cache)

        # When
        result = await use_case.execute(position="SS")

        # Then
        mock_cache.get.assert_called_once_with("players:position:SS")
        player_repository.list_by_position.assert_called_once_with("SS")
        mock_cache.set.assert_called_once_with("players:position:SS", [sample_player], ttl=3600)
        assert result == [sample_player]


class TestSearchPlayersUseCase:
    @pytest.mark.asyncio
    async def test_returns_cached_results(self, sample_player):
        # Given
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=[sample_player])
        player_repository = AsyncMock()
        use_case = SearchPlayersUseCase(player_repository, cache)

        # When
        result = await use_case.execute(name="chris")

        # Then
        cache.get.assert_called_once_with("players:search:chris")
        player_repository.search_by_name.assert_not_called()
        assert result == [sample_player]

    @pytest.mark.asyncio
    async def test_searches_repository_and_sets_cache(self, sample_player, mock_cache):
        # Given
        player_repository = AsyncMock()
        player_repository.search_by_name = AsyncMock(return_value=[sample_player])
        use_case = SearchPlayersUseCase(player_repository, mock_cache)

        # When
        result = await use_case.execute(name="taylor")

        # Then
        mock_cache.get.assert_called_once_with("players:search:taylor")
        player_repository.search_by_name.assert_called_once_with("taylor")
        mock_cache.set.assert_called_once_with("players:search:taylor", [sample_player], ttl=3600)
        assert result == [sample_player]


class TestIngestPlayersUseCase:
    @pytest.mark.asyncio
    async def test_ingests_players_for_each_team(self, sample_player, mock_cache):
        # Given
        player_repository = AsyncMock()
        player_repository.save = AsyncMock(side_effect=lambda player: player)

        teams = [
            Team.create(mlb_id=1, name="A", abbreviation="A", city="CityA", division="DivA", league="LeagueA"),
            Team.create(mlb_id=2, name="B", abbreviation="B", city="CityB", division="DivB", league="LeagueB"),
        ]
        for idx, team in enumerate(teams, start=1):
            team.id = idx

        team_repository = AsyncMock()
        team_repository.list_all = AsyncMock(return_value=teams)

        mlb_api = AsyncMock()
        mlb_api.get_players_by_team = AsyncMock(
            side_effect=lambda mlb_id: [
                MLBPlayerDTO(
                    id=mlb_id * 100,
                    first_name="Player",
                    last_name=str(mlb_id),
                    position="SS",
                    bats="",
                    throws="",
                    birth_date=None,
                    active=True,
                    current_team_id=None,
                )
            ]
        )

        use_case = IngestPlayersUseCase(player_repository, team_repository, mlb_api, mock_cache)

        # When
        ingested_players = await use_case.execute()

        # Then
        team_repository.list_all.assert_called_once()
        mlb_api.get_players_by_team.assert_any_call(1)
        mlb_api.get_players_by_team.assert_any_call(2)
        assert player_repository.save.await_count == len(teams)
        mock_cache.clear.assert_awaited_once_with(pattern="players:*")
        assert all(isinstance(player, Player) for player in ingested_players)

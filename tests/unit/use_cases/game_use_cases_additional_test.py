import asyncio
from datetime import date, datetime
from unittest.mock import AsyncMock

from application.dto.mlb_api_response import MLBGameDTO
from application.use_cases.game_use_cases import (
    GetGameUseCase,
    IngestGamesUseCase,
    ListGamesUseCase,
    ListUpcomingGamesUseCase,
)
from domain.entities.game import Game
from domain.entities.team import Team


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


def _dto(*, game_id: int, home_id: int, away_id: int, game_date: datetime, winning_id: int | None) -> MLBGameDTO:
    return MLBGameDTO(
        id=game_id,
        home_team_id=home_id,
        away_team_id=away_id,
        game_date=game_date,
        status="completed",
        scheduled_innings=9,
        home_score=4,
        away_score=2,
        winning_team_id=winning_id,
    )


def test_list_games_returns_cached_value_without_touching_repository():
    # Given
    cached_games = ["cached"]
    cache = AsyncMock(get=AsyncMock(return_value=cached_games))
    repository = AsyncMock()
    use_case = ListGamesUseCase(repository, cache)

    # When
    result = asyncio.run(use_case.execute(limit=10))

    # Then
    assert result == cached_games
    repository.list_upcoming_games.assert_not_awaited()
    cache.set.assert_not_awaited()


def test_list_games_uses_correct_repository_branch_by_filters():
    # Given
    cache = AsyncMock(get=AsyncMock(return_value=None), set=AsyncMock())
    repository = AsyncMock(
        list_by_date=AsyncMock(return_value=["by-date"]),
        list_by_team=AsyncMock(return_value=["by-team"]),
        list_by_status=AsyncMock(return_value=["by-status"]),
        list_upcoming_games=AsyncMock(return_value=["upcoming"]),
    )
    use_case = ListGamesUseCase(repository, cache)

    # When / Then
    result_by_date = asyncio.run(use_case.execute(game_date=date(2026, 4, 1)))
    result_by_team = asyncio.run(use_case.execute(team_id=7, limit=5))
    result_by_status = asyncio.run(use_case.execute(status="completed", limit=3))
    result_default = asyncio.run(use_case.execute(limit=2))

    assert result_by_date == ["by-date"]
    assert result_by_team == ["by-team"]
    assert result_by_status == ["by-status"]
    assert result_default == ["upcoming"]
    repository.list_by_date.assert_awaited_once_with(date(2026, 4, 1))
    repository.list_by_team.assert_awaited_once_with(7, 5)
    repository.list_by_status.assert_awaited_once_with("completed", 3)
    repository.list_upcoming_games.assert_awaited_once_with(days_ahead=7, limit=2)


def test_get_game_use_case_caches_found_game_only():
    # Given
    game = Game.create(
        mlb_game_id=9001,
        home_team_id=1,
        away_team_id=2,
        game_date=datetime(2026, 4, 2, 18, 0, 0),
        status="scheduled",
    )
    cache = AsyncMock(get=AsyncMock(side_effect=[None, None]), set=AsyncMock())
    repository = AsyncMock(get_by_id=AsyncMock(side_effect=[game, None]))
    use_case = GetGameUseCase(repository, cache)

    # When
    found = asyncio.run(use_case.execute(11))
    missing = asyncio.run(use_case.execute(12))

    # Then
    assert found == game
    assert missing is None
    cache.set.assert_awaited_once()


def test_list_upcoming_games_uses_cache_and_repository_path():
    # Given
    cache = AsyncMock(get=AsyncMock(side_effect=[None, ["cached-upcoming"]]), set=AsyncMock())
    repository = AsyncMock(list_upcoming_games=AsyncMock(return_value=["from-repo"]))
    use_case = ListUpcomingGamesUseCase(repository, cache)

    # When
    first = asyncio.run(use_case.execute(days_ahead=3, limit=4))
    second = asyncio.run(use_case.execute(days_ahead=3, limit=4))

    # Then
    assert first == ["from-repo"]
    assert second == ["cached-upcoming"]
    repository.list_upcoming_games.assert_awaited_once_with(3, 4)


def test_process_games_data_skips_unknown_or_incomplete_teams_and_maps_winner():
    # Given
    game_repository = AsyncMock(save=AsyncMock(side_effect=lambda game: game))
    team_repository = AsyncMock()
    mlb_api = AsyncMock()
    cache = AsyncMock()
    use_case = IngestGamesUseCase(game_repository, team_repository, mlb_api, cache)

    home_team = _team(team_id=1, mlb_id=119)
    away_team = _team(team_id=2, mlb_id=121)
    team_without_id = _team(team_id=None, mlb_id=140)

    teams_by_mlb_id = {119: home_team, 121: away_team, 140: team_without_id}
    team_repository.get_by_mlb_id.side_effect = lambda mlb_id: teams_by_mlb_id.get(mlb_id)

    games = [
        _dto(game_id=1, home_id=119, away_id=121, game_date=datetime(2026, 4, 1, 18, 0), winning_id=121),
        _dto(game_id=2, home_id=999, away_id=121, game_date=datetime(2026, 4, 1, 18, 0), winning_id=None),
        _dto(game_id=3, home_id=140, away_id=121, game_date=datetime(2026, 4, 1, 18, 0), winning_id=140),
        _dto(game_id=4, home_id=119, away_id=121, game_date=None, winning_id=None),
    ]

    # When
    processed = asyncio.run(use_case._process_games_data(games))

    # Then
    assert len(processed) == 1
    assert processed[0].mlb_game_id == 1
    assert processed[0].winning_team_id == 2


def test_ingest_games_execute_with_specific_date_and_with_days_back_clears_cache():
    # Given
    game_repository = AsyncMock(save=AsyncMock(side_effect=lambda game: game))
    team_repository = AsyncMock()
    mlb_api = AsyncMock()
    cache = AsyncMock(clear=AsyncMock())
    use_case = IngestGamesUseCase(game_repository, team_repository, mlb_api, cache)

    team_repository.get_by_mlb_id.side_effect = lambda mlb_id: {
        119: _team(team_id=1, mlb_id=119),
        121: _team(team_id=2, mlb_id=121),
    }.get(mlb_id)
    mlb_api.get_games_by_date.return_value = [
        _dto(game_id=100, home_id=119, away_id=121, game_date=datetime(2026, 4, 10, 18, 0), winning_id=119)
    ]

    # When
    by_date = asyncio.run(use_case.execute(game_date=date(2026, 4, 10)))
    by_days = asyncio.run(use_case.execute(game_date=None, days_back=2))

    # Then
    assert len(by_date) == 1
    assert len(by_days) == 2
    assert cache.clear.await_count == 2

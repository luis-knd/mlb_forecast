import json
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.status import HTTP_200_OK, HTTP_201_CREATED

from domain.entities.game import Game
from domain.entities.team import Team
from interface.rest.exception_handlers import DomainExceptions
from interface.rest.game_routes import get_game, get_game_use_cases, ingest_games, list_games


def _build_team(team_id: int, mlb_id: int, name: str, city: str) -> Team:
    return Team(
        id=team_id,
        mlb_id=mlb_id,
        name=name,
        abbreviation=name[:3].upper(),
        city=city,
        division="National League West",
        league="National League",
        venue_name=f"{name} Park",
        created_at=datetime(2026, 3, 18, 10, 0, 0),
        updated_at=datetime(2026, 3, 18, 10, 5, 0),
    )


def _build_game(home_team: Team, away_team: Team, winning_team: Team | None = None) -> Game:
    return Game(
        id=21,
        mlb_game_id=831526,
        home_team_id=home_team.id or 0,
        away_team_id=away_team.id or 0,
        game_date=datetime(2026, 3, 18, 18, 5, 0),
        status="completed",
        scheduled_innings=9,
        home_score=6,
        away_score=4,
        winning_team_id=winning_team.id if winning_team else None,
        created_at=datetime(2026, 3, 18, 8, 0, 0),
        updated_at=datetime(2026, 3, 18, 22, 0, 0),
        home_team=home_team,
        away_team=away_team,
        winning_team=winning_team,
    )


def _response_body(response) -> dict:
    return json.loads(response.body)


def _use_case(*, result=None, side_effect=None):
    use_case = MagicMock()
    use_case.execute = AsyncMock(side_effect=side_effect) if side_effect is not None else AsyncMock(return_value=result)
    return use_case


def test_get_game_use_cases_builds_all_required_dependencies():
    # Given
    db = MagicMock()
    cache = AsyncMock()

    # When
    use_cases = get_game_use_cases(db=db, cache=cache)

    # Then
    assert set(use_cases.keys()) == {"list_games", "get_game", "ingest_games", "list_upcoming_games"}


class TestListGamesRoute:
    @pytest.mark.asyncio
    async def test_returns_default_shape_when_include_is_missing(self):
        # Given
        home_team = _build_team(11, 119, "Los Angeles Dodgers", "Los Angeles")
        away_team = _build_team(12, 121, "New York Mets", "New York")
        game = _build_game(home_team=home_team, away_team=away_team, winning_team=home_team)
        list_games_use_case = _use_case(result=[game])

        # When
        response = await list_games(
            date=None,
            team_id=None,
            status=None,
            limit=50,
            include=None,
            use_cases={"list_games": list_games_use_case},
        )

        # Then
        body = _response_body(response)
        assert response.status_code == HTTP_200_OK
        assert body["data"][0]["mlb_game_id"] == 831526
        assert "home_team" not in body["data"][0]
        list_games_use_case.execute.assert_awaited_once_with(
            game_date=None,
            team_id=None,
            status=None,
            limit=50,
        )

    @pytest.mark.asyncio
    async def test_hydrates_requested_relations(self):
        # Given
        home_team = _build_team(11, 119, "Los Angeles Dodgers", "Los Angeles")
        away_team = _build_team(12, 121, "New York Mets", "New York")
        game = _build_game(home_team=home_team, away_team=away_team, winning_team=home_team)
        list_games_use_case = _use_case(result=[game])

        # When
        response = await list_games(
            date=None,
            team_id=None,
            status=None,
            limit=50,
            include=["home_team.venue_name", "away_team", "winning_team"],
            use_cases={"list_games": list_games_use_case},
        )

        # Then
        body = _response_body(response)
        assert body["data"][0]["home_team"]["venue_name"] == "Los Angeles Dodgers Park"
        assert body["data"][0]["away_team"]["city"] == "New York"
        assert body["data"][0]["winning_team"]["mlb_id"] == 119

    @pytest.mark.asyncio
    async def test_rejects_invalid_date_format(self):
        # Given / When / Then
        with pytest.raises(DomainExceptions.InvalidDataError, match="Date must be in YYYY-MM-DD format"):
            await list_games(
                date="2026/03/18",
                team_id=None,
                status=None,
                limit=50,
                include=None,
                use_cases={"list_games": _use_case(result=[])},
            )

    @pytest.mark.asyncio
    async def test_rejects_invalid_status(self):
        # Given / When / Then
        with pytest.raises(DomainExceptions.InvalidDataError, match="Status must be one of"):
            await list_games(
                date=None,
                team_id=None,
                status="draft",
                limit=50,
                include=None,
                use_cases={"list_games": _use_case(result=[])},
            )

    @pytest.mark.asyncio
    async def test_rejects_non_positive_team_id(self):
        # Given / When / Then
        with pytest.raises(DomainExceptions.InvalidDataError, match="Team ID must be a positive integer"):
            await list_games(
                date=None,
                team_id=0,
                status=None,
                limit=50,
                include=None,
                use_cases={"list_games": _use_case(result=[])},
            )

    @pytest.mark.asyncio
    async def test_rejects_unknown_include_path(self):
        # Given / When / Then
        with pytest.raises(DomainExceptions.InvalidDataError, match="Invalid include path 'boxscore'"):
            await list_games(
                date=None,
                team_id=None,
                status=None,
                limit=50,
                include=["boxscore"],
                use_cases={"list_games": _use_case(result=[])},
            )

    @pytest.mark.asyncio
    async def test_passes_parsed_date_to_use_case(self):
        # Given
        list_games_use_case = _use_case(result=[])

        # When
        await list_games(
            date="2026-03-18",
            team_id=None,
            status=None,
            limit=50,
            include=None,
            use_cases={"list_games": list_games_use_case},
        )

        # Then
        list_games_use_case.execute.assert_awaited_once_with(
            game_date=date(2026, 3, 18),
            team_id=None,
            status=None,
            limit=50,
        )


class TestGetGameRoute:
    @pytest.mark.asyncio
    async def test_hydrates_requested_relations(self):
        # Given
        home_team = _build_team(11, 119, "Los Angeles Dodgers", "Los Angeles")
        away_team = _build_team(12, 121, "New York Mets", "New York")
        game = _build_game(home_team=home_team, away_team=away_team, winning_team=home_team)
        get_game_use_case = _use_case(result=game)

        # When
        response = await get_game(
            game_id=21,
            include=["winning_team.name", "home_team"],
            use_cases={"get_game": get_game_use_case},
        )

        # Then
        body = _response_body(response)
        assert body["data"]["home_team"]["name"] == "Los Angeles Dodgers"
        assert body["data"]["winning_team"]["name"] == "Los Angeles Dodgers"

    @pytest.mark.asyncio
    async def test_rejects_non_positive_game_id(self):
        # Given / When / Then
        with pytest.raises(DomainExceptions.InvalidDataError, match="Game ID must be a positive integer"):
            await get_game(game_id=0, include=None, use_cases={"get_game": _use_case(result=None)})

    @pytest.mark.asyncio
    async def test_raises_not_found_when_game_does_not_exist(self):
        # Given
        get_game_use_case = _use_case(result=None)

        # When / Then
        with pytest.raises(DomainExceptions.GameNotFoundError):
            await get_game(game_id=21, include=None, use_cases={"get_game": get_game_use_case})


class TestIngestGamesRoute:
    @pytest.mark.asyncio
    async def test_returns_created_response_for_days_back_ingestion(self):
        # Given
        home_team = _build_team(11, 119, "Los Angeles Dodgers", "Los Angeles")
        away_team = _build_team(12, 121, "New York Mets", "New York")
        ingest_games_use_case = _use_case(result=[_build_game(home_team=home_team, away_team=away_team)])

        # When
        response = await ingest_games(date=None, days_back=3, use_cases={"ingest_games": ingest_games_use_case})

        # Then
        body = _response_body(response)
        assert response.status_code == HTTP_201_CREATED
        assert body["data"]["ingestion_summary"]["operation"] == "game_ingestion"
        assert body["data"]["sample_games"][0]["mlb_game_id"] == 831526
        ingest_games_use_case.execute.assert_awaited_once_with(days_back=3)

    @pytest.mark.asyncio
    async def test_routes_specific_date_ingestion_to_use_case(self):
        # Given
        ingest_games_use_case = _use_case(result=[])

        # When
        await ingest_games(date="2026-03-18", days_back=7, use_cases={"ingest_games": ingest_games_use_case})

        # Then
        ingest_games_use_case.execute.assert_awaited_once_with(game_date=date(2026, 3, 18))

    @pytest.mark.asyncio
    async def test_rejects_invalid_date_format(self):
        # Given / When / Then
        with pytest.raises(DomainExceptions.InvalidDataError, match="Date must be in YYYY-MM-DD format"):
            await ingest_games(date="18-03-2026", days_back=7, use_cases={"ingest_games": _use_case(result=[])})

    @pytest.mark.asyncio
    async def test_rejects_days_back_out_of_range(self):
        # Given / When / Then
        with pytest.raises(DomainExceptions.InvalidDataError, match="Days back must be between 1 and 30"):
            await ingest_games(date=None, days_back=0, use_cases={"ingest_games": _use_case(result=[])})

    @pytest.mark.asyncio
    async def test_translates_mlb_api_failures(self):
        # Given
        ingest_games_use_case = _use_case(side_effect=RuntimeError("MLB API timeout"))

        # When / Then
        with pytest.raises(DomainExceptions.ExternalServiceError):
            await ingest_games(date=None, days_back=3, use_cases={"ingest_games": ingest_games_use_case})

    @pytest.mark.asyncio
    async def test_re_raises_unexpected_failures(self):
        # Given
        ingest_games_use_case = _use_case(side_effect=RuntimeError("unexpected failure"))

        # When / Then
        with pytest.raises(RuntimeError, match="unexpected failure"):
            await ingest_games(date=None, days_back=3, use_cases={"ingest_games": ingest_games_use_case})

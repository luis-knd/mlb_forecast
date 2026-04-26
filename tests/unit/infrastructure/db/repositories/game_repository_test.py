from datetime import datetime, timedelta

import pytest

from domain.entities.game import Game
from infrastructure.db.models import GameModel, TeamModel
from infrastructure.db.repositories.game_repository import GameRepository


@pytest.fixture
def game_repository(db_session):
    return GameRepository(db_session)


@pytest.fixture
def seeded_teams(db_session):
    # Given
    home = TeamModel(
        mlb_id=110,
        name="Home Team",
        abbreviation="HOM",
        city="Home City",
        division="East",
        league="AL",
        venue_name="Home Park",
    )
    away = TeamModel(
        mlb_id=120,
        name="Away Team",
        abbreviation="AWY",
        city="Away City",
        division="West",
        league="NL",
        venue_name="Away Park",
    )
    third = TeamModel(
        mlb_id=130,
        name="Third Team",
        abbreviation="THD",
        city="Third City",
        division="Central",
        league="AL",
        venue_name="Third Park",
    )
    db_session.add_all([home, away, third])
    db_session.commit()
    return home, away, third


@pytest.mark.asyncio
async def test_save_creates_and_gets_by_id(game_repository, seeded_teams):
    # Given
    home, away, _ = seeded_teams
    new_game = Game.create(
        mlb_game_id=5001,
        home_team_id=home.id,
        away_team_id=away.id,
        game_date=datetime(2026, 4, 20, 19, 10),
        status="scheduled",
    )

    # When
    saved = await game_repository.save(new_game)
    loaded = await game_repository.get_by_id(saved.id)

    # Then
    assert saved.id is not None
    assert loaded is not None
    assert loaded.mlb_game_id == 5001
    assert loaded.home_team is not None
    assert loaded.away_team is not None


@pytest.mark.asyncio
async def test_save_updates_existing_by_mlb_id_without_overwriting_scores_with_none(game_repository, seeded_teams):
    # Given
    home, away, _ = seeded_teams
    original = await game_repository.save(
        Game.create(
            mlb_game_id=5002,
            home_team_id=home.id,
            away_team_id=away.id,
            game_date=datetime(2026, 4, 21, 19, 10),
            status="completed",
            home_score=4,
            away_score=2,
            winning_team_id=home.id,
        )
    )

    # When
    updated = await game_repository.save(
        Game(
            id=None,
            mlb_game_id=5002,
            home_team_id=home.id,
            away_team_id=away.id,
            game_date=datetime(2026, 4, 22, 19, 10),
            status="scheduled",
            home_score=None,
            away_score=None,
            winning_team_id=None,
        )
    )

    # Then
    assert updated is not None
    assert updated.id == original.id
    assert updated.game_date == datetime(2026, 4, 22, 19, 10)
    assert updated.home_score == 4
    assert updated.away_score == 2
    assert updated.winning_team_id == home.id


@pytest.mark.asyncio
async def test_save_raises_runtime_error_and_rolls_back_when_required_fields_are_missing(game_repository):
    # Given
    invalid_game = Game(
        id=None,
        mlb_game_id=0,
        home_team_id=0,
        away_team_id=0,
        game_date=datetime(2026, 4, 20, 19, 10),
        status="scheduled",
    )

    # When / Then
    with pytest.raises(RuntimeError, match="Failed to save game"):
        await game_repository.save(invalid_game)


@pytest.mark.asyncio
async def test_list_methods_and_result_update(game_repository, db_session, seeded_teams):
    # Given
    home, away, third = seeded_teams
    today = datetime.now().date()
    games = [
        GameModel(
            mlb_game_id=6001,
            home_team_id=home.id,
            away_team_id=away.id,
            game_date=datetime.combine(today, datetime.min.time()) + timedelta(hours=3),
            status="scheduled",
        ),
        GameModel(
            mlb_game_id=6002,
            home_team_id=away.id,
            away_team_id=home.id,
            game_date=datetime.combine(today, datetime.min.time()) + timedelta(hours=5),
            status="in_progress",
        ),
        GameModel(
            mlb_game_id=6003,
            home_team_id=home.id,
            away_team_id=third.id,
            game_date=datetime.combine(today - timedelta(days=2), datetime.min.time()),
            status="completed",
            home_score=3,
            away_score=1,
            winning_team_id=home.id,
        ),
    ]
    db_session.add_all(games)
    db_session.commit()

    # When
    by_date = await game_repository.list_by_date(today)
    by_team = await game_repository.list_by_team(home.id, limit=10)
    by_status = await game_repository.list_by_status("completed", limit=10)
    upcoming = await game_repository.list_upcoming_games(days_ahead=3, limit=10)
    matchups = await game_repository.list_historical_matchups(home.id, third.id, limit=10)
    updated = await game_repository.update_game_result(games[1].id, 8, 5)

    # Then
    assert len(by_date) == 2
    assert len(by_team) == 3
    assert len(by_status) == 1
    assert len(upcoming) == 2
    assert len(matchups) == 1
    assert updated is not None
    assert updated.winning_team_id == away.id


@pytest.mark.asyncio
async def test_update_for_tie_and_delete_paths(game_repository, db_session, seeded_teams):
    # Given
    home, away, _ = seeded_teams
    game = GameModel(
        mlb_game_id=7001,
        home_team_id=home.id,
        away_team_id=away.id,
        game_date=datetime(2026, 4, 25, 20, 0),
        status="scheduled",
    )
    db_session.add(game)
    db_session.commit()

    # When
    tie_result = await game_repository.update_game_result(game.id, 2, 2)
    deleted = await game_repository.delete(game.id)
    deleted_missing = await game_repository.delete(999999)

    # Then
    assert tie_result is not None
    assert tie_result.winning_team_id is None
    assert deleted is True
    assert deleted_missing is False


@pytest.mark.asyncio
async def test_get_by_mlb_id_and_get_by_id_return_none_for_missing(game_repository):
    # Given / When
    by_id = await game_repository.get_by_id(123456)
    by_mlb = await game_repository.get_by_mlb_id(654321)

    # Then
    assert by_id is None
    assert by_mlb is None


def test_update_game_model_updates_timestamp_and_preserves_none_scores():
    # Given
    model = GameModel(
        mlb_game_id=8001,
        home_team_id=1,
        away_team_id=2,
        game_date=datetime(2026, 4, 20, 10, 0),
        status="scheduled",
        home_score=5,
        away_score=4,
        winning_team_id=1,
    )
    entity = Game(
        id=1,
        mlb_game_id=8001,
        home_team_id=1,
        away_team_id=2,
        game_date=datetime(2026, 4, 22, 11, 0),
        status="in_progress",
        home_score=None,
        away_score=None,
        winning_team_id=None,
    )

    # When
    GameRepository._update_game_model(model, entity)

    # Then
    assert model.game_date == datetime(2026, 4, 22, 11, 0)
    assert model.home_score == 5
    assert model.away_score == 4
    assert model.updated_at is not None

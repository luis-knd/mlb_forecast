from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from infrastructure.db.repositories.entity_mapping_helpers import (
    delete_model_by_id,
    game_model_to_entity,
    team_model_to_entity,
)


def _build_team_model(team_id: int, mlb_id: int, name: str) -> SimpleNamespace:
    now = datetime(2026, 1, 1, 10, 0, 0)
    return SimpleNamespace(
        id=team_id,
        mlb_id=mlb_id,
        name=name,
        abbreviation=name[:3].upper(),
        city="City",
        division="Division",
        league="League",
        venue_name="Venue",
        created_at=now,
        updated_at=now,
    )


def test_team_model_to_entity_returns_none_for_missing_model():
    # Given / When
    result = team_model_to_entity(None)

    # Then
    assert result is None


def test_game_model_to_entity_maps_nested_teams():
    # Given
    home_team = _build_team_model(1, 101, "Home")
    away_team = _build_team_model(2, 202, "Away")
    winning_team = _build_team_model(1, 101, "Home")
    now = datetime(2026, 4, 1, 19, 0, 0)
    game_model = SimpleNamespace(
        id=77,
        mlb_game_id=700077,
        home_team_id=1,
        away_team_id=2,
        game_date=now,
        scheduled_innings=9,
        status="completed",
        home_score=6,
        away_score=2,
        winning_team_id=1,
        created_at=now,
        updated_at=now,
        home_team=home_team,
        away_team=away_team,
        winning_team=winning_team,
    )

    # When
    entity = game_model_to_entity(game_model)

    # Then
    assert entity.id == 77
    assert entity.home_team is not None
    assert entity.home_team.name == "Home"
    assert entity.away_team is not None
    assert entity.away_team.name == "Away"
    assert entity.winning_team is not None
    assert entity.winning_team.id == 1


def test_delete_model_by_id_returns_false_when_entity_does_not_exist():
    # Given
    session = MagicMock()
    query = session.query.return_value
    query.filter.return_value.first.return_value = None

    # When
    result = delete_model_by_id(session, SimpleNamespace(id=1), 1)

    # Then
    assert result is False
    session.delete.assert_not_called()
    session.commit.assert_not_called()


def test_delete_model_by_id_deletes_and_commits_when_entity_exists():
    # Given
    model_class = SimpleNamespace(id=123)
    entity_model = SimpleNamespace(id=123)
    session = MagicMock()
    query = session.query.return_value
    query.filter.return_value.first.return_value = entity_model

    # When
    result = delete_model_by_id(session, model_class, 123)

    # Then
    assert result is True
    session.delete.assert_called_once_with(entity_model)
    session.commit.assert_called_once_with()

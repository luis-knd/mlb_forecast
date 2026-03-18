from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from domain.entities.game import Game
from domain.entities.team import Team


def team_model_to_entity(model: Any | None) -> Team | None:
    if model is None:
        return None

    return Team(
        id=model.id,
        mlb_id=model.mlb_id,
        name=model.name,
        abbreviation=model.abbreviation,
        city=model.city,
        division=model.division,
        league=model.league,
        venue_name=model.venue_name,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def game_model_to_entity(model: Any) -> Game:
    game = Game(
        id=model.id,
        mlb_game_id=model.mlb_game_id,
        home_team_id=model.home_team_id,
        away_team_id=model.away_team_id,
        game_date=model.game_date,
        scheduled_innings=model.scheduled_innings,
        status=model.status,
        home_score=model.home_score,
        away_score=model.away_score,
        winning_team_id=model.winning_team_id,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )

    home_team = team_model_to_entity(getattr(model, "home_team", None))
    away_team = team_model_to_entity(getattr(model, "away_team", None))
    winning_team = team_model_to_entity(getattr(model, "winning_team", None))

    if home_team is not None:
        game.home_team = home_team
    if away_team is not None:
        game.away_team = away_team
    if winning_team is not None:
        game.winning_team = winning_team

    return game


def delete_model_by_id(session: Session, model_class: Any, entity_id: int) -> bool:
    entity_model = session.query(model_class).filter(model_class.id == entity_id).first()
    if not entity_model:
        return False

    session.delete(entity_model)
    session.commit()
    return True

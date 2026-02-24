"""
Game repository implementation.
This module implements the GameRepositoryPort interface using SQLAlchemy.
"""

from datetime import date, datetime, timedelta
from typing import List, Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload

from src.application.ports.game_repository import GameRepositoryPort
from src.domain.entities.game import Game
from src.infrastructure.db.models import GameModel
from src.infrastructure.db.repositories.entity_mapping_helpers import game_model_to_entity


class GameRepository(GameRepositoryPort):
    """Implementation of the GameRepositoryPort interface using SQLAlchemy."""

    def __init__(self, session: Session):
        self.session = session

    async def get_by_id(self, game_id: int) -> Optional[Game]:
        """Get a game by its ID."""
        game_model = (
            self.session.query(GameModel)
            .options(
                joinedload(GameModel.home_team),
                joinedload(GameModel.away_team),
                joinedload(GameModel.winning_team),
            )
            .filter(GameModel.id == game_id)
            .first()
        )
        if not game_model:
            return None
        return self._model_to_entity(game_model)

    async def get_by_mlb_id(self, mlb_game_id: int) -> Optional[Game]:
        """Get a game by its MLB ID."""
        game_model = (
            self.session.query(GameModel)
            .options(
                joinedload(GameModel.home_team),
                joinedload(GameModel.away_team),
                joinedload(GameModel.winning_team),
            )
            .filter(GameModel.mlb_game_id == mlb_game_id)
            .first()
        )
        if not game_model:
            return None
        return self._model_to_entity(game_model)

    async def list_by_date(self, game_date: date) -> List[Game]:
        """List games by date."""
        # Convert date to datetime range for the entire day
        start_date = datetime.combine(game_date, datetime.min.time())
        end_date = datetime.combine(game_date, datetime.max.time())

        game_models = (
            self.session.query(GameModel)
            .options(
                joinedload(GameModel.home_team),
                joinedload(GameModel.away_team),
                joinedload(GameModel.winning_team),
            )
            .filter(GameModel.game_date.between(start_date, end_date))
            .all()
        )
        return [self._model_to_entity(game_model) for game_model in game_models]

    async def list_by_team(self, team_id: int, limit: int = 50) -> List[Game]:
        """List games by team."""
        game_models = (
            self.session.query(GameModel)
            .options(
                joinedload(GameModel.home_team),
                joinedload(GameModel.away_team),
                joinedload(GameModel.winning_team),
            )
            .filter(or_(GameModel.home_team_id == team_id, GameModel.away_team_id == team_id))
            .order_by(GameModel.game_date.desc())
            .limit(limit)
            .all()
        )
        return [self._model_to_entity(game_model) for game_model in game_models]

    async def list_by_status(self, status: str, limit: int = 50) -> List[Game]:
        """List games by status."""
        game_models = (
            self.session.query(GameModel)
            .options(
                joinedload(GameModel.home_team),
                joinedload(GameModel.away_team),
                joinedload(GameModel.winning_team),
            )
            .filter(GameModel.status == status)
            .order_by(GameModel.game_date.desc())
            .limit(limit)
            .all()
        )
        return [self._model_to_entity(game_model) for game_model in game_models]

    async def list_upcoming_games(self, days_ahead: int = 7, limit: int = 50) -> List[Game]:
        """List upcoming games."""
        today = datetime.now().date()
        end_date = today + timedelta(days=days_ahead)

        game_models = (
            self.session.query(GameModel)
            .options(
                joinedload(GameModel.home_team),
                joinedload(GameModel.away_team),
                joinedload(GameModel.winning_team),
            )
            .filter(
                and_(
                    GameModel.game_date >= datetime.combine(today, datetime.min.time()),
                    GameModel.game_date <= datetime.combine(end_date, datetime.max.time()),
                    GameModel.status.in_(["scheduled", "in_progress"]),
                )
            )
            .order_by(GameModel.game_date.asc())
            .limit(limit)
            .all()
        )
        return [self._model_to_entity(game_model) for game_model in game_models]

    async def list_historical_matchups(self, home_team_id: int, away_team_id: int, limit: int = 10) -> List[Game]:
        """List historical matchups between two teams."""
        game_models = (
            self.session.query(GameModel)
            .options(
                joinedload(GameModel.home_team),
                joinedload(GameModel.away_team),
                joinedload(GameModel.winning_team),
            )
            .filter(
                and_(
                    or_(
                        and_(
                            GameModel.home_team_id == home_team_id,
                            GameModel.away_team_id == away_team_id,
                        ),
                        and_(
                            GameModel.home_team_id == away_team_id,
                            GameModel.away_team_id == home_team_id,
                        ),
                    ),
                    GameModel.status == "completed",
                )
            )
            .order_by(GameModel.game_date.desc())
            .limit(limit)
            .all()
        )
        return [self._model_to_entity(game_model) for game_model in game_models]

    async def save(self, game: Game) -> Game:
        """Save a game (create or update)."""
        try:
            # Validate required fields before saving
            if not game.mlb_game_id or not game.home_team_id or not game.away_team_id:
                raise ValueError("Missing required game fields")

            # Check if game already exists by ID
            if game.id:
                game_model = self.session.query(GameModel).filter(GameModel.id == game.id).first()
                if game_model:
                    self._update_game_model(game_model, game)
                    self.session.commit()
                    self.session.refresh(game_model)
                    return await self.get_by_id(game_model.id)

            # Check if game exists by MLB ID
            game_model = self.session.query(GameModel).filter(GameModel.mlb_game_id == game.mlb_game_id).first()
            if game_model:
                self._update_game_model(game_model, game)
                self.session.commit()
                self.session.refresh(game_model)
                return await self.get_by_id(game_model.id)

            # Create new game
            game_model = GameModel(
                mlb_game_id=game.mlb_game_id,
                home_team_id=game.home_team_id,
                away_team_id=game.away_team_id,
                game_date=game.game_date,
                scheduled_innings=game.scheduled_innings,
                status=game.status,
                home_score=game.home_score,
                away_score=game.away_score,
                winning_team_id=game.winning_team_id,
            )
            self.session.add(game_model)
            self.session.commit()
            self.session.refresh(game_model)
            return await self.get_by_id(game_model.id)
        except Exception as e:
            self.session.rollback()
            raise RuntimeError(f"Failed to save game with MLB ID {game.mlb_game_id}: {str(e)}") from e

    async def update_game_result(
        self, game_id: int, home_score: int, away_score: int, status: str = "completed"
    ) -> Optional[Game]:
        """Update a game's result."""
        game_model = self.session.query(GameModel).filter(GameModel.id == game_id).first()
        if not game_model:
            return None

        game_model.home_score = home_score
        game_model.away_score = away_score
        game_model.status = status

        # Set winning team
        if home_score > away_score:
            game_model.winning_team_id = game_model.home_team_id
        elif away_score > home_score:
            game_model.winning_team_id = game_model.away_team_id
        else:
            game_model.winning_team_id = None  # Tie

        self.session.commit()
        return await self.get_by_id(game_id)

    async def delete(self, game_id: int) -> bool:
        """Delete a game by its ID."""
        game_model = self.session.query(GameModel).filter(GameModel.id == game_id).first()
        if not game_model:
            return False
        self.session.delete(game_model)
        self.session.commit()
        return True

    def _update_game_model(self, model: GameModel, entity: Game) -> None:
        """Update a GameModel with values from a Game entity."""
        model.mlb_game_id = entity.mlb_game_id
        model.home_team_id = entity.home_team_id
        model.away_team_id = entity.away_team_id
        model.game_date = entity.game_date
        model.scheduled_innings = entity.scheduled_innings
        model.status = entity.status

        # Preserve existing scores if new values are None (important for rescheduled games)
        if entity.home_score is not None:
            model.home_score = entity.home_score
        if entity.away_score is not None:
            model.away_score = entity.away_score
        if entity.winning_team_id is not None:
            model.winning_team_id = entity.winning_team_id

        model.updated_at = datetime.now()  # Explicitly update timestamp

    def _model_to_entity(self, model: GameModel) -> Game:
        """Convert a GameModel to a Game entity."""
        return game_model_to_entity(model)

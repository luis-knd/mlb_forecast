"""
Prediction repository implementation.
This module implements the PredictionRepositoryPort interface using SQLAlchemy.
"""

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from src.application.ports.prediction_repository import PredictionRepositoryPort
from src.domain.entities.game import Game
from src.domain.entities.prediction import Prediction
from src.infrastructure.db.models import GameModel, PredictionModel
from src.infrastructure.db.repositories.entity_mapping_helpers import game_model_to_entity


class PredictionRepository(PredictionRepositoryPort):
    """Implementation of the PredictionRepositoryPort interface using SQLAlchemy."""

    def __init__(self, session: Session):
        self.session = session

    async def get_by_id(self, prediction_id: int) -> Prediction | None:
        """Get a prediction by its ID."""
        prediction_model = (
            self.session.query(PredictionModel)
            .options(
                joinedload(PredictionModel.game).joinedload(GameModel.home_team),
                joinedload(PredictionModel.game).joinedload(GameModel.away_team),
            )
            .filter(PredictionModel.id == prediction_id)
            .first()
        )
        if not prediction_model:
            return None
        return self._model_to_entity(prediction_model)

    async def list_by_game(self, game_id: int) -> list[Prediction]:
        """List predictions for a specific game."""
        prediction_models = (
            self.session.query(PredictionModel)
            .options(
                joinedload(PredictionModel.game).joinedload(GameModel.home_team),
                joinedload(PredictionModel.game).joinedload(GameModel.away_team),
            )
            .filter(PredictionModel.game_id == game_id)
            .order_by(PredictionModel.created_at.desc())
            .all()
        )
        return [self._model_to_entity(model) for model in prediction_models]

    async def list_by_game_and_type(self, game_id: int, prediction_type: str) -> list[Prediction]:
        """List predictions for a specific game and type."""
        prediction_models = (
            self.session.query(PredictionModel)
            .options(
                joinedload(PredictionModel.game).joinedload(GameModel.home_team),
                joinedload(PredictionModel.game).joinedload(GameModel.away_team),
            )
            .filter(
                PredictionModel.game_id == game_id,
                PredictionModel.prediction_type == prediction_type,
            )
            .order_by(PredictionModel.created_at.desc())
            .all()
        )
        return [self._model_to_entity(model) for model in prediction_models]

    async def list_latest_predictions(self, limit: int = 50) -> list[Prediction]:
        """List the latest predictions."""
        prediction_models = (
            self.session.query(PredictionModel)
            .options(
                joinedload(PredictionModel.game).joinedload(GameModel.home_team),
                joinedload(PredictionModel.game).joinedload(GameModel.away_team),
            )
            .order_by(PredictionModel.created_at.desc())
            .limit(limit)
            .all()
        )
        return [self._model_to_entity(model) for model in prediction_models]

    async def list_by_model_version(self, model_version: str, limit: int = 50) -> list[Prediction]:
        """List predictions by model version."""
        prediction_models = (
            self.session.query(PredictionModel)
            .options(
                joinedload(PredictionModel.game).joinedload(GameModel.home_team),
                joinedload(PredictionModel.game).joinedload(GameModel.away_team),
            )
            .filter(PredictionModel.model_version == model_version)
            .order_by(PredictionModel.created_at.desc())
            .limit(limit)
            .all()
        )
        return [self._model_to_entity(model) for model in prediction_models]

    async def save(self, prediction: Prediction) -> Prediction:
        """Save a prediction (create or update)."""
        # Check if prediction already exists
        if prediction.id:
            prediction_model = self.session.query(PredictionModel).filter(PredictionModel.id == prediction.id).first()
            if prediction_model:
                # Update existing prediction
                self._update_prediction_model(prediction_model, prediction)
                self.session.commit()
                return await self.get_by_id(prediction_model.id)

        # Create new prediction
        prediction_model = PredictionModel(
            game_id=prediction.game_id,
            prediction_type=prediction.prediction_type,
            home_win_probability=prediction.home_win_probability,
            away_win_probability=prediction.away_win_probability,
            over_under_runs=prediction.over_under_runs,
            total_runs_prediction=prediction.total_runs_prediction,
            detailed_predictions=prediction.detailed_predictions,
            model_version=prediction.model_version,
            confidence_score=prediction.confidence_score,
            feature_importance=prediction.feature_importance,
            actual_result=prediction.actual_result,
            prediction_accuracy=prediction.prediction_accuracy,
        )
        self.session.add(prediction_model)
        self.session.commit()
        self.session.refresh(prediction_model)
        return await self.get_by_id(prediction_model.id)

    async def update_with_actual_result(
        self, prediction_id: int, actual_result: dict[str, Any], accuracy: float
    ) -> Prediction | None:
        """Update a prediction with the actual result and accuracy."""
        prediction_model = self.session.query(PredictionModel).filter(PredictionModel.id == prediction_id).first()
        if not prediction_model:
            return None

        prediction_model.actual_result = actual_result
        prediction_model.prediction_accuracy = accuracy

        self.session.commit()
        return await self.get_by_id(prediction_id)

    async def delete(self, prediction_id: int) -> bool:
        """Delete a prediction by its ID."""
        prediction_model = self.session.query(PredictionModel).filter(PredictionModel.id == prediction_id).first()
        if not prediction_model:
            return False
        self.session.delete(prediction_model)
        self.session.commit()
        return True

    async def get_prediction_accuracy_by_model(self, model_version: str) -> float:
        """Get the average prediction accuracy for a specific model version."""
        result = (
            self.session.query(func.avg(PredictionModel.prediction_accuracy))
            .filter(
                PredictionModel.model_version == model_version,
                PredictionModel.prediction_accuracy.isnot(None),
            )
            .scalar()
        )
        return float(result) if result is not None else 0.0

    @staticmethod
    def _update_prediction_model(model: PredictionModel, entity: Prediction) -> None:
        """Update a PredictionModel with values from a Prediction entity."""
        model.game_id = entity.game_id
        model.prediction_type = entity.prediction_type
        model.home_win_probability = entity.home_win_probability
        model.away_win_probability = entity.away_win_probability
        model.over_under_runs = entity.over_under_runs
        model.total_runs_prediction = entity.total_runs_prediction
        model.detailed_predictions = entity.detailed_predictions
        model.model_version = entity.model_version
        model.confidence_score = entity.confidence_score
        model.feature_importance = entity.feature_importance
        model.actual_result = entity.actual_result
        model.prediction_accuracy = entity.prediction_accuracy

    @staticmethod
    def _model_to_entity(model: PredictionModel) -> Prediction:
        """Convert a PredictionModel to a Prediction entity."""
        prediction = Prediction(
            id=model.id,
            game_id=model.game_id,
            prediction_type=model.prediction_type,
            home_win_probability=model.home_win_probability,
            away_win_probability=model.away_win_probability,
            over_under_runs=model.over_under_runs,
            total_runs_prediction=model.total_runs_prediction,
            detailed_predictions=model.detailed_predictions,
            model_version=model.model_version,
            confidence_score=model.confidence_score,
            feature_importance=model.feature_importance,
            actual_result=model.actual_result,
            prediction_accuracy=model.prediction_accuracy,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

        # Set related game if loaded
        if hasattr(model, "game") and model.game:
            prediction.game = PredictionRepository._game_model_to_entity(model.game)

        return prediction

    @staticmethod
    def _game_model_to_entity(model: GameModel) -> Game:
        """Convert a GameModel to a Game entity."""
        return game_model_to_entity(model)

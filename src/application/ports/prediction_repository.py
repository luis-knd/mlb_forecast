"""
Prediction repository port (interface) for the application layer.
This defines how the application interacts with prediction data storage.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from src.domain.entities.prediction import Prediction


class PredictionRepositoryPort(ABC):
    """Interface for prediction repository operations."""

    @abstractmethod
    async def get_by_id(self, prediction_id: int) -> Optional[Prediction]:
        """Get a prediction by its ID."""
        pass

    @abstractmethod
    async def list_by_game(self, game_id: int) -> List[Prediction]:
        """List predictions for a specific game."""
        pass

    @abstractmethod
    async def list_by_game_and_type(self, game_id: int, prediction_type: str) -> List[Prediction]:
        """List predictions for a specific game and type."""
        pass

    @abstractmethod
    async def list_latest_predictions(self, limit: int = 50) -> List[Prediction]:
        """List the latest predictions."""
        pass

    @abstractmethod
    async def list_by_model_version(self, model_version: str, limit: int = 50) -> List[Prediction]:
        """List predictions by model version."""
        pass

    @abstractmethod
    async def save(self, prediction: Prediction) -> Prediction:
        """Save a prediction (create or update)."""
        pass

    @abstractmethod
    async def update_with_actual_result(
        self, prediction_id: int, actual_result: Dict[str, Any], accuracy: float
    ) -> Optional[Prediction]:
        """Update a prediction with the actual result and accuracy."""
        pass

    @abstractmethod
    async def delete(self, prediction_id: int) -> bool:
        """Delete a prediction by its ID."""
        pass

    @abstractmethod
    async def get_prediction_accuracy_by_model(self, model_version: str) -> float:
        """Get the average prediction accuracy for a specific model version."""
        pass

"""
ML Model port (interface) for the application layer.
This defines how the application interacts with machine learning models for predictions.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.domain.entities.game import Game
from src.domain.entities.prediction import Prediction


class MLModelPort(ABC):
    """Interface for machine learning model operations."""

    @abstractmethod
    async def train(self, historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Train the model with historical data and return performance metrics."""
        pass

    @abstractmethod
    async def predict_game_outcome(
        self,
        home_team_stats: Dict[str, Any],
        away_team_stats: Dict[str, Any],
        game_date: datetime,
        historical_matchups: Optional[List[Game]] = None,
    ) -> Prediction:
        """Predict the outcome of a game based on team statistics and historical matchups."""
        pass

    @abstractmethod
    async def evaluate_model(self, test_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """Evaluate the model on test data and return performance metrics."""
        pass

    @abstractmethod
    async def get_feature_importance(self) -> Dict[str, float]:
        """Get the importance of each feature in the model."""
        pass

    @abstractmethod
    async def save_model(self, filepath: str) -> bool:
        """Save the model to a file."""
        pass

    @abstractmethod
    async def load_model(self, filepath: str) -> bool:
        """Load the model from a file."""
        pass

    @abstractmethod
    async def get_model_version(self) -> str:
        """Get the current model version."""
        pass

    @abstractmethod
    async def get_model_performance(self) -> Dict[str, float]:
        """Get the current model performance metrics."""
        pass

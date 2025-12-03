"""
Prediction entity representing a prediction for a baseball game in the MLB.
This is a pure domain entity without any framework dependencies.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from src.domain.entities.game import Game


@dataclass
class Prediction:
    """Prediction entity representing a prediction for a baseball game in the MLB."""

    id: Optional[int]
    game_id: int
    prediction_type: str  # winner, total_runs, player_performance
    home_win_probability: Optional[float] = None
    away_win_probability: Optional[float] = None
    over_under_runs: Optional[float] = None
    total_runs_prediction: Optional[float] = None
    detailed_predictions: Optional[Dict[str, Any]] = None
    model_version: str = "1.0.0"
    confidence_score: Optional[float] = None
    feature_importance: Optional[Dict[str, Any]] = None
    actual_result: Optional[Dict[str, Any]] = None
    prediction_accuracy: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # This is not stored but can be set for convenience
    game: Optional[Game] = None

    @classmethod
    def create(
        cls,
        game_id: int,
        prediction_type: str,
        model_version: str,
        home_win_probability: Optional[float] = None,
        away_win_probability: Optional[float] = None,
        over_under_runs: Optional[float] = None,
        total_runs_prediction: Optional[float] = None,
        detailed_predictions: Optional[Dict[str, Any]] = None,
        confidence_score: Optional[float] = None,
        feature_importance: Optional[Dict[str, Any]] = None,
    ) -> "Prediction":
        """Factory method to create a new Prediction entity."""
        return cls(
            id=None,
            game_id=game_id,
            prediction_type=prediction_type,
            home_win_probability=home_win_probability,
            away_win_probability=away_win_probability,
            over_under_runs=over_under_runs,
            total_runs_prediction=total_runs_prediction,
            detailed_predictions=detailed_predictions,
            model_version=model_version,
            confidence_score=confidence_score,
            feature_importance=feature_importance,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

    def update_with_actual_result(self, actual_result: Dict[str, Any], accuracy: float) -> None:
        """Update the prediction with the actual result and accuracy."""
        self.actual_result = actual_result
        self.prediction_accuracy = accuracy
        self.updated_at = datetime.now()

    def get_predicted_winner(self) -> Optional[str]:
        """Get the predicted winner (home/away) based on win probabilities."""
        if self.home_win_probability is None or self.away_win_probability is None:
            return None

        if self.home_win_probability > self.away_win_probability:
            return "home"
        elif self.away_win_probability > self.home_win_probability:
            return "away"

        return None  # Equal probabilities

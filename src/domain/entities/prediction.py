"""
Prediction entity representing a prediction for a baseball game in the MLB.
This is a pure domain entity without any framework dependencies.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.domain.entities.game import Game


@dataclass
class Prediction:
    """Prediction entity representing a prediction for a baseball game in the MLB."""

    id: int | None
    game_id: int
    prediction_type: str  # winner, total_runs, player_performance
    home_win_probability: float | None = None
    away_win_probability: float | None = None
    over_under_runs: float | None = None
    total_runs_prediction: float | None = None
    detailed_predictions: dict[str, Any] | None = None
    model_version: str = "1.0.0"
    confidence_score: float | None = None
    feature_importance: dict[str, Any] | None = None
    actual_result: dict[str, Any] | None = None
    prediction_accuracy: float | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # This is not stored but can be set for convenience
    game: Game | None = None

    @classmethod
    def create(
        cls,
        game_id: int,
        prediction_type: str,
        model_version: str,
        home_win_probability: float | None = None,
        away_win_probability: float | None = None,
        over_under_runs: float | None = None,
        total_runs_prediction: float | None = None,
        detailed_predictions: dict[str, Any] | None = None,
        confidence_score: float | None = None,
        feature_importance: dict[str, Any] | None = None,
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

    def update_with_actual_result(self, actual_result: dict[str, Any], accuracy: float) -> None:
        """Update the prediction with the actual result and accuracy."""
        self.actual_result = actual_result
        self.prediction_accuracy = accuracy
        self.updated_at = datetime.now()

    def get_predicted_winner(self) -> str | None:
        """Get the predicted winner (home/away) based on win probabilities."""
        if self.home_win_probability is None or self.away_win_probability is None:
            return None

        if self.home_win_probability > self.away_win_probability:
            return "home"
        elif self.away_win_probability > self.home_win_probability:
            return "away"

        return None  # Equal probabilities

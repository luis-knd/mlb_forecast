"""
Use cases for prediction operations.
These define the application's business logic for prediction operations.
"""

from datetime import datetime
from typing import Any

from src.application.ports.cache import CachePort
from src.application.ports.game_repository import GameRepositoryPort
from src.application.ports.ml_model import MLModelPort
from src.application.ports.prediction_repository import PredictionRepositoryPort
from src.application.ports.team_stats_repository import TeamStatsRepositoryPort
from src.domain.entities.prediction import Prediction


class GeneratePredictionUseCase:
    """Use case for generating a prediction for a game."""

    def __init__(
        self,
        prediction_repository: PredictionRepositoryPort,
        game_repository: GameRepositoryPort,
        team_stats_repository: TeamStatsRepositoryPort,
        ml_model: MLModelPort,
        cache: CachePort,
    ):
        self.prediction_repository = prediction_repository
        self.game_repository = game_repository
        self.team_stats_repository = team_stats_repository
        self.ml_model = ml_model
        self.cache = cache

    async def execute(self, game_id: int, prediction_type: str = "winner") -> Prediction | None:
        """
        Generate a prediction for a game.

        Args:
            game_id: The ID of the game to predict
            prediction_type: The type of prediction to generate (winner, total_runs, etc.)

        Returns:
            Prediction entity or None if prediction could not be generated
        """
        # Get the game
        game = await self.game_repository.get_by_id(game_id)
        if not game:
            return None

        # Check if game is already completed
        if game.is_completed():
            return None

        # Get team stats for the current season
        current_season = datetime.now().year
        home_team_stats = await self.team_stats_repository.get_by_team_and_season(game.home_team_id, current_season)
        away_team_stats = await self.team_stats_repository.get_by_team_and_season(game.away_team_id, current_season)

        if not home_team_stats or not away_team_stats:
            return None

        # Get historical matchups
        historical_matchups = await self.game_repository.list_historical_matchups(
            game.home_team_id, game.away_team_id, limit=10
        )

        # Generate prediction using ML model
        prediction = await self.ml_model.predict_game_outcome(
            home_team_stats=home_team_stats,
            away_team_stats=away_team_stats,
            game_date=game.game_date,
            historical_matchups=historical_matchups,
        )

        # Set game ID and prediction type
        prediction.game_id = game_id
        prediction.prediction_type = prediction_type

        # Save prediction to repository
        saved_prediction = await self.prediction_repository.save(prediction)

        # Clear cache for predictions
        await self.cache.clear(pattern=f"predictions:game:{game_id}*")

        return saved_prediction


class GetPredictionsForGameUseCase:
    """Use case for getting predictions for a game."""

    def __init__(self, prediction_repository: PredictionRepositoryPort, cache: CachePort):
        self.prediction_repository = prediction_repository
        self.cache = cache

    async def execute(self, game_id: int, prediction_type: str | None = None) -> list[Prediction]:
        """
        Get predictions for a game, optionally filtered by prediction type.

        Args:
            game_id: The ID of the game to get predictions for
            prediction_type: Optional filter by prediction type

        Returns:
            List of Prediction entities
        """
        cache_key = f"predictions:game:{game_id}:{prediction_type or 'all'}"

        # Try to get from cache first
        cached_predictions = await self.cache.get(cache_key)
        if cached_predictions:
            return cached_predictions

        # Get from repository
        if prediction_type:
            predictions = await self.prediction_repository.list_by_game_and_type(game_id, prediction_type)
        else:
            predictions = await self.prediction_repository.list_by_game(game_id)

        # Cache the result
        await self.cache.set(cache_key, predictions, ttl=1800)  # Cache for 30 minutes

        return predictions


class ListUpcomingPredictionsUseCase:
    """Use case for listing predictions for upcoming games."""

    def __init__(
        self,
        prediction_repository: PredictionRepositoryPort,
        game_repository: GameRepositoryPort,
        cache: CachePort,
    ):
        self.prediction_repository = prediction_repository
        self.game_repository = game_repository
        self.cache = cache

    async def execute(self, days_ahead: int = 3, limit: int = 20) -> list[dict[str, Any]]:
        """
        List predictions for upcoming games.

        Args:
            days_ahead: Number of days ahead to look for games
            limit: Maximum number of games to return

        Returns:
            List of dictionaries containing game and prediction information
        """
        cache_key = f"predictions:upcoming:{days_ahead}:{limit}"

        # Try to get from cache first
        cached_result = await self.cache.get(cache_key)
        if cached_result:
            return cached_result

        # Get upcoming games
        upcoming_games = await self.game_repository.list_upcoming_games(days_ahead, limit)

        # Get predictions for each game
        result = []
        for game in upcoming_games:
            # Ensure game.id is not None before proceeding
            if game.id is None:
                continue

            predictions = await self.prediction_repository.list_by_game(game.id)

            # If no predictions exist for this game, skip it
            if not predictions:
                continue

            # Get the most recent prediction of each type - add proper type annotation
            prediction_by_type: dict[str, Any] = {}
            for prediction in predictions:
                # Ensure created_at is not None before comparison
                if prediction.created_at is None:
                    continue

                # If we haven't seen this type yet, or this prediction is newer
                if prediction.prediction_type not in prediction_by_type or (
                    prediction_by_type[prediction.prediction_type].created_at is not None
                    and prediction.created_at > prediction_by_type[prediction.prediction_type].created_at
                ):
                    prediction_by_type[prediction.prediction_type] = prediction

            # Add game and predictions to result
            result.append({"game": game, "predictions": list(prediction_by_type.values())})

        # Cache the result
        await self.cache.set(cache_key, result, ttl=1800)  # Cache for 30 minutes

        return result


class UpdatePredictionWithResultUseCase:
    """Use case for updating a prediction with the actual result."""

    def __init__(
        self,
        prediction_repository: PredictionRepositoryPort,
        game_repository: GameRepositoryPort,
        cache: CachePort,
    ):
        self.prediction_repository = prediction_repository
        self.game_repository = game_repository
        self.cache = cache

    async def execute(self, prediction_id: int) -> Prediction | None:
        """
        Update a prediction with the actual result of the game.

        Args:
            prediction_id: The ID of the prediction to update

        Returns:
            Updated Prediction entity or None if update failed
        """
        prediction = await self.prediction_repository.get_by_id(prediction_id)
        if prediction is None:
            return None

        game = await self._get_completed_game(prediction.game_id)
        if game is None:
            return None

        actual_result = self._build_actual_result(game)
        accuracy = self._calculate_accuracy(prediction, game)
        updated_prediction = await self.prediction_repository.update_with_actual_result(
            prediction_id, actual_result, accuracy
        )
        await self.cache.clear(pattern=f"predictions:game:{prediction.game_id}*")
        return updated_prediction

    async def _get_completed_game(self, game_id: int) -> Any | None:
        game = await self.game_repository.get_by_id(game_id)
        if game is None or not game.is_completed():
            return None
        return game

    @staticmethod
    def _build_actual_result(game: Any) -> dict[str, Any]:
        return {
            "home_score": game.home_score,
            "away_score": game.away_score,
            "winning_team_id": game.winning_team_id,
        }

    def _calculate_accuracy(self, prediction: Prediction, game: Any) -> float:
        if prediction.prediction_type == "winner":
            return self._winner_accuracy(prediction, game)
        if prediction.prediction_type == "total_runs":
            return self._total_runs_accuracy(prediction, game)
        return 0.0

    @staticmethod
    def _winner_accuracy(prediction: Prediction, game: Any) -> float:
        if game.home_score is None or game.away_score is None:
            return 0.0
        predicted_winner = prediction.get_predicted_winner()
        if predicted_winner == "home" and game.home_score > game.away_score:
            return 1.0
        if predicted_winner == "away" and game.away_score > game.home_score:
            return 1.0
        return 0.0

    @staticmethod
    def _total_runs_accuracy(prediction: Prediction, game: Any) -> float:
        if prediction.total_runs_prediction is None or game.home_score is None or game.away_score is None:
            return 0.0
        actual_total = game.home_score + game.away_score
        if actual_total <= 0:
            return 1.0 if prediction.total_runs_prediction == actual_total else 0.0
        error = abs(prediction.total_runs_prediction - actual_total)
        return max(0.0, 1.0 - (error / actual_total))

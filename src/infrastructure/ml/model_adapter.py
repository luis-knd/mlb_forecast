"""
ML model adapter implementation.
This module implements the MLModelPort interface using scikit-learn.
"""

import logging
import os
import pickle
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from src.application.ports.ml_model import MLModelPort
from src.domain.entities.game import Game
from src.domain.entities.prediction import Prediction
from src.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


class MLModelException(Exception):
    """Custom exception for ML model errors."""

    pass


class MLModelAdapter(MLModelPort):
    """Implementation of the MLModelPort interface using scikit-learn."""

    def __init__(self):
        self.winner_model = RandomForestClassifier(
            n_estimators=100, max_depth=10, random_state=42, class_weight="balanced"
        )
        self.runs_model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
        self.model_version = settings.DEFAULT_MODEL_VERSION
        self.model_dir = settings.MODEL_DIR

        # Create model directory if it doesn't exist
        os.makedirs(self.model_dir, exist_ok=True)

        # Try to load existing model
        self._try_load_model()

    async def train(self, historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Train the model with historical data and return performance metrics."""
        logger.info("Starting model training")

        try:
            # Convert historical data to DataFrame
            df = pd.DataFrame(historical_data)

            if df.empty or len(df) < 50:
                raise MLModelException("Insufficient historical data for training")

            # Prepare features and targets
            features_df = df.drop(columns=["winner", "total_runs"])
            winner_df = df["winner"]
            runs_df = df["total_runs"]

            # Preprocess features
            features_scaled = self.scaler.fit_transform(features_df.fillna(0))

            # Split data
            X_train, X_test, y_winner_train, y_winner_test = train_test_split(
                features_scaled, winner_df, test_size=0.2, random_state=42
            )

            _, _, y_runs_train, y_runs_test = train_test_split(features_scaled, runs_df, test_size=0.2, random_state=42)

            # Train models
            self.winner_model.fit(X_train, y_winner_train)
            self.runs_model.fit(X_train, y_runs_train)

            self.is_trained = True
            self.model_version = f"v1.0_{datetime.now().strftime('%Y%m%d')}"

            # Evaluate models
            winner_pred = self.winner_model.predict(X_test)
            runs_pred = self.runs_model.predict(X_test)

            metrics = {
                "winner_accuracy": float(accuracy_score(y_winner_test, winner_pred)),
                "winner_precision": float(precision_score(y_winner_test, winner_pred, average="weighted")),
                "winner_recall": float(recall_score(y_winner_test, winner_pred, average="weighted")),
                "winner_f1": float(f1_score(y_winner_test, winner_pred, average="weighted")),
                "runs_mae": float(mean_absolute_error(y_runs_test, runs_pred)),
                "training_samples": len(df),
                "model_version": self.model_version,
            }

            # Save model
            await self.save_model(os.path.join(self.model_dir, f"model_{self.model_version}.pkl"))

            logger.info(f"Training completed: {metrics}")
            return metrics

        except Exception as e:
            logger.error(f"Error during training: {e}")
            raise MLModelException(f"Training error: {e}")

    async def predict_game_outcome(
        self,
        home_team_stats: Dict[str, Any],
        away_team_stats: Dict[str, Any],
        game_date: datetime,
        historical_matchups: Optional[List[Game]] = None,
    ) -> Prediction:
        """Predict the outcome of a game based on team statistics and historical matchups."""
        if not self.is_trained:
            raise MLModelException("Model has not been trained")

        try:
            # Create features
            features = self._create_game_features(home_team_stats, away_team_stats, game_date, historical_matchups)

            # Prepare for prediction
            features_array = np.array([list(features.values())])
            features_scaled = self.scaler.transform(features_array)

            # Make predictions
            home_win_prob = float(self.winner_model.predict_proba(features_scaled)[0][1])
            away_win_prob = 1.0 - home_win_prob

            predicted_total_runs = float(self.runs_model.predict(features_scaled)[0])

            # Calculate confidence
            confidence = float(max(home_win_prob, away_win_prob))

            # Get feature importance
            feature_importance = self._get_feature_importance()

            # Create prediction entity
            prediction = Prediction.create(
                game_id=0,  # This will be set by the use case
                prediction_type="winner",
                model_version=self.model_version,
                home_win_probability=home_win_prob,
                away_win_probability=away_win_prob,
                total_runs_prediction=predicted_total_runs,
                confidence_score=confidence,
                feature_importance=feature_importance,
            )

            return prediction

        except Exception as e:
            logger.error(f"Error during prediction: {e}")
            raise MLModelException(f"Prediction error: {e}")

    async def evaluate_model(self, test_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """Evaluate the model on test data and return performance metrics."""
        if not self.is_trained:
            raise MLModelException("Model has not been trained")

        try:
            # Convert test data to DataFrame
            df = pd.DataFrame(test_data)

            if df.empty:
                raise MLModelException("Empty test data")

            # Prepare features and targets
            features_df = df.drop(columns=["winner", "total_runs"])
            winner_df = df["winner"]
            runs_df = df["total_runs"]

            # Preprocess features
            features_scaled = self.scaler.transform(features_df.fillna(0))

            # Make predictions
            winner_pred = self.winner_model.predict(features_scaled)
            runs_pred = self.runs_model.predict(features_scaled)

            # Calculate metrics
            metrics = {
                "winner_accuracy": float(accuracy_score(winner_df, winner_pred)),
                "winner_precision": float(precision_score(winner_df, winner_pred, average="weighted")),
                "winner_recall": float(recall_score(winner_df, winner_pred, average="weighted")),
                "winner_f1": float(f1_score(winner_df, winner_pred, average="weighted")),
                "runs_mae": float(mean_absolute_error(runs_df, runs_pred)),
                "test_samples": len(df),
            }

            logger.info(f"Model evaluation completed: {metrics}")
            return metrics

        except Exception as e:
            logger.error(f"Error during model evaluation: {e}")
            raise MLModelException(f"Evaluation error: {e}")

    async def get_feature_importance(self) -> Dict[str, float]:
        """Get the importance of each feature in the model."""
        if not self.is_trained:
            raise MLModelException("Model has not been trained")

        return self._get_feature_importance()

    async def save_model(self, filepath: str) -> bool:
        """Save the model to a file."""
        try:
            model_data = {
                "winner_model": self.winner_model,
                "runs_model": self.runs_model,
                "scaler": self.scaler,
                "model_version": self.model_version,
                "is_trained": self.is_trained,
            }

            with open(filepath, "wb") as f:
                pickle.dump(model_data, f)

            logger.info(f"Model saved to {filepath}")
            return True

        except Exception as e:
            logger.error(f"Error saving model: {e}")
            return False

    async def load_model(self, filepath: str) -> bool:
        """Load the model from a file."""
        try:
            with open(filepath, "rb") as f:
                model_data = pickle.load(f)

            self.winner_model = model_data["winner_model"]
            self.runs_model = model_data["runs_model"]
            self.scaler = model_data["scaler"]
            self.model_version = model_data["model_version"]
            self.is_trained = model_data["is_trained"]

            logger.info(f"Model loaded from {filepath}")
            return True

        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False

    async def get_model_version(self) -> str:
        """Get the current model version."""
        return self.model_version

    async def get_model_performance(self) -> Dict[str, Any]:
        """Get the current model performance metrics."""
        if not self.is_trained:
            return {"error": "Model not trained"}

        # This would typically come from a database, but for simplicity
        # we'll return some basic information
        return {
            "is_trained": float(self.is_trained),
            "model_version": self.model_version,
        }

    def _try_load_model(self) -> None:
        """Try to load the latest model."""
        try:
            # Find the latest model file
            model_files = [f for f in os.listdir(self.model_dir) if f.startswith("model_") and f.endswith(".pkl")]

            if not model_files:
                logger.info("No existing model found")
                return

            # Sort by version/date
            latest_model = sorted(model_files)[-1]
            model_path = os.path.join(self.model_dir, latest_model)

            # Load the model
            with open(model_path, "rb") as f:
                model_data = pickle.load(f)

            self.winner_model = model_data["winner_model"]
            self.runs_model = model_data["runs_model"]
            self.scaler = model_data["scaler"]
            self.model_version = model_data["model_version"]
            self.is_trained = model_data["is_trained"]

            logger.info(f"Loaded existing model: {self.model_version}")

        except Exception as e:
            logger.warning(f"Could not load existing model: {e}")

    def _create_game_features(
        self,
        home_team_stats: Dict[str, Any],
        away_team_stats: Dict[str, Any],
        game_date: datetime,
        historical_matchups: Optional[List[Game]] = None,
    ) -> Dict[str, float]:
        """Create features for game prediction."""
        # Convert TeamStats entities to dictionaries
        home_stats_dict = self._team_stats_to_dict(home_team_stats)
        away_stats_dict = self._team_stats_to_dict(away_team_stats)

        # Create matchup features
        matchup_features = self._create_matchup_features(home_stats_dict, away_stats_dict, historical_matchups)

        # Create temporal features
        temporal_features = self._create_temporal_features(game_date)

        # Combine all features
        features = {
            **home_stats_dict,
            **{f"away_{k}": v for k, v in away_stats_dict.items()},
            **matchup_features,
            **temporal_features,
        }

        return features

    def _team_stats_to_dict(self, stats: Dict[str, Any]) -> Dict[str, float]:
        """Convert TeamStats dictionary (nested) to flat dictionary for model."""
        # Extract stats from nested dictionary
        hitting = stats.get("hitting_stats") or {}
        pitching = stats.get("pitching_stats") or {}

        # Helper to safely get float
        def _get_f(src, key, default=0.0):
            val = src.get(key, default)
            return float(val) if val is not None else default

        # Helper to safely get int/float
        def _get_n(src, key, default=0):
            val = src.get(key, default)
            return float(val) if val is not None else float(default)

        # Calculate derived stats if missing
        runs_scored = _get_n(hitting, "runs_scored")
        runs_allowed = _get_n(pitching, "runs_allowed")

        run_differential = runs_scored - runs_allowed

        pythagorean_expectation = 0.0
        if runs_scored > 0 and runs_allowed > 0:
            pythagorean_expectation = (runs_scored**2) / (runs_scored**2 + runs_allowed**2)

        games_played = _get_n(hitting, "games_played")
        wins = _get_n(pitching, "wins")
        win_percentage = (wins / games_played) if games_played > 0 else 0.0

        return {
            "games_played": games_played,
            "wins": wins,
            "losses": _get_n(pitching, "losses"),
            "runs_scored": runs_scored,
            "runs_allowed": runs_allowed,
            "batting_average": _get_f(hitting, "batting_average"),
            "on_base_percentage": _get_f(hitting, "on_base_percentage"),
            "slugging_percentage": _get_f(hitting, "slugging_percentage"),
            "earned_run_average": _get_f(pitching, "earned_run_average"),
            "win_percentage": win_percentage,
            "ops": _get_f(hitting, "ops"),
            "run_differential": run_differential,
            "pythagorean_expectation": pythagorean_expectation,
        }

    def _create_matchup_features(
        self,
        home_stats: Dict[str, float],
        away_stats: Dict[str, float],
        historical_matchups: Optional[List[Game]] = None,
    ) -> Dict[str, float]:
        """Create features based on team matchup."""
        features = {}

        # Differences between teams
        features["win_pct_diff"] = home_stats.get("win_percentage", 0) - away_stats.get("win_percentage", 0)
        features["runs_diff_advantage"] = home_stats.get("run_differential", 0) - away_stats.get("run_differential", 0)
        features["ops_diff"] = home_stats.get("ops", 0) - away_stats.get("ops", 0)
        features["era_diff"] = away_stats.get("earned_run_average", 0) - home_stats.get("earned_run_average", 0)

        # Home field advantage
        features["home_field_advantage"] = 1.0

        # Historical matchups
        if historical_matchups:
            recent_games = historical_matchups[-10:]  # Last 10 games

            # Home team win rate in matchups
            home_wins = sum(
                1
                for game in recent_games
                if game.winning_team_id == game.home_team_id and game.home_team_id == home_stats.get("team_id")
            )

            features["historical_home_win_rate"] = home_wins / len(recent_games) if recent_games else 0.5

            # Average total runs in matchups
            total_runs = [
                (game.home_score or 0) + (game.away_score or 0)
                for game in recent_games
                if game.home_score is not None and game.away_score is not None
            ]

            features["avg_total_runs_historical"] = sum(total_runs) / len(total_runs) if total_runs else 9.0
        else:
            features["historical_home_win_rate"] = 0.5
            features["avg_total_runs_historical"] = 9.0

        return features

    def _create_temporal_features(self, game_date: datetime) -> Dict[str, float]:
        """Create features based on game date."""
        features = {}

        features["day_of_week"] = float(game_date.weekday())  # 0 = Monday, 6 = Sunday
        features["month"] = float(game_date.month)
        features["is_weekend"] = float(game_date.weekday() >= 5)

        # Season progress
        season_start = datetime(game_date.year, 3, 1)  # Approximate
        days_since_season_start = (game_date - season_start).days
        features["season_progress"] = min(days_since_season_start / 180.0, 1.0)  # Normalized

        return features

    def _get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance from the winner model."""
        if not self.is_trained:
            return {}

        try:
            # Get feature names (this would be more robust in a real implementation)
            feature_names = [
                "games_played",
                "wins",
                "losses",
                "runs_scored",
                "runs_allowed",
                "batting_average",
                "on_base_percentage",
                "slugging_percentage",
                "earned_run_average",
                "win_percentage",
                "ops",
                "run_differential",
                "pythagorean_expectation",
                "away_games_played",
                "away_wins",
                "away_losses",
                "away_runs_scored",
                "away_runs_allowed",
                "away_batting_average",
                "away_on_base_percentage",
                "away_slugging_percentage",
                "away_earned_run_average",
                "away_win_percentage",
                "away_ops",
                "away_run_differential",
                "away_pythagorean_expectation",
                "win_pct_diff",
                "runs_diff_advantage",
                "ops_diff",
                "era_diff",
                "home_field_advantage",
                "historical_home_win_rate",
                "avg_total_runs_historical",
                "day_of_week",
                "month",
                "is_weekend",
                "season_progress",
            ]

            # Get importance values
            importance = self.winner_model.feature_importances_

            # Create dictionary of feature importance
            # If the number of features doesn't match, use indices
            if len(feature_names) != len(importance):
                return {f"feature_{i}": float(imp) for i, imp in enumerate(importance)}

            return {name: float(imp) for name, imp in zip(feature_names, importance)}

        except Exception as e:
            logger.error(f"Error getting feature importance: {e}")
            return {}

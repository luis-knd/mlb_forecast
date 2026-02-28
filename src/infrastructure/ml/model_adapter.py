"""
ML model adapter implementation.
This module implements the MLModelPort interface using scikit-learn.
"""

import logging
import os
import pickle
from datetime import datetime
from typing import Any, Protocol

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

WINNER_FEATURE_NAMES = [
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


def _to_float(source: dict[str, Any], key: str, default: float = 0.0) -> float:
    value = source.get(key, default)
    return float(value) if value is not None else default


def _to_number(source: dict[str, Any], key: str, default: int = 0) -> float:
    value = source.get(key, default)
    return float(value) if value is not None else float(default)


def _team_stats_to_dict(stats: dict[str, Any]) -> dict[str, float]:
    hitting = stats.get("hitting_stats") or {}
    pitching = stats.get("pitching_stats") or {}

    runs_scored = _to_number(hitting, "runs_scored")
    runs_allowed = _to_number(pitching, "runs_allowed")
    games_played = _to_number(hitting, "games_played")
    wins = _to_number(pitching, "wins")

    run_differential = runs_scored - runs_allowed
    pythagorean_expectation = 0.0
    if runs_scored > 0 and runs_allowed > 0:
        pythagorean_expectation = (runs_scored**2) / (runs_scored**2 + runs_allowed**2)

    win_percentage = (wins / games_played) if games_played > 0 else 0.0
    return {
        "games_played": games_played,
        "wins": wins,
        "losses": _to_number(pitching, "losses"),
        "runs_scored": runs_scored,
        "runs_allowed": runs_allowed,
        "batting_average": _to_float(hitting, "batting_average"),
        "on_base_percentage": _to_float(hitting, "on_base_percentage"),
        "slugging_percentage": _to_float(hitting, "slugging_percentage"),
        "earned_run_average": _to_float(pitching, "earned_run_average"),
        "win_percentage": win_percentage,
        "ops": _to_float(hitting, "ops"),
        "run_differential": run_differential,
        "pythagorean_expectation": pythagorean_expectation,
    }


def _create_matchup_features(
    home_stats: dict[str, float],
    away_stats: dict[str, float],
    historical_matchups: list[Game] | None = None,
) -> dict[str, float]:
    features = {
        "win_pct_diff": home_stats.get("win_percentage", 0) - away_stats.get("win_percentage", 0),
        "runs_diff_advantage": home_stats.get("run_differential", 0) - away_stats.get("run_differential", 0),
        "ops_diff": home_stats.get("ops", 0) - away_stats.get("ops", 0),
        "era_diff": away_stats.get("earned_run_average", 0) - home_stats.get("earned_run_average", 0),
        "home_field_advantage": 1.0,
        "historical_home_win_rate": 0.5,
        "avg_total_runs_historical": 9.0,
    }
    if not historical_matchups:
        return features

    recent_games = historical_matchups[-10:]
    home_wins = sum(
        1
        for game in recent_games
        if game.winning_team_id == game.home_team_id and game.home_team_id == home_stats.get("team_id")
    )
    total_runs = [
        (game.home_score or 0) + (game.away_score or 0)
        for game in recent_games
        if game.home_score is not None and game.away_score is not None
    ]
    features["historical_home_win_rate"] = home_wins / len(recent_games) if recent_games else 0.5
    features["avg_total_runs_historical"] = sum(total_runs) / len(total_runs) if total_runs else 9.0
    return features


def _create_temporal_features(game_date: datetime) -> dict[str, float]:
    season_start = datetime(game_date.year, 3, 1)
    days_since_season_start = (game_date - season_start).days
    return {
        "day_of_week": float(game_date.weekday()),
        "month": float(game_date.month),
        "is_weekend": float(game_date.weekday() >= 5),
        "season_progress": min(days_since_season_start / 180.0, 1.0),
    }


def _create_game_features(
    home_team_stats: dict[str, Any],
    away_team_stats: dict[str, Any],
    game_date: datetime,
    historical_matchups: list[Game] | None = None,
) -> dict[str, float]:
    home_stats_dict = _team_stats_to_dict(home_team_stats)
    away_stats_dict = _team_stats_to_dict(away_team_stats)
    matchup_features = _create_matchup_features(home_stats_dict, away_stats_dict, historical_matchups)
    temporal_features = _create_temporal_features(game_date)
    return {
        **home_stats_dict,
        **{f"away_{key}": value for key, value in away_stats_dict.items()},
        **matchup_features,
        **temporal_features,
    }


class MLModelException(Exception):
    """Custom exception for ML model errors."""

    pass


class _ModelPersistenceContext(Protocol):
    winner_model: RandomForestClassifier
    runs_model: RandomForestRegressor
    scaler: StandardScaler
    is_trained: bool
    model_version: str
    model_dir: str


class _ModelPersistenceMixin:
    def _try_load_model(self: _ModelPersistenceContext) -> None:
        """Try to load the latest model."""
        try:
            model_files = [
                filename
                for filename in os.listdir(self.model_dir)
                if filename.startswith("model_") and filename.endswith(".pkl")
            ]
            if not model_files:
                logger.info("No existing model found")
                return

            model_path = os.path.join(self.model_dir, sorted(model_files)[-1])
            with open(model_path, "rb") as file_handle:
                model_data = pickle.load(file_handle)
            self.winner_model = model_data["winner_model"]
            self.runs_model = model_data["runs_model"]
            self.scaler = model_data["scaler"]
            self.model_version = model_data["model_version"]
            self.is_trained = model_data["is_trained"]
            logger.info(f"Loaded existing model: {self.model_version}")
        except Exception as e:
            logger.warning(f"Could not load existing model: {e}")


class MLModelAdapter(_ModelPersistenceMixin, MLModelPort):
    """Implementation of the MLModelPort interface using scikit-learn."""

    _create_game_features = staticmethod(_create_game_features)
    _team_stats_to_dict = staticmethod(_team_stats_to_dict)
    _create_matchup_features = staticmethod(_create_matchup_features)
    _create_temporal_features = staticmethod(_create_temporal_features)

    def __init__(self):
        self.winner_model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            class_weight="balanced",
        )
        self.runs_model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
        self.model_version = settings.DEFAULT_MODEL_VERSION
        self.model_dir = settings.MODEL_DIR
        os.makedirs(self.model_dir, exist_ok=True)
        self._try_load_model()

    async def train(self, historical_data: list[dict[str, Any]]) -> dict[str, Any]:
        """Train the model with historical data and return performance metrics."""
        logger.info("Starting model training")
        try:
            training_df = self._to_training_frame(historical_data)
            features_df, winner_df, runs_df = self._extract_training_columns(training_df)
            features_scaled = self.scaler.fit_transform(features_df.fillna(0))
            split_data = self._split_training_data(features_scaled, winner_df, runs_df)
            X_train, X_test, y_winner_train, y_winner_test, y_runs_train, y_runs_test = split_data

            self.winner_model.fit(X_train, y_winner_train)
            self.runs_model.fit(X_train, y_runs_train)
            self.is_trained = True
            self.model_version = self._next_model_version()

            winner_pred = self.winner_model.predict(X_test)
            runs_pred = self.runs_model.predict(X_test)
            metrics = self._build_training_metrics(y_winner_test, winner_pred, y_runs_test, runs_pred, len(training_df))

            await self.save_model(os.path.join(self.model_dir, f"model_{self.model_version}.pkl"))
            logger.info(f"Training completed: {metrics}")
            return metrics
        except Exception as e:
            logger.error(f"Error during training: {e}")
            raise MLModelException(f"Training error: {e}")

    async def predict_game_outcome(
        self,
        home_team_stats: dict[str, Any],
        away_team_stats: dict[str, Any],
        game_date: datetime,
        historical_matchups: list[Game] | None = None,
    ) -> Prediction:
        """Predict the outcome of a game based on team statistics and historical matchups."""
        if not self.is_trained:
            raise MLModelException("Model has not been trained")

        try:
            features = _create_game_features(home_team_stats, away_team_stats, game_date, historical_matchups)
            features_array = np.array([list(features.values())])
            features_scaled = self.scaler.transform(features_array)
            home_win_prob = float(self.winner_model.predict_proba(features_scaled)[0][1])
            away_win_prob = 1.0 - home_win_prob
            predicted_total_runs = float(self.runs_model.predict(features_scaled)[0])
            confidence = float(max(home_win_prob, away_win_prob))

            return Prediction.create(
                game_id=0,
                prediction_type="winner",
                model_version=self.model_version,
                home_win_probability=home_win_prob,
                away_win_probability=away_win_prob,
                total_runs_prediction=predicted_total_runs,
                confidence_score=confidence,
                feature_importance=self._get_feature_importance(),
            )
        except Exception as e:
            logger.error(f"Error during prediction: {e}")
            raise MLModelException(f"Prediction error: {e}")

    async def evaluate_model(self, test_data: list[dict[str, Any]]) -> dict[str, float]:
        """Evaluate the model on test data and return performance metrics."""
        if not self.is_trained:
            raise MLModelException("Model has not been trained")

        try:
            df = pd.DataFrame(test_data)
            if df.empty:
                raise MLModelException("Empty test data")

            features_df, winner_df, runs_df = self._extract_training_columns(df)
            features_scaled = self.scaler.transform(features_df.fillna(0))
            winner_pred = self.winner_model.predict(features_scaled)
            runs_pred = self.runs_model.predict(features_scaled)
            metrics = self._build_training_metrics(winner_df, winner_pred, runs_df, runs_pred, len(df))
            metrics["test_samples"] = metrics.pop("training_samples")
            logger.info(f"Model evaluation completed: {metrics}")
            return metrics
        except Exception as e:
            logger.error(f"Error during model evaluation: {e}")
            raise MLModelException(f"Evaluation error: {e}")

    async def get_feature_importance(self) -> dict[str, float]:
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
            with open(filepath, "wb") as file_handle:
                pickle.dump(model_data, file_handle)
            logger.info(f"Model saved to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error saving model: {e}")
            return False

    async def load_model(self, filepath: str) -> bool:
        """Load the model from a file."""
        try:
            with open(filepath, "rb") as file_handle:
                model_data = pickle.load(file_handle)
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

    async def get_model_performance(self) -> dict[str, Any]:
        """Get the current model performance metrics."""
        if not self.is_trained:
            return {"error": "Model not trained"}
        return {
            "is_trained": float(self.is_trained),
            "model_version": self.model_version,
        }

    @staticmethod
    def _to_training_frame(historical_data: list[dict[str, Any]]) -> pd.DataFrame:
        df = pd.DataFrame(historical_data)
        if df.empty or len(df) < 50:
            raise MLModelException("Insufficient historical data for training")
        return df

    @staticmethod
    def _extract_training_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
        features_df = df.drop(columns=["winner", "total_runs"])
        return features_df, df["winner"], df["total_runs"]

    @staticmethod
    def _split_training_data(
        features_scaled: np.ndarray,
        winner_df: pd.Series,
        runs_df: pd.Series,
    ) -> tuple[np.ndarray, np.ndarray, pd.Series, pd.Series, pd.Series, pd.Series]:
        X_train, X_test, y_winner_train, y_winner_test = train_test_split(
            features_scaled, winner_df, test_size=0.2, random_state=42
        )
        _, _, y_runs_train, y_runs_test = train_test_split(features_scaled, runs_df, test_size=0.2, random_state=42)
        return X_train, X_test, y_winner_train, y_winner_test, y_runs_train, y_runs_test

    def _build_training_metrics(
        self,
        winner_true: pd.Series,
        winner_pred: np.ndarray,
        runs_true: pd.Series,
        runs_pred: np.ndarray,
        samples: int,
    ) -> dict[str, Any]:
        return {
            "winner_accuracy": float(accuracy_score(winner_true, winner_pred)),
            "winner_precision": float(precision_score(winner_true, winner_pred, average="weighted")),
            "winner_recall": float(recall_score(winner_true, winner_pred, average="weighted")),
            "winner_f1": float(f1_score(winner_true, winner_pred, average="weighted")),
            "runs_mae": float(mean_absolute_error(runs_true, runs_pred)),
            "training_samples": samples,
            "model_version": self.model_version,
        }

    @staticmethod
    def _next_model_version() -> str:
        return f"v1.0_{datetime.now().strftime('%Y%m%d')}"

    def _get_feature_importance(self) -> dict[str, float]:
        """Get feature importance from the winner model."""
        if not self.is_trained:
            return {}

        try:
            importance_values = list(self.winner_model.feature_importances_)
            return self._map_feature_importance(importance_values)
        except Exception as e:
            logger.error(f"Error getting feature importance: {e}")
            return {}

    @staticmethod
    def _map_feature_importance(importance_values: list[float]) -> dict[str, float]:
        if len(WINNER_FEATURE_NAMES) != len(importance_values):
            return {f"feature_{index}": float(value) for index, value in enumerate(importance_values)}
        return {name: float(value) for name, value in zip(WINNER_FEATURE_NAMES, importance_values, strict=False)}

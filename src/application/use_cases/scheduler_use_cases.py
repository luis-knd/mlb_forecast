"""
Scheduler use cases for the MLB Forecast application.
This module contains the business logic for scheduled tasks.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from src.application.ports.cache import CachePort
from src.application.ports.game_repository import GameRepositoryPort
from src.application.ports.ml_model import MLModelPort
from src.application.ports.mlb_api import MLBApiPort
from src.application.ports.prediction_repository import PredictionRepositoryPort
from src.application.ports.team_repository import TeamRepositoryPort
from src.application.ports.team_stats_repository import TeamStatsRepositoryPort
from src.domain.entities.game import Game
from src.domain.entities.team import Team
from src.domain.entities.team_stats import TeamStats

logger = logging.getLogger(__name__)


async def _ingest_games_for_date_impl(
    mlb_api: MLBApiPort,
    game_repository: GameRepositoryPort,
    cache: CachePort,
    date_obj: date,
) -> List[Game]:
    games_data = await mlb_api.get_games_by_date(date_obj)
    games: List[Game] = []
    for game_data in games_data:
        mlb_game_id = game_data.id
        home_team_id = game_data.home_team_id
        away_team_id = game_data.away_team_id
        game_date = game_data.game_date
        if not mlb_game_id or not home_team_id or not away_team_id or game_date is None:
            continue
        try:
            mlb_game_id_int = int(mlb_game_id)
            home_team_id_int = int(home_team_id)
            away_team_id_int = int(away_team_id)
        except (ValueError, TypeError):
            continue
        game = Game.create(
            mlb_game_id=mlb_game_id_int,
            home_team_id=home_team_id_int,
            away_team_id=away_team_id_int,
            game_date=game_date,
            status=game_data.status,
            scheduled_innings=game_data.scheduled_innings,
            home_score=game_data.home_score,
            away_score=game_data.away_score,
            winning_team_id=game_data.winning_team_id,
        )
        await game_repository.save(game)
        games.append(game)
        game_dict = {
            "id": game.id,
            "mlb_game_id": game.mlb_game_id,
            "home_team_id": game.home_team_id,
            "away_team_id": game.away_team_id,
            "game_date": game.game_date.isoformat() if game.game_date else None,
            "status": game.status,
            "home_score": game.home_score,
            "away_score": game.away_score,
        }
        await cache.set(f"game:{game.mlb_game_id}", game_dict, ttl=3600)
    return games


def _safe_float(source: Dict[str, Any], key: str, default: float = 0.0) -> float:
    value = source.get(key, default)
    return float(value) if value is not None else default


def _safe_number(source: Dict[str, Any], key: str, default: float = 0.0) -> float:
    value = source.get(key, default)
    return float(value) if value is not None else default


def _build_team_feature_snapshot(hitting_stats: Dict[str, Any], pitching_stats: Dict[str, Any]) -> Dict[str, float]:
    wins = _safe_number(pitching_stats, "wins")
    games_played = max(_safe_number(hitting_stats, "games_played"), 1.0)
    runs_scored = _safe_number(hitting_stats, "runs_scored")
    runs_allowed = _safe_number(pitching_stats, "runs_allowed")
    return {
        "games_played": _safe_number(hitting_stats, "games_played"),
        "wins": wins,
        "losses": _safe_number(pitching_stats, "losses"),
        "runs_scored": runs_scored,
        "runs_allowed": runs_allowed,
        "batting_average": _safe_float(hitting_stats, "batting_average"),
        "on_base_percentage": _safe_float(hitting_stats, "on_base_percentage"),
        "slugging_percentage": _safe_float(hitting_stats, "slugging_percentage"),
        "earned_run_average": _safe_float(pitching_stats, "earned_run_average"),
        "win_percentage": wins / games_played,
        "ops": _safe_float(hitting_stats, "ops"),
        "run_differential": runs_scored - runs_allowed,
    }


def _create_game_features_impl(
    home_team_stats: Dict[str, Any],
    away_team_stats: Dict[str, Any],
    game: Game,
) -> Dict[str, Any]:
    home_hitting = home_team_stats.get("hitting_stats") or {}
    home_pitching = home_team_stats.get("pitching_stats") or {}
    away_hitting = away_team_stats.get("hitting_stats") or {}
    away_pitching = away_team_stats.get("pitching_stats") or {}

    home_stats = _build_team_feature_snapshot(home_hitting, home_pitching)
    away_stats = _build_team_feature_snapshot(away_hitting, away_pitching)
    return {
        "home_games_played": home_stats.get("games_played", 0),
        "home_wins": home_stats.get("wins", 0),
        "home_losses": home_stats.get("losses", 0),
        "home_runs_scored": home_stats.get("runs_scored", 0),
        "home_runs_allowed": home_stats.get("runs_allowed", 0),
        "home_batting_average": home_stats.get("batting_average", 0.0),
        "home_on_base_percentage": home_stats.get("on_base_percentage", 0.0),
        "home_slugging_percentage": home_stats.get("slugging_percentage", 0.0),
        "home_earned_run_average": home_stats.get("earned_run_average", 0.0),
        "home_win_percentage": home_stats.get("win_percentage", 0.0),
        "home_ops": home_stats.get("ops", 0.0),
        "home_run_differential": home_stats.get("run_differential", 0),
        "away_games_played": away_stats.get("games_played", 0),
        "away_wins": away_stats.get("wins", 0),
        "away_losses": away_stats.get("losses", 0),
        "away_runs_scored": away_stats.get("runs_scored", 0),
        "away_runs_allowed": away_stats.get("runs_allowed", 0),
        "away_batting_average": away_stats.get("batting_average", 0.0),
        "away_on_base_percentage": away_stats.get("on_base_percentage", 0.0),
        "away_slugging_percentage": away_stats.get("slugging_percentage", 0.0),
        "away_earned_run_average": away_stats.get("earned_run_average", 0.0),
        "away_win_percentage": away_stats.get("win_percentage", 0.0),
        "away_ops": away_stats.get("ops", 0.0),
        "away_run_differential": away_stats.get("run_differential", 0),
        "win_pct_diff": home_stats.get("win_percentage", 0.0) - away_stats.get("win_percentage", 0.0),
        "runs_diff_advantage": home_stats.get("run_differential", 0) - away_stats.get("run_differential", 0),
        "ops_diff": home_stats.get("ops", 0.0) - away_stats.get("ops", 0.0),
        "era_diff": away_stats.get("earned_run_average", 0.0) - home_stats.get("earned_run_average", 0.0),
        "home_field_advantage": 1.0,
        "day_of_week": game.game_date.weekday(),
        "month": game.game_date.month,
        "is_weekend": 1 if game.game_date.weekday() >= 5 else 0,
    }


async def _generate_upcoming_predictions_impl(
    game_repository: GameRepositoryPort,
    prediction_repository: PredictionRepositoryPort,
    team_stats_repository: TeamStatsRepositoryPort,
    ml_model: MLModelPort,
    cache: CachePort,
) -> Dict[str, Any]:
    try:
        upcoming_games = await game_repository.list_upcoming_games(days_ahead=3)
        predictions_generated = 0
        for game in upcoming_games:
            try:
                if game.id is None:
                    continue
                existing_predictions = await prediction_repository.list_by_game(game.id)
                if existing_predictions:
                    continue
                home_team_stats = await team_stats_repository.get_by_team_and_season(
                    game.home_team_id,
                    game.game_date.year,
                )
                away_team_stats = await team_stats_repository.get_by_team_and_season(
                    game.away_team_id,
                    game.game_date.year,
                )
                if not home_team_stats or not away_team_stats:
                    continue
                prediction = await ml_model.predict_game_outcome(home_team_stats, away_team_stats, game.game_date)
                prediction.game_id = game.id
                await prediction_repository.save(prediction)
                prediction_dict = {
                    "game_id": prediction.game_id,
                    "prediction_type": prediction.prediction_type,
                    "home_win_probability": prediction.home_win_probability,
                    "away_win_probability": prediction.away_win_probability,
                    "model_version": prediction.model_version,
                }
                await cache.set(f"mlb:prediction:{game.id}:outcome", prediction_dict, ttl=1800)
                predictions_generated += 1
            except Exception as exc:
                logger.warning(f"Error generating prediction for game {game.id}: {exc}")
        logger.info(f"✅ Predictions generated: {predictions_generated} games")
        return {
            "success": True,
            "predictions_generated": predictions_generated,
            "total_upcoming_games": len(upcoming_games),
        }
    except Exception as exc:
        logger.error(f"❌ Error generating predictions: {exc}")
        return {"success": False, "error": str(exc)}


class SchedulerUseCases:
    """Use cases for scheduled tasks."""

    def __init__(
        self,
        db_session: Session,
        cache: CachePort,
        ml_model: MLModelPort,
        mlb_api: MLBApiPort,
        game_repository: GameRepositoryPort,
        team_repository: TeamRepositoryPort,
        team_stats_repository: TeamStatsRepositoryPort,
        prediction_repository: PredictionRepositoryPort,
    ):
        self.db_session = db_session
        self.cache = cache
        self.ml_model = ml_model
        self.mlb_api = mlb_api
        self.game_repository = game_repository
        self.team_repository = team_repository
        self.team_stats_repository = team_stats_repository
        self.prediction_repository = prediction_repository

    async def ingest_daily_games(self) -> Dict[str, Any]:
        """
        Ingest games for today, yesterday, and tomorrow.

        Returns:
            Dictionary with ingestion results
        """
        logger.info("🎯 Executing daily games ingestion")

        try:
            # Get dates
            today = datetime.now().date()
            yesterday = today - timedelta(days=1)
            tomorrow = today + timedelta(days=1)

            # Ingest games for each date
            games_today = await self._ingest_games_for_date(today)
            games_yesterday = await self._ingest_games_for_date(yesterday)
            games_tomorrow = await self._ingest_games_for_date(tomorrow)

            total_games = len(games_today) + len(games_yesterday) + len(games_tomorrow)

            logger.info(f"✅ Daily ingestion completed: {total_games} games processed")

            return {
                "success": True,
                "total_games": total_games,
                "games_today": len(games_today),
                "games_yesterday": len(games_yesterday),
                "games_tomorrow": len(games_tomorrow),
            }

        except Exception as e:
            logger.error(f"❌ Error in daily games ingestion: {e}")
            return {"success": False, "error": str(e)}

    async def ingest_team_statistics(self) -> Dict[str, Any]:
        """
        Ingest team statistics for the current season.

        Returns:
            Dictionary with ingestion results
        """
        logger.info("📊 Executing team statistics ingestion")

        try:
            current_season = datetime.now().year

            # Get all teams
            teams = await self.team_repository.list_all()

            stats_count = 0
            for team in teams:
                # Validate team.id is not None before proceeding
                if team.id is None:
                    continue

                # Get team stats from API - correct parameter order: team_id as int, season as str
                stats_data = await self.mlb_api.get_team_stats(team.mlb_id, str(current_season))

                if stats_data:
                    # Create TeamStats entity - remove invalid arguments that are auto-calculated
                    team_stats = TeamStats.create(
                        team_id=team.id,
                        season=current_season,
                        games_played=stats_data.get("games_played", 0),
                        wins=stats_data.get("wins", 0),
                        losses=stats_data.get("losses", 0),
                        runs_scored=stats_data.get("runs_scored", 0),
                        runs_allowed=stats_data.get("runs_allowed", 0),
                        batting_average=stats_data.get("batting_average", 0.0),
                        on_base_percentage=stats_data.get("on_base_percentage", 0.0),
                        slugging_percentage=stats_data.get("slugging_percentage", 0.0),
                        earned_run_average=stats_data.get("earned_run_average", 0.0),
                        ops=stats_data.get("ops", 0.0),
                        # Remove run_differential and pythagorean_expectation - auto-calculated
                    )

                    # Save to repository using the save method instead of create_or_update
                    await self.team_stats_repository.save(team_stats)
                    stats_count += 1

            logger.info(f"✅ Team statistics updated: {stats_count} teams")

            return {"success": True, "teams_updated": stats_count}

        except Exception as e:
            logger.error(f"❌ Error in team statistics ingestion: {e}")
            return {"success": False, "error": str(e)}

    async def retrain_ml_model(self) -> Dict[str, Any]:
        """
        Retrain the ML model with the latest data.

        Returns:
            Dictionary with retraining results
        """
        logger.info("🤖 Executing ML model retraining")

        try:
            # Get historical games with results - use list_by_status instead of get_completed_games
            games = await self.game_repository.list_by_status("completed", limit=1000)

            if len(games) < 50:
                logger.warning("Insufficient historical data for training")
                return {
                    "success": False,
                    "error": "Insufficient historical data for training",
                }

            # Prepare training data
            training_data = []
            for game in games:
                # Get team stats for both teams
                home_team_stats = await self.team_stats_repository.get_by_team_and_season(
                    game.home_team_id, game.game_date.year
                )
                away_team_stats = await self.team_stats_repository.get_by_team_and_season(
                    game.away_team_id, game.game_date.year
                )

                if home_team_stats and away_team_stats:
                    # Create feature dictionary
                    features = self._create_game_features(home_team_stats, away_team_stats, game)

                    # Add target variables
                    features["winner"] = 1 if game.winning_team_id == game.home_team_id else 0
                    features["total_runs"] = (game.home_score or 0) + (game.away_score or 0)

                    training_data.append(features)

            # Train the model
            metrics = await self.ml_model.train(training_data)

            logger.info(f"✅ ML model retrained: {metrics}")

            return {"success": True, "model_updated": True, "metrics": metrics}

        except Exception as e:
            logger.error(f"❌ Error in ML model retraining: {e}")
            return {"success": False, "error": str(e)}

    async def cache_maintenance(self) -> Dict[str, Any]:
        """
        Perform cache maintenance tasks.

        Returns:
            Dictionary with maintenance results
        """
        logger.info("🧹 Executing cache maintenance")

        try:
            # Get cache statistics before maintenance
            stats_before = await self.cache.get_stats()

            # Clear old predictions (older than 7 days)
            cleared_predictions = await self.cache.clear("mlb:prediction:*")

            # Get cache statistics after maintenance
            stats_after = await self.cache.get_stats()

            logger.info("✅ Cache maintenance completed")
            logger.info(f"  - Memory used: {stats_after.get('used_memory', 'N/A')}")
            logger.info(f"  - Hit rate: {stats_after.get('hit_rate', 0)}%")

            return {
                "success": True,
                "cleared_predictions": cleared_predictions,
                "memory_before": stats_before.get("used_memory", "N/A"),
                "memory_after": stats_after.get("used_memory", "N/A"),
                "hit_rate": stats_after.get("hit_rate", 0),
            }

        except Exception as e:
            logger.error(f"❌ Error in cache maintenance: {e}")
            return {"success": False, "error": str(e)}

    async def generate_upcoming_predictions(self) -> Dict[str, Any]:
        """
        Generate predictions for upcoming games.

        Returns:
            Dictionary with prediction results
        """
        logger.info("🔮 Generating predictions for upcoming games")
        return await _generate_upcoming_predictions_impl(
            game_repository=self.game_repository,
            prediction_repository=self.prediction_repository,
            team_stats_repository=self.team_stats_repository,
            ml_model=self.ml_model,
            cache=self.cache,
        )

    async def ingest_teams_weekly(self) -> Dict[str, Any]:
        """
        Ingest team data weekly.

        Returns:
            Dictionary with ingestion results
        """
        logger.info("🏟️ Executing weekly team ingestion")

        try:
            # Get teams from API
            teams_data = await self.mlb_api.get_teams()

            teams_count = 0
            for team_data in teams_data:
                # Create Team entity - ensure mlb_id is an int
                mlb_id = team_data.id
                if mlb_id <= 0:
                    continue

                team = Team.create(
                    mlb_id=mlb_id,
                    name=team_data.name,
                    abbreviation=team_data.abbreviation,
                    city=team_data.city,
                    division=team_data.division,
                    league=team_data.league,
                )

                # Save to repository using save method instead of create_or_update
                await self.team_repository.save(team)
                teams_count += 1

            logger.info(f"✅ Weekly team ingestion completed: {teams_count} teams")

            return {"success": True, "teams_ingested": teams_count}

        except Exception as e:
            logger.error(f"❌ Error in weekly team ingestion: {e}")
            return {"success": False, "error": str(e)}

    async def _ingest_games_for_date(self, date_obj: date) -> List[Game]:
        """
        Ingest games for a specific date.

        Args:
            date_obj: Date to ingest games for

        Returns:
            List of ingested games
        """
        return await _ingest_games_for_date_impl(
            mlb_api=self.mlb_api,
            game_repository=self.game_repository,
            cache=self.cache,
            date_obj=date_obj,
        )

    def _create_game_features(
        self, home_team_stats: Dict[str, Any], away_team_stats: Dict[str, Any], game: Game
    ) -> Dict[str, Any]:
        """
        Create features for game prediction.

        Args:
            home_team_stats: Home team statistics
            away_team_stats: Away team statistics
            game: Game entity

        Returns:
            Dictionary of features
        """
        return _create_game_features_impl(home_team_stats, away_team_stats, game)

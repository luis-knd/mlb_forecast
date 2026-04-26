"""
Main entry point for the MLB Forecast jobs.
This module initializes the jobs and sets up the scheduled tasks.
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Any

import structlog

from application.use_cases.scheduler_use_cases import SchedulerUseCases
from infrastructure.cache.redis_adapter import RedisAdapter
from infrastructure.config.settings import settings
from infrastructure.db.database import SessionLocal
from infrastructure.db.repositories.game_repository import GameRepository
from infrastructure.db.repositories.prediction_repository import PredictionRepository
from infrastructure.db.repositories.team_repository import TeamRepository
from infrastructure.db.repositories.team_stats_repository import TeamStatsRepository
from infrastructure.jobs.scheduler_adapter import SchedulerAdapter
from infrastructure.ml.model_adapter import MLModelAdapter
from infrastructure.mlb_api.adapter import MLBApiAdapter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = structlog.get_logger(__name__)
SCHEDULER_RUNTIME_ERRORS = (RuntimeError, OSError, ValueError, TypeError)


def _build_adapters() -> tuple[RedisAdapter, MLModelAdapter, MLBApiAdapter, SchedulerAdapter]:
    cache_adapter = RedisAdapter()
    ml_model_adapter = MLModelAdapter()
    mlb_api_adapter = MLBApiAdapter()
    scheduler_adapter = SchedulerAdapter()
    return cache_adapter, ml_model_adapter, mlb_api_adapter, scheduler_adapter


def _build_repositories(db_session):
    game_repository = GameRepository(db_session)
    team_repository = TeamRepository(db_session)
    team_stats_repository = TeamStatsRepository(db_session)
    prediction_repository = PredictionRepository(db_session)
    return game_repository, team_repository, team_stats_repository, prediction_repository


async def _load_current_model(ml_model_adapter: MLModelAdapter) -> None:
    try:
        model_path = os.path.join(settings.MODEL_DIR, "current_model.pkl")
        await ml_model_adapter.load_model(model_path)
        logger.info("ML model loaded successfully")
    except SCHEDULER_RUNTIME_ERRORS as e:
        logger.warning(f"Could not load ML model: {e}")


def _ingest_daily_games_job(scheduler_use_cases: SchedulerUseCases) -> dict[str, Any]:
    return {
        "job_id": "ingest_daily_games",
        "func": scheduler_use_cases.ingest_daily_games,
        "trigger_type": "interval",
        "hours": 1,
        "name": "Ingest daily games",
        "max_instances": 1,
        "coalesce": True,
        "misfire_grace_time": 300,
    }


def _ingest_team_statistics_job(scheduler_use_cases: SchedulerUseCases) -> dict[str, Any]:
    return {
        "job_id": "ingest_team_statistics",
        "func": scheduler_use_cases.ingest_team_statistics,
        "trigger_type": "cron",
        "hour": 6,
        "minute": 0,
        "name": "Ingest team statistics",
        "max_instances": 1,
        "coalesce": True,
    }


def _retrain_ml_model_job(scheduler_use_cases: SchedulerUseCases) -> dict[str, Any]:
    return {
        "job_id": "retrain_ml_model",
        "func": scheduler_use_cases.retrain_ml_model,
        "trigger_type": "cron",
        "hour": 3,
        "minute": 0,
        "name": "Retrain ML model",
        "max_instances": 1,
        "coalesce": True,
    }


def _cache_maintenance_job(scheduler_use_cases: SchedulerUseCases) -> dict[str, Any]:
    return {
        "job_id": "cache_maintenance",
        "func": scheduler_use_cases.cache_maintenance,
        "trigger_type": "interval",
        "hours": 4,
        "name": "Cache maintenance",
        "max_instances": 1,
        "coalesce": True,
    }


def _generate_upcoming_predictions_job(scheduler_use_cases: SchedulerUseCases) -> dict[str, Any]:
    return {
        "job_id": "generate_upcoming_predictions",
        "func": scheduler_use_cases.generate_upcoming_predictions,
        "trigger_type": "interval",
        "minutes": 30,
        "name": "Generate upcoming predictions",
        "max_instances": 1,
        "coalesce": True,
    }


def _ingest_teams_weekly_job(scheduler_use_cases: SchedulerUseCases) -> dict[str, Any]:
    return {
        "job_id": "ingest_teams_weekly",
        "func": scheduler_use_cases.ingest_teams_weekly,
        "trigger_type": "cron",
        "day_of_week": 6,
        "hour": 2,
        "minute": 0,
        "name": "Ingest teams weekly",
        "max_instances": 1,
        "coalesce": True,
    }


def _job_definitions(scheduler_use_cases: SchedulerUseCases) -> tuple[dict[str, Any], ...]:
    return (
        _ingest_daily_games_job(scheduler_use_cases),
        _ingest_team_statistics_job(scheduler_use_cases),
        _retrain_ml_model_job(scheduler_use_cases),
        _cache_maintenance_job(scheduler_use_cases),
        _generate_upcoming_predictions_job(scheduler_use_cases),
        _ingest_teams_weekly_job(scheduler_use_cases),
    )


async def _register_jobs(scheduler_adapter: SchedulerAdapter, scheduler_use_cases: SchedulerUseCases) -> None:
    for job_kwargs in _job_definitions(scheduler_use_cases):
        await scheduler_adapter.add_job(**job_kwargs)


async def setup_scheduler():
    """Initialize and set up the jobs with all required tasks."""
    logger.info("🚀 Initializing MLB Forecast Scheduler")
    cache_adapter, ml_model_adapter, mlb_api_adapter, scheduler_adapter = _build_adapters()
    db_session = SessionLocal()
    game_repository, team_repository, team_stats_repository, prediction_repository = _build_repositories(db_session)
    scheduler_use_cases = SchedulerUseCases(
        db_session=db_session,
        cache=cache_adapter,
        ml_model=ml_model_adapter,
        mlb_api=mlb_api_adapter,
        game_repository=game_repository,
        team_repository=team_repository,
        team_stats_repository=team_stats_repository,
        prediction_repository=prediction_repository,
    )
    await cache_adapter.connect()
    await _load_current_model(ml_model_adapter)
    await scheduler_adapter.initialize()
    await _register_jobs(scheduler_adapter, scheduler_use_cases)
    await scheduler_adapter.start()
    logger.info("✅ Scheduler started successfully")
    return scheduler_adapter, cache_adapter


async def main():
    """Main entry point for the jobs."""
    try:
        scheduler_adapter, cache_adapter = await setup_scheduler()

        logger.info("✅ Scheduler running. Press Ctrl+C to stop.")

        # Keep the jobs running
        while True:
            await asyncio.sleep(60)  # Check every minute

            # Log status every hour
            if datetime.now().minute == 0:
                jobs = await scheduler_adapter.get_jobs()
                logger.info(f"📋 Scheduler status: {len(jobs)} active jobs")

    except KeyboardInterrupt:
        logger.info("⏹️ Interrupt received, shutting down...")
    except SCHEDULER_RUNTIME_ERRORS as e:
        logger.error(f"❌ Critical error in jobs: {e}")
    finally:
        # Clean up
        if "scheduler_adapter" in locals():
            await scheduler_adapter.stop()
        if "cache_adapter" in locals():
            await cache_adapter.disconnect()
        logger.info("👋 Scheduler stopped")


if __name__ == "__main__":
    asyncio.run(main())

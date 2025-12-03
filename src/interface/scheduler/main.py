"""
Main entry point for the MLB Forecast jobs.
This module initializes the jobs and sets up the scheduled tasks.
"""

import asyncio
import logging
import os
from datetime import datetime

import structlog

from src.application.use_cases.scheduler_use_cases import SchedulerUseCases
from src.infrastructure.cache.redis_adapter import RedisAdapter
from src.infrastructure.config.settings import settings
from src.infrastructure.db.database import SessionLocal
from src.infrastructure.db.repositories.game_repository import GameRepository
from src.infrastructure.db.repositories.prediction_repository import PredictionRepository
from src.infrastructure.db.repositories.team_repository import TeamRepository
from src.infrastructure.db.repositories.team_stats_repository import TeamStatsRepository
from src.infrastructure.jobs.scheduler_adapter import SchedulerAdapter
from src.infrastructure.ml.model_adapter import MLModelAdapter
from src.infrastructure.mlb_api.adapter import MLBApiAdapter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = structlog.get_logger(__name__)


async def setup_scheduler():
    """Initialize and set up the jobs with all required tasks."""
    logger.info("🚀 Initializing MLB Forecast Scheduler")

    # Initialize adapters
    cache_adapter = RedisAdapter()
    ml_model_adapter = MLModelAdapter()
    mlb_api_adapter = MLBApiAdapter()
    scheduler_adapter = SchedulerAdapter()

    # Initialize repositories
    db_session = SessionLocal()
    game_repository = GameRepository(db_session)
    team_repository = TeamRepository(db_session)
    team_stats_repository = TeamStatsRepository(db_session)
    prediction_repository = PredictionRepository(db_session)

    # Initialize use cases
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

    # Connect to Redis
    await cache_adapter.connect()

    # Initialize ML model
    try:
        model_path = os.path.join(settings.MODEL_DIR, "current_model.pkl")
        await ml_model_adapter.load_model(model_path)
        logger.info("ML model loaded successfully")
    except Exception as e:
        logger.warning(f"Could not load ML model: {e}")

    # Initialize jobs
    await scheduler_adapter.initialize()

    # Set up scheduled tasks

    # 1. Ingest daily games (hourly)
    await scheduler_adapter.add_job(
        job_id="ingest_daily_games",
        func=scheduler_use_cases.ingest_daily_games,
        trigger_type="interval",
        hours=1,
        name="Ingest daily games",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300,  # 5 minutes grace time
    )

    # 2. Ingest team statistics (daily at 6 AM)
    await scheduler_adapter.add_job(
        job_id="ingest_team_statistics",
        func=scheduler_use_cases.ingest_team_statistics,
        trigger_type="cron",
        hour=6,
        minute=0,
        name="Ingest team statistics",
        max_instances=1,
        coalesce=True,
    )

    # 3. Retrain ML model (daily at 3 AM)
    await scheduler_adapter.add_job(
        job_id="retrain_ml_model",
        func=scheduler_use_cases.retrain_ml_model,
        trigger_type="cron",
        hour=3,
        minute=0,
        name="Retrain ML model",
        max_instances=1,
        coalesce=True,
    )

    # 4. Cache maintenance (every 4 hours)
    await scheduler_adapter.add_job(
        job_id="cache_maintenance",
        func=scheduler_use_cases.cache_maintenance,
        trigger_type="interval",
        hours=4,
        name="Cache maintenance",
        max_instances=1,
        coalesce=True,
    )

    # 5. Generate upcoming predictions (every 30 minutes)
    await scheduler_adapter.add_job(
        job_id="generate_upcoming_predictions",
        func=scheduler_use_cases.generate_upcoming_predictions,
        trigger_type="interval",
        minutes=30,
        name="Generate upcoming predictions",
        max_instances=1,
        coalesce=True,
    )

    # 6. Ingest teams weekly (Sunday at 2 AM)
    await scheduler_adapter.add_job(
        job_id="ingest_teams_weekly",
        func=scheduler_use_cases.ingest_teams_weekly,
        trigger_type="cron",
        day_of_week=6,  # Sunday
        hour=2,
        minute=0,
        name="Ingest teams weekly",
        max_instances=1,
        coalesce=True,
    )

    # Start the jobs
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
    except Exception as e:
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

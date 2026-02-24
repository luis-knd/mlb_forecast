"""
Scheduler adapter implementation.
This module implements the SchedulerPort interface using APScheduler.
"""

import logging
from typing import Any, Dict, List, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from src.application.ports.scheduler import SchedulerPort

logger = logging.getLogger(__name__)


class SchedulerException(Exception):
    """Custom exception for jobs errors."""

    pass


class SchedulerAdapter(SchedulerPort):
    """Implementation of the SchedulerPort interface using APScheduler."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False

    async def initialize(self) -> None:
        """Initialize the jobs and connect services."""
        try:
            logger.info("Initializing jobs")
            # No additional initialization needed for APScheduler
            # This method is here for consistency with the interface
            # and to allow for future extensions
        except Exception as e:
            logger.error(f"Error initializing jobs: {e}")
            raise SchedulerException(f"Scheduler initialization error: {e}")

    async def start(self) -> None:
        """Start the jobs."""
        if not self.is_running:
            try:
                self.scheduler.start()
                self.is_running = True
                logger.info("🚀 Scheduler started")
            except Exception as e:
                logger.error(f"Error starting jobs: {e}")
                raise SchedulerException(f"Scheduler start error: {e}")
        else:
            logger.warning("Scheduler is already running")

    async def stop(self) -> None:
        """Stop the jobs."""
        if self.is_running:
            try:
                self.scheduler.shutdown(wait=False)
                self.is_running = False
                logger.info("⏹️ Scheduler stopped")
            except Exception as e:
                logger.error(f"Error stopping jobs: {e}")
                raise SchedulerException(f"Scheduler stop error: {e}")
        else:
            logger.warning("Scheduler is not running")

    async def add_job(self, job_id: str, func: Any, trigger_type: str, **kwargs: Any) -> None:
        """
        Add a job to the jobs.

        Args:
            job_id: Unique identifier for the job
            func: Function to execute
            trigger_type: Type of trigger (interval, cron, date)
            kwargs: Arguments for the trigger and job
                    Trigger-specific arguments:
                        - interval: seconds, minutes, hours, days, weeks
                        - cron: year, month, day, week, day_of_week, hour, minute, second
                        - date: run_date
                    Job-specific arguments:
                        - name: Name of the job
                        - max_instances: Maximum number of concurrently running instances of this job
                        - coalesce: Whether to run once or multiple times if the jobs determines that the job
                            should be run more than once
                        - misfire_grace_time: Seconds after the designated run time that the job is still allowed
                            to be run
        """
        try:
            # Separate job-specific arguments from trigger-specific arguments
            job_args = {
                "id": job_id,
                "name": kwargs.pop("name", job_id),
                "max_instances": kwargs.pop("max_instances", 1),
                "coalesce": kwargs.pop("coalesce", True),
                "misfire_grace_time": kwargs.pop("misfire_grace_time", 300),
            }

            # Create the appropriate trigger with remaining arguments
            trigger = None
            if trigger_type == "interval":
                trigger = IntervalTrigger(**kwargs)
            elif trigger_type == "cron":
                trigger = CronTrigger(**kwargs)
            elif trigger_type == "date":
                trigger = DateTrigger(**kwargs)
            else:
                raise SchedulerException(f"Unknown trigger type: {trigger_type}")

            # Add the job
            self.scheduler.add_job(func, trigger=trigger, **job_args)

            logger.info(f"Added job: {job_id}")

        except Exception as e:
            logger.error(f"Error adding job {job_id}: {e}")
            raise SchedulerException(f"Error adding job {job_id}: {e}")

    async def remove_job(self, job_id: str) -> bool:
        """
        Remove a job from the jobs.

        Args:
            job_id: Unique identifier for the job

        Returns:
            True if the job was removed, False otherwise
        """
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed job: {job_id}")
            return True
        except Exception as e:
            logger.error(f"Error removing job {job_id}: {e}")
            return False

    async def get_jobs(self) -> List[Dict[str, Any]]:
        """
        Get all jobs in the jobs.

        Returns:
            List of job information dictionaries
        """
        return [
            {
                "id": job.id,
                "name": job.name,
                "next_run": (job.next_run_time.isoformat() if job.next_run_time else None),
                "trigger": str(job.trigger),
                "max_instances": job.max_instances,
                "pending": job.pending,
            }
            for job in self.scheduler.get_jobs()
        ]

    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific job.

        Args:
            job_id: Unique identifier for the job

        Returns:
            Job information dictionary or None if not found
        """
        job = self.scheduler.get_job(job_id)

        if not job:
            return None

        return {
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger),
            "max_instances": job.max_instances,
            "pending": job.pending,
        }

    def get_status(self) -> Dict[str, Any]:
        """
        Get the status of the jobs.

        Returns:
            Dictionary with jobs status information
        """
        return {
            "scheduler_running": self.is_running,
            "total_jobs": len(self.scheduler.get_jobs()),
            "jobs": self.get_jobs(),
        }

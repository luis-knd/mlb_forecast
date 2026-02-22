"""
Scheduler port for the MLB Forecast application.
This module defines the interface for scheduling tasks.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class SchedulerPort(ABC):
    """Interface for scheduling tasks."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the jobs and connect services."""
        pass

    @abstractmethod
    async def start(self) -> None:
        """Start the jobs."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the jobs."""
        pass

    @abstractmethod
    async def add_job(
        self,
        job_id: str,
        func: Any,
        trigger_type: str,
        **_trigger_args: Any,
    ) -> None:
        """
        Add a job to the jobs.

        Args:
            job_id: Unique identifier for the job
            func: Function to execute
            trigger_type: Type of trigger (interval, cron, date)
            _trigger_args: Arguments for the trigger
        """
        pass

    @abstractmethod
    async def remove_job(self, job_id: str) -> bool:
        """
        Remove a job from the jobs.

        Args:
            job_id: Unique identifier for the job

        Returns:
            True if the job was removed, False otherwise
        """
        pass

    @abstractmethod
    async def get_jobs(self) -> List[Dict[str, Any]]:
        """
        Get all jobs in the jobs.

        Returns:
            List of job information dictionaries
        """
        pass

    @abstractmethod
    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific job.

        Args:
            job_id: Unique identifier for the job

        Returns:
            Job information dictionary or None if not found
        """
        pass

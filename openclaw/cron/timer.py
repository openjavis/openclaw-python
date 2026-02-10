"""Timer management matching TypeScript openclaw/src/cron/service/timer.ts"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Callable

from .schedule import compute_next_run, is_due

if TYPE_CHECKING:
    from .types import CronJob

logger = logging.getLogger(__name__)

# Maximum timeout for asyncio.sleep (about 24 days)
MAX_TIMEOUT_MS = 2**31 - 1


class CronTimer:
    """
    Timer manager for cron jobs
    
    Features:
    - Single timer for next due job (efficient)
    - Handles long delays
    - Automatic rescheduling
    """
    
    def __init__(self, on_timer_callback: Callable[[list[CronJob]], None]):
        """
        Initialize timer
        
        Args:
            on_timer_callback: Callback function when timer fires
        """
        self.on_timer = on_timer_callback
        self.timer_task: asyncio.Task | None = None
        self.next_fire_ms: int | None = None
        self.running = False
    
    def arm_timer(self, jobs: list[CronJob]) -> None:
        """
        Arm timer for next due job
        
        Args:
            jobs: List of cron jobs
        """
        # Cancel existing timer
        if self.timer_task and not self.timer_task.done():
            self.timer_task.cancel()
            self.timer_task = None
        
        # Find next job to run
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        
        next_job: CronJob | None = None
        next_run_ms: int | None = None
        
        for job in jobs:
            if not job.enabled:
                continue
            
            # Compute next run if not set
            if job.state.next_run_ms is None:
                job.state.next_run_ms = compute_next_run(job.schedule, now_ms)
            
            if job.state.next_run_ms is None:
                continue
            
            # Track earliest next run
            if next_run_ms is None or job.state.next_run_ms < next_run_ms:
                next_run_ms = job.state.next_run_ms
                next_job = job
        
        # If no jobs to run, don't arm timer
        if next_job is None or next_run_ms is None:
            logger.info("No jobs to schedule")
            self.next_fire_ms = None
            return
        
        # Calculate delay
        delay_ms = max(0, next_run_ms - now_ms)
        
        # Clamp to MAX_TIMEOUT_MS
        if delay_ms > MAX_TIMEOUT_MS:
            logger.warning(f"Delay {delay_ms}ms exceeds max, clamping to {MAX_TIMEOUT_MS}ms")
            delay_ms = MAX_TIMEOUT_MS
        
        delay_seconds = delay_ms / 1000
        
        logger.info(f"Arming timer for job '{next_job.name}' ({next_job.id}) in {delay_seconds:.1f}s")
        
        # Store next fire time
        self.next_fire_ms = next_run_ms
        
        # Create timer task
        self.timer_task = asyncio.create_task(self._timer_wait(delay_seconds, jobs))
    
    async def _timer_wait(self, delay_seconds: float, jobs: list[CronJob]) -> None:
        """
        Wait for delay and then fire timer
        
        Args:
            delay_seconds: Delay in seconds
            jobs: List of jobs
        """
        try:
            await asyncio.sleep(delay_seconds)
            
            # Timer fired - find and run due jobs
            logger.info("Timer fired")
            await self._on_timer_fired(jobs)
            
        except asyncio.CancelledError:
            logger.debug("Timer cancelled")
        except Exception as e:
            logger.error(f"Error in timer: {e}", exc_info=True)
    
    async def _on_timer_fired(self, jobs: list[CronJob]) -> None:
        """
        Handle timer firing
        
        Args:
            jobs: List of jobs to check
        """
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        
        # Find all due jobs
        due_jobs: list[CronJob] = []
        
        for job in jobs:
            if not job.enabled:
                continue
            
            if is_due(job.state.next_run_ms, now_ms):
                due_jobs.append(job)
        
        if due_jobs:
            logger.info(f"Running {len(due_jobs)} due jobs")
            
            # Call callback with due jobs
            await self.on_timer(due_jobs)
        
        # Rearm timer for next job
        self.arm_timer(jobs)
    
    def stop(self) -> None:
        """Stop timer"""
        if self.timer_task and not self.timer_task.done():
            self.timer_task.cancel()
            self.timer_task = None
        
        self.next_fire_ms = None
        self.running = False
        
        logger.info("Timer stopped")
    
    def get_status(self) -> dict[str, any]:
        """Get timer status"""
        status = {
            "running": self.timer_task is not None and not self.timer_task.done(),
            "next_fire_ms": self.next_fire_ms,
        }
        
        if self.next_fire_ms:
            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            time_until_ms = self.next_fire_ms - now_ms
            status["time_until_ms"] = max(0, time_until_ms)
            status["time_until_seconds"] = max(0, time_until_ms / 1000)
        
        return status

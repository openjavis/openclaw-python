"""Timer management matching TypeScript openclaw/src/cron/service/timer.ts

Key differences from previous implementation:
- The 'running' flag now lives on CronService (self._timer_running)
- Timer always re-arms after tick (even on error) for resilience
- arm_timer accepts the jobs list directly
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable, Awaitable

from .schedule import compute_next_run, is_due

if TYPE_CHECKING:
    from .types import CronJob

logger = logging.getLogger(__name__)

# Maximum timeout for asyncio.sleep (~24 days)
MAX_TIMEOUT_MS = 2**31 - 1


class CronTimer:
    """
    Timer manager for cron jobs.

    Maintains a single asyncio task that sleeps until the earliest
    nextRunAtMs across all enabled jobs.  When it fires it invokes
    ``on_timer_callback`` with the list of due jobs.
    """

    def __init__(
        self,
        on_timer_callback: Callable[[list[CronJob]], Awaitable[None]],
    ):
        self.on_timer = on_timer_callback
        self.timer_task: asyncio.Task[None] | None = None
        self.next_fire_ms: int | None = None

    # ------------------------------------------------------------------
    # arm / stop
    # ------------------------------------------------------------------
    def arm_timer(self, jobs: list[CronJob]) -> None:
        """Arm (or re-arm) the timer for the next due job."""
        # Cancel existing timer
        if self.timer_task and not self.timer_task.done():
            self.timer_task.cancel()
            self.timer_task = None

        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

        # Find the earliest next_run_ms across enabled, non-running jobs
        next_run_ms: int | None = None
        next_job_name: str | None = None

        for job in jobs:
            if not job.enabled:
                continue
            if job.state.running_at_ms is not None:
                continue

            nxt = job.state.next_run_ms
            if nxt is None:
                # Recompute if missing
                nxt = compute_next_run(job.schedule, now_ms)
                job.state.next_run_ms = nxt

            if nxt is not None and (next_run_ms is None or nxt < next_run_ms):
                next_run_ms = nxt
                next_job_name = job.name or job.id

        if next_run_ms is None:
            self.next_fire_ms = None
            return

        delay_ms = max(0, next_run_ms - now_ms)
        # Clamp to MAX_TIMEOUT_MS to avoid overflow
        if delay_ms > MAX_TIMEOUT_MS:
            delay_ms = MAX_TIMEOUT_MS

        self.next_fire_ms = next_run_ms
        delay_seconds = delay_ms / 1000

        logger.info(
            f"Timer armed for '{next_job_name}' in {delay_seconds:.1f}s"
        )

        self.timer_task = asyncio.create_task(
            self._timer_wait(delay_seconds, jobs)
        )

    def stop(self) -> None:
        """Stop the timer."""
        if self.timer_task and not self.timer_task.done():
            self.timer_task.cancel()
            self.timer_task = None
        self.next_fire_ms = None
        logger.info("Timer stopped")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    async def _timer_wait(
        self, delay_seconds: float, jobs: list[CronJob]
    ) -> None:
        """Sleep then invoke the on_timer callback."""
        try:
            await asyncio.sleep(delay_seconds)
            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

            # Find due jobs
            due_jobs = [
                j
                for j in jobs
                if j.enabled
                and j.state.running_at_ms is None
                and is_due(j.state.next_run_ms, now_ms)
            ]

            if due_jobs:
                logger.info(f"Timer fired: {len(due_jobs)} due jobs")
                await self.on_timer(due_jobs)
            else:
                # No jobs due (perhaps they were updated externally)
                # The service's on_timer will re-arm
                await self.on_timer([])

        except asyncio.CancelledError:
            logger.debug("Timer cancelled")
        except Exception as e:
            logger.error(f"Error in timer: {e}", exc_info=True)

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------
    def get_status(self) -> dict[str, Any]:
        """Get timer status."""
        status: dict[str, Any] = {
            "running": self.timer_task is not None and not self.timer_task.done(),
            "next_fire_ms": self.next_fire_ms,
        }
        if self.next_fire_ms:
            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            time_until_ms = self.next_fire_ms - now_ms
            status["time_until_ms"] = max(0, time_until_ms)
            status["time_until_seconds"] = max(0, time_until_ms / 1000)
        return status

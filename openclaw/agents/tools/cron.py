"""Cron job management tool using APScheduler"""

import logging
from datetime import UTC, datetime
from typing import Any

from .base import AgentTool, ToolResult

logger = logging.getLogger(__name__)


class CronTool(AgentTool):
    """Scheduled task management using APScheduler"""

    def __init__(self):
        super().__init__()
        self.name = "cron"
        self.description = "Manage scheduled tasks and reminders"
        self._scheduler = None
        self._jobs: dict[str, Any] = {}

    def _init_scheduler(self):
        """Initialize scheduler"""
        if self._scheduler is not None:
            return

        try:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler

            self._scheduler = AsyncIOScheduler()
            self._scheduler.start()
            logger.info("Cron scheduler initialized")

        except ImportError:
            raise ImportError("APScheduler not installed. Install with: pip install apscheduler")

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["add", "list", "remove", "status", "update", "run"],
                    "description": "Cron action to perform",
                },
                "job_id": {"type": "string", "description": "Job identifier"},
                "schedule": {
                    "type": "string",
                    "description": "Schedule in cron format or natural language (e.g., 'daily at 9am', '0 9 * * *')",
                },
                "task": {"type": "string", "description": "Task description or command to execute"},
                "message": {"type": "string", "description": "Message to send when job runs"},
                "session_id": {
                    "type": "string",
                    "description": "Target session for notifications",
                    "default": "main",
                },
            },
            "required": ["action"],
        }

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        """Execute cron action"""
        action = params.get("action", "")

        if not action:
            return ToolResult(success=False, content="", error="action required")

        try:
            self._init_scheduler()

            if action == "add":
                return await self._add_job(params)
            elif action == "list":
                return await self._list_jobs(params)
            elif action == "remove":
                return await self._remove_job(params)
            elif action == "status":
                return await self._job_status(params)
            elif action == "update":
                return await self._update_job(params)
            elif action == "run":
                return await self._run_job(params)
            else:
                return ToolResult(success=False, content="", error=f"Unknown action: {action}")

        except ImportError as e:
            return ToolResult(success=False, content="", error=str(e))
        except Exception as e:
            logger.error(f"Cron tool error: {e}", exc_info=True)
            return ToolResult(success=False, content="", error=str(e))

    async def _add_job(self, params: dict[str, Any]) -> ToolResult:
        """Add scheduled job"""
        job_id = params.get("job_id") or f"job-{int(datetime.now(UTC).timestamp())}"
        schedule = params.get("schedule", "")
        task = params.get("task", "")
        message = params.get("message", "")
        session_id = params.get("session_id", "main")

        if not schedule or not (task or message):
            return ToolResult(
                success=False, content="", error="schedule and (task or message) required"
            )

        # Parse schedule
        trigger_kwargs = self._parse_schedule(schedule)

        if not trigger_kwargs:
            return ToolResult(
                success=False, content="", error=f"Invalid schedule format: {schedule}"
            )

        # Add job to scheduler
        self._scheduler.add_job(
            self._job_callback,
            **trigger_kwargs,
            id=job_id,
            kwargs={"job_id": job_id, "task": task, "message": message, "session_id": session_id},
        )

        # Store job info
        self._jobs[job_id] = {
            "id": job_id,
            "schedule": schedule,
            "task": task,
            "message": message,
            "session_id": session_id,
            "created": datetime.now(UTC).isoformat(),
            "runs": 0,
        }

        return ToolResult(
            success=True,
            content=f"Created job '{job_id}' with schedule '{schedule}'",
            metadata={"job_id": job_id},
        )

    def _parse_schedule(self, schedule: str) -> dict | None:
        """Parse schedule string to APScheduler trigger kwargs"""
        from apscheduler.triggers.cron import CronTrigger
        from apscheduler.triggers.interval import IntervalTrigger

        # Try cron format
        if any(c in schedule for c in ["*", ","]):
            try:
                parts = schedule.split()
                if len(parts) == 5:
                    minute, hour, day, month, day_of_week = parts
                    return {
                        "trigger": CronTrigger(
                            minute=minute, hour=hour, day=day, month=month, day_of_week=day_of_week
                        )
                    }
            except:
                pass

        # Natural language patterns
        schedule_lower = schedule.lower()

        if "every" in schedule_lower:
            # Extract interval
            if "minute" in schedule_lower:
                return {"trigger": IntervalTrigger(minutes=1)}
            elif "hour" in schedule_lower:
                return {"trigger": IntervalTrigger(hours=1)}
            elif "day" in schedule_lower:
                return {"trigger": IntervalTrigger(days=1)}

        if "daily" in schedule_lower or "every day" in schedule_lower:
            # Extract time if present
            import re

            time_match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", schedule_lower)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2)) if time_match.group(2) else 0
                am_pm = time_match.group(3)

                if am_pm == "pm" and hour < 12:
                    hour += 12
                elif am_pm == "am" and hour == 12:
                    hour = 0

                return {"trigger": CronTrigger(hour=hour, minute=minute)}

            return {"trigger": CronTrigger(hour=9, minute=0)}  # Default to 9am

        return None

    async def _job_callback(self, job_id: str, task: str, message: str, session_id: str):
        """Job execution callback"""
        logger.info(f"Executing job '{job_id}': {task or message}")

        # Update run count
        if job_id in self._jobs:
            self._jobs[job_id]["runs"] += 1
            self._jobs[job_id]["last_run"] = datetime.now(UTC).isoformat()

        # TODO: Integrate with session manager to send notifications
        # For now, just log
        logger.info(f"Job '{job_id}' notification: {message}")

    async def _list_jobs(self, params: dict[str, Any]) -> ToolResult:
        """List all jobs"""
        if not self._jobs:
            return ToolResult(success=True, content="No scheduled jobs", metadata={"count": 0})

        output = f"Scheduled jobs ({len(self._jobs)}):\n\n"
        for job_id, job_info in self._jobs.items():
            output += f"- **{job_id}**\n"
            output += f"  Schedule: {job_info['schedule']}\n"
            output += f"  Task: {job_info.get('task', 'N/A')}\n"
            output += f"  Runs: {job_info['runs']}\n"
            if "last_run" in job_info:
                output += f"  Last run: {job_info['last_run']}\n"
            output += "\n"

        return ToolResult(
            success=True,
            content=output,
            metadata={"count": len(self._jobs), "jobs": list(self._jobs.values())},
        )

    async def _remove_job(self, params: dict[str, Any]) -> ToolResult:
        """Remove job"""
        job_id = params.get("job_id", "")

        if not job_id:
            return ToolResult(success=False, content="", error="job_id required")

        if job_id not in self._jobs:
            return ToolResult(success=False, content="", error=f"Job '{job_id}' not found")

        # Remove from scheduler
        self._scheduler.remove_job(job_id)

        # Remove from our tracking
        del self._jobs[job_id]

        return ToolResult(success=True, content=f"Removed job '{job_id}'")

    async def _job_status(self, params: dict[str, Any]) -> ToolResult:
        """Get job status"""
        job_id = params.get("job_id", "")

        if not job_id:
            # Return overall status
            return ToolResult(
                success=True,
                content=f"Scheduler running with {len(self._jobs)} jobs",
                metadata={"running": self._scheduler.running, "job_count": len(self._jobs)},
            )

        if job_id not in self._jobs:
            return ToolResult(success=False, content="", error=f"Job '{job_id}' not found")

        job_info = self._jobs[job_id]
        output = f"Job '{job_id}':\n"
        output += f"  Schedule: {job_info['schedule']}\n"
        output += f"  Task: {job_info.get('task', 'N/A')}\n"
        output += f"  Runs: {job_info['runs']}\n"
        if "last_run" in job_info:
            output += f"  Last run: {job_info['last_run']}\n"

        return ToolResult(success=True, content=output, metadata=job_info)

    async def _update_job(self, params: dict[str, Any]) -> ToolResult:
        """Update job"""
        job_id = params.get("job_id", "")
        schedule = params.get("schedule")

        if not job_id:
            return ToolResult(success=False, content="", error="job_id required")

        if job_id not in self._jobs:
            return ToolResult(success=False, content="", error=f"Job '{job_id}' not found")

        # For now, just update the schedule if provided
        if schedule:
            trigger_kwargs = self._parse_schedule(schedule)
            if trigger_kwargs:
                self._scheduler.reschedule_job(job_id, **trigger_kwargs)
                self._jobs[job_id]["schedule"] = schedule

        return ToolResult(success=True, content=f"Updated job '{job_id}'")

    async def _run_job(self, params: dict[str, Any]) -> ToolResult:
        """Run job immediately"""
        job_id = params.get("job_id", "")

        if not job_id:
            return ToolResult(success=False, content="", error="job_id required")

        if job_id not in self._jobs:
            return ToolResult(success=False, content="", error=f"Job '{job_id}' not found")

        # Get job and run it
        job = self._scheduler.get_job(job_id)
        if job:
            job.modify(next_run_time=datetime.now())

        return ToolResult(success=True, content=f"Triggered job '{job_id}'")

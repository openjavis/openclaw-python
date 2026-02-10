"""Cron service matching TypeScript openclaw/src/cron/service.ts"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .schedule import compute_next_run
from .store import CronRunLog, CronStore
from .timer import CronTimer
from .types import (
    AgentTurnPayload,
    AtSchedule,
    CronJob,
    CronSchedule,
    CronScheduleType,
    EverySchedule,
    SystemEventPayload,
)

logger = logging.getLogger(__name__)


class CronService:
    """
    Cron service for managing scheduled tasks
    
    Features:
    - CRUD operations (add, update, remove, list, run)
    - Multiple schedule types (at, every, cron)
    - Main session and isolated agent execution
    - Run logging
    - Event broadcasting
    """
    
    def __init__(
        self,
        store_path: Path,
        log_dir: Path,
        on_system_event: Callable[[str], None] | None = None,
        on_isolated_agent: Callable[[CronJob], Any] | None = None,
        on_event: Callable[[str, dict[str, Any]], None] | None = None,
    ):
        """
        Initialize cron service
        
        Args:
            store_path: Path to jobs.json
            log_dir: Directory for run logs
            on_system_event: Callback for system events (main session)
            on_isolated_agent: Callback for isolated agent execution
            on_event: Event broadcast callback
        """
        self.store_path = store_path
        self.log_dir = log_dir
        
        # Callbacks
        self.on_system_event = on_system_event
        self.on_isolated_agent = on_isolated_agent
        self.on_event = on_event
        
        # Storage
        self.store = CronStore(store_path)
        self.jobs: dict[str, CronJob] = {}
        
        # Timer
        self.timer = CronTimer(self._execute_due_jobs)
        
        # Load jobs
        self._load_jobs()
    
    def _load_jobs(self) -> None:
        """Load jobs from store"""
        try:
            # Migrate store if needed
            self.store.migrate_if_needed()
            
            # Load jobs
            jobs = self.store.load()
            self.jobs = {job.id: job for job in jobs}
            
            logger.info(f"Loaded {len(self.jobs)} cron jobs")
            
            # Clear stuck running markers (jobs running for >2 hours are stuck)
            self._clear_stuck_jobs()
            
        except Exception as e:
            logger.error(f"Error loading jobs: {e}", exc_info=True)
    
    def _clear_stuck_jobs(self) -> None:
        """Clear stuck running markers"""
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        stuck_threshold_ms = 2 * 60 * 60 * 1000  # 2 hours
        
        for job in self.jobs.values():
            if job.state.running_at_ms:
                running_duration_ms = now_ms - job.state.running_at_ms
                
                if running_duration_ms > stuck_threshold_ms:
                    logger.warning(f"Clearing stuck job: {job.name} ({job.id})")
                    job.state.running_at_ms = None
                    job.state.last_status = "error"
                    job.state.last_error = "Job was stuck"
        
        # Save if any were cleared
        self._save_jobs()
    
    def _save_jobs(self) -> None:
        """Save jobs to store"""
        try:
            jobs = list(self.jobs.values())
            self.store.save(jobs)
        except Exception as e:
            logger.error(f"Error saving jobs: {e}", exc_info=True)
    
    def _broadcast_event(self, event_type: str, payload: dict[str, Any]) -> None:
        """Broadcast event"""
        if self.on_event:
            try:
                self.on_event(event_type, payload)
            except Exception as e:
                logger.error(f"Error broadcasting event: {e}", exc_info=True)
    
    def start(self) -> None:
        """Start cron service"""
        logger.info("Starting cron service")
        
        # Arm timer for next job
        self.timer.arm_timer(list(self.jobs.values()))
        
        self.timer.running = True
        
        logger.info("Cron service started")
    
    def stop(self) -> None:
        """Stop cron service"""
        logger.info("Stopping cron service")
        
        self.timer.stop()
        
        logger.info("Cron service stopped")
    
    def add(
        self,
        name: str,
        schedule: CronScheduleType,
        payload: SystemEventPayload | AgentTurnPayload,
        job_id: str | None = None,
        **kwargs,
    ) -> CronJob:
        """
        Add cron job
        
        Args:
            name: Job name
            schedule: Schedule configuration
            payload: Job payload
            job_id: Optional job ID (generated if not provided)
            **kwargs: Additional job parameters
            
        Returns:
            Created job
        """
        # Generate ID if not provided
        if job_id is None:
            job_id = str(uuid.uuid4())
        
        # Check for duplicate
        if job_id in self.jobs:
            raise ValueError(f"Job with ID {job_id} already exists")
        
        # Compute next run
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        next_run_ms = compute_next_run(schedule, now_ms)
        
        # Create job
        job = CronJob(
            id=job_id,
            name=name,
            schedule=schedule,
            payload=payload,
            **kwargs
        )
        
        job.state.next_run_ms = next_run_ms
        
        # Add to jobs
        self.jobs[job_id] = job
        
        # Save
        self._save_jobs()
        
        # Broadcast event
        self._broadcast_event("cron_job_added", {"job_id": job_id, "name": name})
        
        # Rearm timer
        self.timer.arm_timer(list(self.jobs.values()))
        
        logger.info(f"Added cron job: {name} ({job_id})")
        
        return job
    
    def update(self, job_id: str, **updates) -> CronJob:
        """
        Update cron job
        
        Args:
            job_id: Job ID
            **updates: Fields to update
            
        Returns:
            Updated job
        """
        if job_id not in self.jobs:
            raise ValueError(f"Job {job_id} not found")
        
        job = self.jobs[job_id]
        
        # Update fields
        for key, value in updates.items():
            if hasattr(job, key):
                setattr(job, key, value)
        
        # Update timestamp
        job.updated_at_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        
        # Recompute next run if schedule changed
        if "schedule" in updates:
            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            job.state.next_run_ms = compute_next_run(job.schedule, now_ms)
        
        # Save
        self._save_jobs()
        
        # Broadcast event
        self._broadcast_event("cron_job_updated", {"job_id": job_id})
        
        # Rearm timer
        self.timer.arm_timer(list(self.jobs.values()))
        
        logger.info(f"Updated cron job: {job.name} ({job_id})")
        
        return job
    
    def remove(self, job_id: str) -> None:
        """
        Remove cron job
        
        Args:
            job_id: Job ID
        """
        if job_id not in self.jobs:
            raise ValueError(f"Job {job_id} not found")
        
        job = self.jobs[job_id]
        
        # Remove from jobs
        del self.jobs[job_id]
        
        # Save
        self._save_jobs()
        
        # Broadcast event
        self._broadcast_event("cron_job_removed", {"job_id": job_id})
        
        # Rearm timer
        self.timer.arm_timer(list(self.jobs.values()))
        
        logger.info(f"Removed cron job: {job.name} ({job_id})")
    
    def get(self, job_id: str) -> CronJob | None:
        """Get job by ID"""
        return self.jobs.get(job_id)
    
    def list(self, enabled_only: bool = False) -> list[CronJob]:
        """
        List cron jobs
        
        Args:
            enabled_only: Only return enabled jobs
            
        Returns:
            List of jobs
        """
        jobs = list(self.jobs.values())
        
        if enabled_only:
            jobs = [j for j in jobs if j.enabled]
        
        # Sort by next run time
        jobs.sort(key=lambda j: j.state.next_run_ms or float("inf"))
        
        return jobs
    
    async def run_now(self, job_id: str) -> None:
        """
        Run job immediately
        
        Args:
            job_id: Job ID
        """
        if job_id not in self.jobs:
            raise ValueError(f"Job {job_id} not found")
        
        job = self.jobs[job_id]
        
        logger.info(f"Running job immediately: {job.name} ({job_id})")
        
        await self._execute_job(job)
    
    async def _execute_due_jobs(self, jobs: list[CronJob]) -> None:
        """
        Execute due jobs
        
        Args:
            jobs: List of due jobs
        """
        for job in jobs:
            await self._execute_job(job)
    
    async def _execute_job(self, job: CronJob) -> None:
        """
        Execute single job
        
        Args:
            job: Job to execute
        """
        logger.info(f"Executing job: {job.name} ({job.id})")
        
        # Mark as running
        start_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        job.state.running_at_ms = start_ms
        
        # Broadcast event
        self._broadcast_event("cron_job_started", {
            "job_id": job.id,
            "name": job.name,
            "started_at_ms": start_ms
        })
        
        # Create run log
        run_log = CronRunLog(self.log_dir, job.id)
        
        try:
            # Execute based on session target
            if job.session_target == "main":
                await self._execute_main_session_job(job)
            elif job.session_target == "isolated":
                await self._execute_isolated_job(job)
            else:
                raise ValueError(f"Unknown session target: {job.session_target}")
            
            # Success
            end_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            duration_ms = end_ms - start_ms
            
            job.state.running_at_ms = None
            job.state.last_run_at_ms = start_ms
            job.state.last_status = "success"
            job.state.last_error = None
            job.state.last_duration_ms = duration_ms
            
            # Log run
            run_log.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "success",
                "duration_ms": duration_ms
            })
            
            # Broadcast event
            self._broadcast_event("cron_job_finished", {
                "job_id": job.id,
                "name": job.name,
                "status": "success",
                "duration_ms": duration_ms
            })
            
            logger.info(f"Job completed: {job.name} ({job.id}) in {duration_ms}ms")
            
        except Exception as e:
            # Error
            end_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            duration_ms = end_ms - start_ms
            error_msg = str(e)
            
            job.state.running_at_ms = None
            job.state.last_run_at_ms = start_ms
            job.state.last_status = "error"
            job.state.last_error = error_msg
            job.state.last_duration_ms = duration_ms
            
            # Log run
            run_log.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "error",
                "error": error_msg,
                "duration_ms": duration_ms
            })
            
            # Broadcast event
            self._broadcast_event("cron_job_finished", {
                "job_id": job.id,
                "name": job.name,
                "status": "error",
                "error": error_msg,
                "duration_ms": duration_ms
            })
            
            logger.error(f"Job failed: {job.name} ({job.id}): {error_msg}", exc_info=True)
        
        finally:
            # Compute next run
            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            
            # For 'at' schedules with delete_after_run, disable job
            if isinstance(job.schedule, AtSchedule) and job.delete_after_run:
                logger.info(f"Deleting one-shot job: {job.name} ({job.id})")
                self.remove(job.id)
            else:
                # Compute next run
                job.state.next_run_ms = compute_next_run(job.schedule, now_ms)
                
                # Save
                self._save_jobs()
    
    async def _execute_main_session_job(self, job: CronJob) -> None:
        """Execute main session job"""
        if not isinstance(job.payload, SystemEventPayload):
            raise ValueError(f"Main session job must have systemEvent payload")
        
        if not job.payload.text:
            raise ValueError(f"System event text is empty")
        
        # Enqueue system event
        if self.on_system_event:
            await self.on_system_event(job.payload.text)
        else:
            logger.warning("No system event handler configured")
    
    async def _execute_isolated_job(self, job: CronJob) -> None:
        """Execute isolated agent job"""
        if not isinstance(job.payload, AgentTurnPayload):
            raise ValueError(f"Isolated job must have agentTurn payload")
        
        # Run isolated agent
        if self.on_isolated_agent:
            await self.on_isolated_agent(job)
        else:
            logger.warning("No isolated agent handler configured")
    
    def get_status(self) -> dict[str, Any]:
        """Get service status"""
        return {
            "running": self.timer.running,
            "job_count": len(self.jobs),
            "enabled_job_count": len([j for j in self.jobs.values() if j.enabled]),
            "timer_status": self.timer.get_status(),
        }

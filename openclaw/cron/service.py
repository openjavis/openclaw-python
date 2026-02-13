"""
Cron job scheduling service - Complete AI-driven intelligent scheduled task system

Provides scheduled task features fully aligned with the TypeScript version:
- Three scheduling types (at/every/cron)
- Isolated Agent execution (intelligent tasks)
- System events (simple notifications)
- Persistent storage
- Run logs
- Auto delivery
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Dict, Callable, Awaitable, Union

from .types import (
    CronJob,
    AgentTurnPayload,
    SystemEventPayload,
    CronJobState
)
from .schedule import compute_next_run
from .timer import CronTimer
from .store import CronStore, CronRunLog

logger = logging.getLogger(__name__)


class CronService:
    """
    Complete Cron scheduling service
    
    Features:
    - Three scheduling types (at/every/cron)
    - Isolated Agent execution (intelligent tasks)
    - System events (simple notifications)
    - Persistent storage
    - Run logs
    - Auto delivery
    """
    
    def __init__(
        self,
        store_path: Optional[Path] = None,
        log_dir: Optional[Path] = None,
        on_system_event: Optional[Callable[[str, Optional[str]], Awaitable[None]]] = None,
        on_isolated_agent: Optional[Callable[[CronJob], Awaitable[Dict[str, Any]]]] = None,
        on_event: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        """
        Initialize Cron service
        
        Args:
            store_path: Job storage path
            log_dir: Run log directory
            on_system_event: System event callback (text, agent_id)
            on_isolated_agent: Isolated Agent execution callback (job) -> result
            on_event: Event broadcast callback (event)
        """
        self.jobs: Dict[str, CronJob] = {}
        self._running = False
        
        # Configuration
        self.store_path = store_path
        self.log_dir = log_dir
        self.on_system_event = on_system_event
        self.on_isolated_agent = on_isolated_agent
        self.on_event = on_event
        
        # Storage and logging
        self._store: Optional[CronStore] = None
        if store_path:
            self._store = CronStore(store_path)
        
        # Timer
        self._timer: Optional[CronTimer] = None
        
        logger.info("CronService initialized")
    
    def start(self) -> None:
        """Start Cron service"""
        if self._running:
            logger.warning("CronService already running")
            return
        
        self._running = True
        
        # Create and start timer
        self._timer = CronTimer(on_timer_callback=self._on_timer_fired)
        self._timer.arm_timer(list(self.jobs.values()))
        
        logger.info(f"✅ CronService started with {len(self.jobs)} jobs")
        self._broadcast_event({
            "action": "service-started",
            "job_count": len(self.jobs),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    
    def stop(self) -> None:
        """Stop Cron service"""
        if not self._running:
            return
        
        self._running = False
        
        if self._timer:
            self._timer.stop()
            self._timer = None
        
        logger.info("CronService stopped")
        self._broadcast_event({
            "action": "service-stopped",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    
    # Compatibility with old API name
    def shutdown(self) -> None:
        """Stop service (compatible with old API)"""
        self.stop()
    
    def add_job(self, job: CronJob) -> bool:
        """
        Add scheduled task
        
        Args:
            job: Task definition
            
        Returns:
            True if successful
        """
        try:
            # Calculate first run time
            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            
            if job.state.next_run_ms is None:
                job.state.next_run_ms = compute_next_run(job.schedule, now_ms)
            
            # Add to memory
            self.jobs[job.id] = job
            
            # Persist
            if self._store:
                self._store.save(list(self.jobs.values()))
            
            # Reschedule timer
            if self._timer and self._running:
                self._timer.arm_timer(list(self.jobs.values()))
            
            logger.info(f"✅ Added cron job: {job.name} (id={job.id})")
            self._broadcast_event({
                "action": "job-added",
                "jobId": job.id,
                "jobName": job.name,
                "nextRun": job.state.next_run_ms,
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add job {job.id}: {e}", exc_info=True)
            return False
    
    def update_job(self, job: CronJob) -> bool:
        """
        Update task
        
        Args:
            job: Updated task definition
            
        Returns:
            True if successful
        """
        try:
            if job.id not in self.jobs:
                logger.error(f"Job {job.id} not found")
                return False
            
            # Recalculate next_run
            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            job.state.next_run_ms = compute_next_run(job.schedule, now_ms)
            
            # Update
            self.jobs[job.id] = job
            
            # Persist
            if self._store:
                self._store.save(list(self.jobs.values()))
            
            # Reschedule
            if self._timer and self._running:
                self._timer.arm_timer(list(self.jobs.values()))
            
            logger.info(f"✅ Updated job: {job.id}")
            self._broadcast_event({
                "action": "job-updated",
                "jobId": job.id,
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update job {job.id}: {e}", exc_info=True)
            return False
    
    def remove_job(self, job_id: str) -> bool:
        """
        Delete task
        
        Args:
            job_id: Task ID
            
        Returns:
            True if successful
        """
        try:
            if job_id not in self.jobs:
                logger.error(f"Job {job_id} not found")
                return False
            
            # Delete
            job = self.jobs.pop(job_id)
            
            # Persist
            if self._store:
                self._store.save(list(self.jobs.values()))
            
            # Reschedule
            if self._timer and self._running:
                self._timer.arm_timer(list(self.jobs.values()))
            
            logger.info(f"✅ Removed job: {job_id}")
            self._broadcast_event({
                "action": "job-removed",
                "jobId": job_id,
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove job {job_id}: {e}", exc_info=True)
            return False
    
    def list_jobs(self, include_disabled: bool = False) -> list[Dict[str, Any]]:
        """
        List all tasks
        
        Args:
            include_disabled: Whether to include disabled tasks
            
        Returns:
            Task list
        """
        jobs = list(self.jobs.values())
        
        if not include_disabled:
            jobs = [j for j in jobs if j.enabled]
        
        return [self._job_to_dict(job) for job in jobs]
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task status
        
        Args:
            job_id: Task ID
            
        Returns:
            Task status dictionary, None if not exists
        """
        job = self.jobs.get(job_id)
        if not job:
            return None
        
        return self._job_to_dict(job)
    
    # Compatibility with old API name
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status (alias for get_job_status)"""
        return self.get_job_status(job_id)
    
    async def run_job_now(self, job_id: str) -> Dict[str, Any]:
        """
        Run task immediately
        
        Args:
            job_id: Task ID
            
        Returns:
            Execution result
        """
        job = self.jobs.get(job_id)
        if not job:
            return {
                "success": False,
                "error": f"Job {job_id} not found"
            }
        
        logger.info(f"🚀 Running job immediately: {job.name} (id={job_id})")
        
        result = await self._execute_job(job)
        
        return result
    
    async def _on_timer_fired(self, due_jobs: list[CronJob]) -> None:
        """
        Timer fired - Execute all due tasks
        
        Args:
            due_jobs: List of due tasks
        """
        logger.info(f"⏰ Timer fired: {len(due_jobs)} due jobs")
        
        for job in due_jobs:
            if not job.enabled:
                continue
            
            try:
                await self._execute_job(job)
            except Exception as e:
                logger.error(f"Error executing job {job.id}: {e}", exc_info=True)
    
    async def _execute_job(self, job: CronJob) -> Dict[str, Any]:
        """
        Execute task
        
        Args:
            job: Task to execute
            
        Returns:
            Execution result
        """
        if not job.enabled:
            logger.debug(f"Job {job.id} is disabled, skipping")
            return {"success": False, "error": "Job disabled"}
        
        # Update status
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        job.state.running_at_ms = now_ms
        
        # Broadcast start event
        self._broadcast_event({
            "action": "job-started",
            "jobId": job.id,
            "jobName": job.name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        
        start_time = datetime.now(timezone.utc)
        result: Dict[str, Any] = {"success": False}
        
        try:
            # Execute based on payload type
            if isinstance(job.payload, SystemEventPayload):
                result = await self._execute_system_event(job)
            elif isinstance(job.payload, AgentTurnPayload):
                result = await self._execute_agent_turn(job)
            else:
                raise ValueError(f"Unknown payload type: {type(job.payload)}")
            
            # Update status
            job.state.last_run_at_ms = now_ms
            job.state.last_status = "success" if result.get("success") else "error"
            job.state.last_error = result.get("error")
            
        except Exception as e:
            logger.error(f"Job {job.id} execution error: {e}", exc_info=True)
            result = {
                "success": False,
                "error": str(e)
            }
            job.state.last_status = "error"
            job.state.last_error = str(e)
        
        finally:
            # Calculate duration
            duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            job.state.last_duration_ms = duration_ms
            job.state.running_at_ms = None
            
            # Calculate next run time
            if not job.delete_after_run:
                job.state.next_run_ms = compute_next_run(
                    job.schedule,
                    int(datetime.now(timezone.utc).timestamp() * 1000)
                )
            else:
                # One-shot task, delete after execution
                logger.info(f"Job {job.id} is one-shot, removing after execution")
                self.remove_job(job.id)
                return result  # Early exit because job is deleted
            
            # Persist status
            if self._store and job.id in self.jobs:
                self._store.save(list(self.jobs.values()))
            
            # Record run log
            if self.log_dir:
                try:
                    run_log = CronRunLog(self.log_dir, job.id)
                    run_log.append({
                        "timestamp": start_time.isoformat(),
                        "duration_ms": duration_ms,
                        "status": job.state.last_status,
                        "error": job.state.last_error,
                        "summary": result.get("summary"),
                    })
                except Exception as e:
                    logger.warning(f"Failed to write run log: {e}")
            
            # Broadcast completion event
            self._broadcast_event({
                "action": "job-finished",
                "jobId": job.id,
                "jobName": job.name,
                "status": job.state.last_status,
                "durationMs": duration_ms,
                "error": job.state.last_error,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        
        return result
    
    async def _execute_system_event(self, job: CronJob) -> Dict[str, Any]:
        """
        Execute system event
        
        Args:
            job: Task
            
        Returns:
            Execution result
        """
        payload = job.payload
        if not isinstance(payload, SystemEventPayload):
            return {"success": False, "error": "Invalid payload type"}
        
        if not payload.text:
            logger.warning(f"Job {job.id} has empty systemEvent text, skipping")
            return {"success": False, "error": "Empty system event text"}
        
        logger.info(f"📨 Executing systemEvent for job {job.name}")
        
        try:
            if self.on_system_event:
                await self.on_system_event(payload.text, job.agent_id)
                return {
                    "success": True,
                    "summary": payload.text,
                }
            else:
                logger.warning("on_system_event callback not configured")
                return {
                    "success": False,
                    "error": "System event callback not configured"
                }
                
        except Exception as e:
            logger.error(f"System event execution error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _execute_agent_turn(self, job: CronJob) -> Dict[str, Any]:
        """
        Execute Agent turn (intelligent task)
        
        Args:
            job: Task
            
        Returns:
            Execution result {success, summary, full_response, session_key, model, ...}
        """
        payload = job.payload
        if not isinstance(payload, AgentTurnPayload):
            return {"success": False, "error": "Invalid payload type"}
        
        if not payload.prompt:
            logger.warning(f"Job {job.id} has empty agentTurn prompt, skipping")
            return {"success": False, "error": "Empty prompt"}
        
        logger.info(f"🤖 Executing agentTurn for job {job.name}")
        logger.info(f"   Prompt: {payload.prompt[:100]}...")
        
        try:
            if self.on_isolated_agent:
                # Call isolated Agent execution
                result = await self.on_isolated_agent(job)
                
                logger.info(f"✅ Agent turn completed: {result.get('success')}")
                if result.get("summary"):
                    logger.info(f"   Summary: {result['summary'][:100]}...")
                
                return result
            else:
                logger.error("on_isolated_agent callback not configured")
                return {
                    "success": False,
                    "error": "Isolated agent callback not configured"
                }
                
        except Exception as e:
            logger.error(f"Agent turn execution error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _job_to_dict(self, job: CronJob) -> Dict[str, Any]:
        """Convert Job to dictionary"""
        result = job.to_dict()
        
        # Add runtime information
        if job.state.next_run_ms:
            result["nextRun"] = datetime.fromtimestamp(
                job.state.next_run_ms / 1000, 
                tz=timezone.utc
            ).isoformat()
        
        if job.state.last_run_at_ms:
            result["lastRun"] = datetime.fromtimestamp(
                job.state.last_run_at_ms / 1000,
                tz=timezone.utc
            ).isoformat()
        
        result["running"] = job.state.running_at_ms is not None
        
        return result
    
    def _broadcast_event(self, event: Dict[str, Any]) -> None:
        """Broadcast event"""
        try:
            if self.on_event:
                self.on_event(event)
        except Exception as e:
            logger.error(f"Error broadcasting event: {e}", exc_info=True)


# Global singleton
_cron_service: Optional[CronService] = None


def get_cron_service() -> CronService:
    """Get global CronService instance"""
    global _cron_service
    if _cron_service is None:
        _cron_service = CronService()
    return _cron_service


def set_cron_service(service: CronService) -> None:
    """Set global CronService instance"""
    global _cron_service
    _cron_service = service

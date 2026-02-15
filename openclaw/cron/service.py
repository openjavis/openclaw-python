"""
Cron job scheduling service - aligned with TypeScript openclaw/src/cron/service/ops.ts

All operations are serialized via asyncio.Lock to prevent races,
matching the TypeScript locked() pattern.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Awaitable, Dict, Literal, Optional

from .types import (
    CronJob,
    AgentTurnPayload,
    SystemEventPayload,
    CronJobState,
)
from .schedule import compute_next_run
from .timer import CronTimer
from .store import CronStore, CronRunLog

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CronEvent type (mirrors TypeScript CronEvent)
# ---------------------------------------------------------------------------

CronEventAction = Literal["added", "updated", "removed", "started", "finished"]


class CronEvent(dict):
    """Structured cron event matching TypeScript CronEvent."""
    pass


def _make_event(**kwargs: Any) -> CronEvent:
    return CronEvent({k: v for k, v in kwargs.items() if v is not None})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _next_wake_at_ms(jobs: list[CronJob]) -> int | None:
    """Find earliest nextRunAtMs across enabled jobs."""
    earliest: int | None = None
    for j in jobs:
        if not j.enabled:
            continue
        nxt = j.state.next_run_ms
        if nxt is not None and (earliest is None or nxt < earliest):
            earliest = nxt
    return earliest


def _recompute_next_runs(jobs: list[CronJob], now_ms: int | None = None) -> None:
    """Recompute nextRunAtMs for all enabled jobs."""
    now = now_ms or _now_ms()
    for job in jobs:
        if not job.enabled:
            job.state.next_run_ms = None
            continue
        if job.state.running_at_ms is not None:
            # Don't recompute while job is running
            continue
        job.state.next_run_ms = compute_next_run(job.schedule, now)


# ---------------------------------------------------------------------------
# CronService
# ---------------------------------------------------------------------------

class CronService:
    """
    Complete Cron scheduling service aligned with TypeScript ops.ts.

    Features:
    - Three scheduling types (at/every/cron)
    - Isolated Agent execution (intelligent tasks)
    - System events (simple notifications)
    - Persistent storage with mtime-based reload
    - Run logs
    - Concurrency-safe via asyncio.Lock
    - status / wake / run with due|force mode
    """

    def __init__(
        self,
        store_path: Optional[Path] = None,
        log_dir: Optional[Path] = None,
        cron_enabled: bool = True,
        # Callbacks matching TypeScript CronServiceDeps
        enqueue_system_event: Optional[Callable[..., Any]] = None,
        request_heartbeat_now: Optional[Callable[..., Any]] = None,
        run_heartbeat_once: Optional[Callable[..., Any]] = None,
        run_isolated_agent_job: Optional[Callable[..., Awaitable[Dict[str, Any]]]] = None,
        on_event: Optional[Callable[[CronEvent], None]] = None,
        # Legacy callback names (backward compat)
        on_system_event: Optional[Callable[..., Awaitable[None]]] = None,
        on_isolated_agent: Optional[Callable[..., Awaitable[Dict[str, Any]]]] = None,
    ):
        # Jobs dict (in-memory mirror of store)
        self.jobs: Dict[str, CronJob] = {}
        self._service_running = False
        self._cron_enabled = cron_enabled

        # Store
        self.store_path = store_path
        self.log_dir = log_dir
        self._store: Optional[CronStore] = None
        self._store_loaded_at_ms: int | None = None
        self._store_file_mtime_ms: float | None = None
        if store_path:
            self._store = CronStore(store_path)

        # Callbacks (TypeScript-aligned names)
        self.enqueue_system_event = enqueue_system_event
        self.request_heartbeat_now = request_heartbeat_now
        self.run_heartbeat_once = run_heartbeat_once
        self.run_isolated_agent_job = run_isolated_agent_job
        self.on_event = on_event

        # Backward-compat: map legacy names if new names not provided
        if on_system_event and not enqueue_system_event:
            self.enqueue_system_event = on_system_event
        if on_isolated_agent and not run_isolated_agent_job:
            self.run_isolated_agent_job = on_isolated_agent

        # Concurrency lock (matches TypeScript locked())
        self._lock = asyncio.Lock()

        # Timer
        self._timer: Optional[CronTimer] = None

        # Running flag to prevent concurrent timer ticks
        self._timer_running = False

        # Warned-disabled flag (warn only once)
        self._warned_disabled = False

        logger.info("CronService initialized")

    # ------------------------------------------------------------------
    # Lock helper (matches TypeScript locked())
    # ------------------------------------------------------------------
    async def _locked(self, fn: Callable[..., Awaitable[Any]], *args: Any) -> Any:
        async with self._lock:
            return await fn(*args)

    # ------------------------------------------------------------------
    # Store helpers (matches TypeScript ensureLoaded / persist)
    # ------------------------------------------------------------------
    async def _ensure_loaded(
        self,
        force_reload: bool = False,
        skip_recompute: bool = False,
    ) -> None:
        """Load store if not loaded or force reload requested."""
        if self._store is None:
            return

        # Fast path: store already in memory
        if self.jobs and not force_reload:
            return

        # Load from disk
        jobs = self._store.load()
        self.jobs = {j.id: j for j in jobs}
        self._store_loaded_at_ms = _now_ms()

        # Track file mtime for change detection
        if self.store_path and self.store_path.exists():
            self._store_file_mtime_ms = self.store_path.stat().st_mtime_ns / 1e6

        if not skip_recompute:
            _recompute_next_runs(list(self.jobs.values()))

        logger.debug(f"Store loaded: {len(self.jobs)} jobs (force={force_reload})")

    async def _persist(self) -> None:
        """Save current jobs to store."""
        if self._store is None:
            return
        self._store.save(list(self.jobs.values()))
        # Update mtime after save
        if self.store_path and self.store_path.exists():
            self._store_file_mtime_ms = self.store_path.stat().st_mtime_ns / 1e6

    # ------------------------------------------------------------------
    # Emit helper
    # ------------------------------------------------------------------
    def _emit(self, **kwargs: Any) -> None:
        """Emit a CronEvent to the on_event callback."""
        evt = _make_event(**kwargs)
        try:
            if self.on_event:
                self.on_event(evt)
        except Exception:
            pass  # Matches TypeScript: silently ignore

    # ------------------------------------------------------------------
    # Warn-if-disabled (matches TypeScript warnIfDisabled)
    # ------------------------------------------------------------------
    def _warn_if_disabled(self, action: str) -> None:
        if self._cron_enabled:
            return
        if self._warned_disabled:
            return
        self._warned_disabled = True
        logger.warning(
            f"cron: scheduler disabled; jobs will not run automatically (action={action})"
        )

    # ------------------------------------------------------------------
    # Timer management
    # ------------------------------------------------------------------
    def _arm_timer(self) -> None:
        if self._timer:
            self._timer.arm_timer(list(self.jobs.values()))

    # ------------------------------------------------------------------
    # Public operations (all locked, matching TypeScript ops.ts)
    # ------------------------------------------------------------------
    async def start(self) -> None:
        """Start cron service (matches TypeScript start)."""
        async def _do_start() -> None:
            if not self._cron_enabled:
                logger.info("cron: disabled")
                return
            await self._ensure_loaded()
            _recompute_next_runs(list(self.jobs.values()))
            await self._persist()

            self._timer = CronTimer(on_timer_callback=self._on_timer)
            self._arm_timer()
            self._service_running = True

            nxt = _next_wake_at_ms(list(self.jobs.values()))
            logger.info(
                f"cron: started (jobs={len(self.jobs)}, nextWakeAtMs={nxt})"
            )

        await self._locked(_do_start)

    def stop(self) -> None:
        """Stop cron service (matches TypeScript stop)."""
        if self._timer:
            self._timer.stop()
            self._timer = None
        self._service_running = False
        logger.info("CronService stopped")

    # Backward compat
    def shutdown(self) -> None:
        self.stop()

    async def status(self) -> Dict[str, Any]:
        """Return service status (matches TypeScript status)."""
        async def _do_status() -> Dict[str, Any]:
            await self._ensure_loaded()
            nxt = (
                _next_wake_at_ms(list(self.jobs.values()))
                if self._cron_enabled
                else None
            )
            return {
                "enabled": self._cron_enabled,
                "storePath": str(self.store_path) if self.store_path else None,
                "jobs": len(self.jobs),
                "nextWakeAtMs": nxt,
            }

        return await self._locked(_do_status)

    async def list_jobs(
        self, include_disabled: bool = False
    ) -> list[Dict[str, Any]]:
        """List all jobs (matches TypeScript list)."""
        async def _do_list() -> list[Dict[str, Any]]:
            await self._ensure_loaded()
            jobs = list(self.jobs.values())
            if not include_disabled:
                jobs = [j for j in jobs if j.enabled]
            # Sort by nextRunAtMs ascending
            jobs.sort(key=lambda j: j.state.next_run_ms or 0)
            return [self._job_to_dict(j) for j in jobs]

        return await self._locked(_do_list)

    async def add_job(self, job: CronJob) -> CronJob:
        """Add a new cron job (matches TypeScript add)."""
        async def _do_add() -> CronJob:
            self._warn_if_disabled("add")
            await self._ensure_loaded()

            # Compute initial next run
            now = _now_ms()
            if job.state.next_run_ms is None:
                job.state.next_run_ms = compute_next_run(job.schedule, now)

            self.jobs[job.id] = job
            await self._persist()
            self._arm_timer()

            self._emit(
                jobId=job.id,
                action="added",
                nextRunAtMs=job.state.next_run_ms,
            )
            logger.info(f"Added cron job: {job.name} (id={job.id})")
            return job

        return await self._locked(_do_add)

    async def update_job(self, job_id: str, patch: Dict[str, Any]) -> CronJob:
        """Update an existing job (matches TypeScript update)."""
        async def _do_update() -> CronJob:
            self._warn_if_disabled("update")
            await self._ensure_loaded()

            job = self.jobs.get(job_id)
            if not job:
                raise ValueError(f"Job not found: {job_id}")

            now = _now_ms()
            _apply_job_patch(job, patch)
            job.updated_at_ms = now

            if job.enabled:
                job.state.next_run_ms = compute_next_run(job.schedule, now)
            else:
                job.state.next_run_ms = None
                job.state.running_at_ms = None

            await self._persist()
            self._arm_timer()

            self._emit(
                jobId=job_id,
                action="updated",
                nextRunAtMs=job.state.next_run_ms,
            )
            logger.info(f"Updated job: {job_id}")
            return job

        return await self._locked(_do_update)

    async def remove_job(self, job_id: str) -> Dict[str, Any]:
        """Remove a job (matches TypeScript remove)."""
        async def _do_remove() -> Dict[str, Any]:
            self._warn_if_disabled("remove")
            await self._ensure_loaded()

            removed = job_id in self.jobs
            if removed:
                del self.jobs[job_id]

            await self._persist()
            self._arm_timer()

            if removed:
                self._emit(jobId=job_id, action="removed")
                logger.info(f"Removed job: {job_id}")

            return {"ok": True, "removed": removed}

        return await self._locked(_do_remove)

    async def run(
        self, job_id: str, mode: Literal["due", "force"] = "force"
    ) -> Dict[str, Any]:
        """Run a job (matches TypeScript run with due|force mode)."""
        async def _do_run() -> Dict[str, Any]:
            self._warn_if_disabled("run")
            await self._ensure_loaded()

            job = self.jobs.get(job_id)
            if not job:
                raise ValueError(f"Job not found: {job_id}")

            now = _now_ms()
            forced = mode == "force"

            # Check if due
            if not forced:
                if not _is_job_due(job, now):
                    return {"ok": True, "ran": False, "reason": "not-due"}

            await self._execute_job(job, now, forced=forced)
            await self._persist()
            self._arm_timer()
            return {"ok": True, "ran": True}

        return await self._locked(_do_run)

    # Backward compat alias
    async def run_job_now(self, job_id: str) -> Dict[str, Any]:
        return await self.run(job_id, mode="force")

    def wake(
        self,
        text: str,
        mode: Literal["now", "next-heartbeat"] = "now",
    ) -> Dict[str, Any]:
        """Send a wake event (matches TypeScript wake / wakeNow)."""
        text = text.strip()
        if not text:
            return {"ok": False}

        if self.enqueue_system_event:
            # enqueue_system_event may be sync or async; fire-and-forget
            try:
                result = self.enqueue_system_event(text)
                if asyncio.iscoroutine(result):
                    asyncio.ensure_future(result)
            except Exception as e:
                logger.error(f"Error in enqueue_system_event: {e}")

        if mode == "now" and self.request_heartbeat_now:
            try:
                self.request_heartbeat_now(reason="wake")
            except Exception as e:
                logger.error(f"Error in request_heartbeat_now: {e}")

        return {"ok": True}

    def get_job(self, job_id: str) -> Optional[CronJob]:
        """Get a job by ID (direct access, no lock)."""
        return self.jobs.get(job_id)

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status as dict."""
        job = self.jobs.get(job_id)
        return self._job_to_dict(job) if job else None

    # ------------------------------------------------------------------
    # Timer callback (matches TypeScript onTimer)
    # ------------------------------------------------------------------
    async def _on_timer(self, due_jobs: list[CronJob]) -> None:
        """Timer callback - runs due jobs under lock."""
        if self._timer_running:
            return
        self._timer_running = True
        try:
            async with self._lock:
                # Force-reload store to detect external changes
                await self._ensure_loaded(force_reload=True, skip_recompute=True)

                # Run due jobs
                await self._run_due_jobs()

                # Recompute all next runs
                _recompute_next_runs(list(self.jobs.values()))
                await self._persist()
        except Exception as e:
            logger.error(f"cron: timer tick failed: {e}", exc_info=True)
        finally:
            self._timer_running = False
            # Always re-arm so transient errors don't kill the scheduler
            self._arm_timer()

    async def _run_due_jobs(self) -> None:
        """Run all due jobs (called under lock)."""
        now = _now_ms()
        due = [
            j
            for j in self.jobs.values()
            if j.enabled
            and j.state.running_at_ms is None
            and j.state.next_run_ms is not None
            and now >= j.state.next_run_ms
        ]

        for job in due:
            try:
                await self._execute_job(job, now, forced=False)
            except Exception as e:
                logger.error(f"Error executing job {job.id}: {e}", exc_info=True)

    # ------------------------------------------------------------------
    # Job execution (matches TypeScript executeJob in timer.ts)
    # ------------------------------------------------------------------
    async def _execute_job(
        self, job: CronJob, now_ms: int, *, forced: bool = False
    ) -> Dict[str, Any]:
        """Execute a single job. Matches TypeScript executeJob."""
        started_at = _now_ms()
        job.state.running_at_ms = started_at
        job.state.last_error = None

        self._emit(jobId=job.id, action="started", runAtMs=started_at)

        deleted = False

        async def finish(
            status: Literal["ok", "error", "skipped"],
            error: str | None = None,
            summary: str | None = None,
        ) -> None:
            nonlocal deleted
            ended_at = _now_ms()
            job.state.running_at_ms = None
            job.state.last_run_at_ms = started_at
            # Use "ok" instead of "success" to match TypeScript
            job.state.last_status = "ok" if status == "ok" else ("error" if status == "error" else "skipped")
            job.state.last_duration_ms = max(0, ended_at - started_at)
            job.state.last_error = error

            from .types import AtSchedule
            should_delete = (
                isinstance(job.schedule, AtSchedule)
                and status == "ok"
                and job.delete_after_run
            )

            if not should_delete:
                if isinstance(job.schedule, AtSchedule) and status == "ok":
                    # One-shot completed: disable
                    job.enabled = False
                    job.state.next_run_ms = None
                elif job.enabled:
                    job.state.next_run_ms = compute_next_run(job.schedule, ended_at)
                else:
                    job.state.next_run_ms = None

            self._emit(
                jobId=job.id,
                action="finished",
                status=status,
                error=error,
                summary=summary,
                runAtMs=started_at,
                durationMs=job.state.last_duration_ms,
                nextRunAtMs=job.state.next_run_ms,
            )

            if should_delete and job.id in self.jobs:
                del self.jobs[job.id]
                deleted = True
                self._emit(jobId=job.id, action="removed")

        result: Dict[str, Any] = {"success": False}

        try:
            if job.session_target == "main":
                result = await self._execute_main_session_job(job, finish)
            else:
                result = await self._execute_isolated_job(job, finish)
        except Exception as e:
            await finish("error", str(e))
            result = {"success": False, "error": str(e)}
        finally:
            job.updated_at_ms = now_ms
            if not forced and job.enabled and not deleted:
                # Keep nextRunAtMs in sync in case schedule advanced during long run
                job.state.next_run_ms = compute_next_run(job.schedule, _now_ms())

            # Record run log (TypeScript-compatible format)
            if self.log_dir:
                try:
                    run_log = CronRunLog(self.log_dir, job.id)
                    
                    # Convert status: "success" → "ok"
                    status = job.state.last_status
                    if status == "success":
                        status = "ok"
                    
                    run_log.append({
                        "ts": int(datetime.now(timezone.utc).timestamp() * 1000),
                        "jobId": job.id,
                        "action": "finished",
                        "status": status,
                        "error": job.state.last_error,
                        "summary": result.get("summary"),
                        "runAtMs": job.state.last_run_at_ms,
                        "durationMs": job.state.last_duration_ms,
                        "nextRunAtMs": job.state.next_run_ms,
                    })
                except Exception as e:
                    logger.warning(f"Failed to write run log: {e}")

        return result

    async def _execute_main_session_job(
        self,
        job: CronJob,
        finish: Callable[..., Awaitable[None]],
    ) -> Dict[str, Any]:
        """Execute main session job (systemEvent). Matches TypeScript logic."""
        # Resolve payload text
        text = _resolve_job_payload_text_for_main(job)
        if not text:
            kind = getattr(job.payload, "kind", "unknown")
            reason = (
                "main job requires non-empty systemEvent text"
                if kind == "systemEvent"
                else 'main job requires payload.kind="systemEvent"'
            )
            await finish("skipped", reason)
            return {"success": False, "error": reason}

        # Enqueue system event
        if self.enqueue_system_event:
            try:
                result = self.enqueue_system_event(text, job.agent_id)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Error enqueuing system event: {e}")

        # Handle wakeMode
        if job.wake_mode == "now" and self.run_heartbeat_once:
            # Wait for main lane to become idle (up to 2 minutes)
            reason = f"cron:{job.id}"
            max_wait_ms = 2 * 60_000
            wait_started_at = _now_ms()

            heartbeat_result: Dict[str, Any] = {"status": "error", "reason": "not-run"}
            while True:
                try:
                    heartbeat_result = await self.run_heartbeat_once(reason=reason)
                except Exception as e:
                    heartbeat_result = {"status": "error", "reason": str(e)}
                    break

                if (
                    heartbeat_result.get("status") != "skipped"
                    or heartbeat_result.get("reason") != "requests-in-flight"
                ):
                    break
                if _now_ms() - wait_started_at > max_wait_ms:
                    heartbeat_result = {
                        "status": "skipped",
                        "reason": "timeout waiting for main lane to become idle",
                    }
                    break
                await asyncio.sleep(0.25)

            hb_status = heartbeat_result.get("status", "error")
            if hb_status == "ran" or hb_status == "completed":
                await finish("ok", summary=text)
            elif hb_status == "skipped":
                await finish("skipped", heartbeat_result.get("reason"), text)
            else:
                await finish("error", heartbeat_result.get("reason"), text)
        else:
            # wakeMode is "next-heartbeat" or runHeartbeatOnce not available
            if self.request_heartbeat_now:
                try:
                    self.request_heartbeat_now(reason=f"cron:{job.id}")
                except Exception as e:
                    logger.error(f"Error requesting heartbeat: {e}")
            await finish("ok", summary=text)

        return {"success": True, "summary": text}

    async def _execute_isolated_job(
        self,
        job: CronJob,
        finish: Callable[..., Awaitable[None]],
    ) -> Dict[str, Any]:
        """Execute isolated agent job. Matches TypeScript logic."""
        payload = job.payload
        if not isinstance(payload, AgentTurnPayload):
            await finish("skipped", "isolated job requires payload.kind=agentTurn")
            return {"success": False, "error": "isolated job requires agentTurn"}

        if not self.run_isolated_agent_job:
            await finish("error", "isolated agent callback not configured")
            return {"success": False, "error": "callback not configured"}

        # Run isolated agent
        res = await self.run_isolated_agent_job(job)

        # Post summary back to main session
        summary_text = (res.get("summary") or "").strip()
        delivery_mode = "announce"
        if job.delivery and hasattr(job.delivery, "mode"):
            delivery_mode = getattr(job.delivery, "mode", "announce")

        if summary_text and delivery_mode != "none":
            prefix = "Cron"
            status = res.get("status", res.get("success"))
            if status == "error" or status is False:
                label = f"{prefix} (error): {summary_text}"
            else:
                label = f"{prefix}: {summary_text}"

            if self.enqueue_system_event:
                try:
                    r = self.enqueue_system_event(label, job.agent_id)
                    if asyncio.iscoroutine(r):
                        await r
                except Exception as e:
                    logger.error(f"Error posting summary to main: {e}")

            if job.wake_mode == "now" and self.request_heartbeat_now:
                try:
                    self.request_heartbeat_now(reason=f"cron:{job.id}")
                except Exception as e:
                    logger.error(f"Error requesting heartbeat: {e}")

        # Determine status
        job_status = res.get("status", "ok" if res.get("success") else "error")
        if job_status == "ok" or job_status is True:
            await finish("ok", summary=res.get("summary"))
        elif job_status == "skipped":
            await finish("skipped", summary=res.get("summary"))
        else:
            await finish("error", res.get("error", "cron job failed"), res.get("summary"))

        return {
            "success": job_status in ("ok", True),
            "summary": res.get("summary"),
            "error": res.get("error"),
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _job_to_dict(self, job: CronJob) -> Dict[str, Any]:
        """
        Convert Job to dictionary in TypeScript-compatible format
        
        Uses serialization module to ensure complete API compatibility
        """
        from openclaw.cron.serialization import convert_job_to_api
        
        # Get Python dict first
        python_dict = job.to_dict()
        
        # Convert to TypeScript API format
        return convert_job_to_api(python_dict)


# ---------------------------------------------------------------------------
# Patch helper (matches TypeScript applyJobPatch)
# ---------------------------------------------------------------------------

def _apply_job_patch(job: CronJob, patch: Dict[str, Any]) -> None:
    """Apply a patch to a CronJob, matching TypeScript applyJobPatch."""
    from .types import AtSchedule, EverySchedule, CronSchedule, CronDelivery

    if "name" in patch:
        job.name = str(patch["name"]).strip() or job.name
    if "description" in patch:
        job.description = patch["description"]
    if "enabled" in patch:
        job.enabled = bool(patch["enabled"])
    if "deleteAfterRun" in patch or "delete_after_run" in patch:
        job.delete_after_run = bool(patch.get("deleteAfterRun", patch.get("delete_after_run", False)))
    if "sessionTarget" in patch or "session_target" in patch:
        val = patch.get("sessionTarget", patch.get("session_target"))
        if val in ("main", "isolated"):
            job.session_target = val
    if "wakeMode" in patch or "wake_mode" in patch:
        val = patch.get("wakeMode", patch.get("wake_mode"))
        if val in ("now", "next-heartbeat"):
            job.wake_mode = val
    if "agentId" in patch or "agent_id" in patch:
        job.agent_id = patch.get("agentId", patch.get("agent_id"))

    # Schedule patch
    if "schedule" in patch:
        sched = patch["schedule"]
        stype = sched.get("type", sched.get("kind"))
        if stype == "at":
            job.schedule = AtSchedule(timestamp=sched.get("timestamp", sched.get("at", "")))
        elif stype == "every":
            job.schedule = EverySchedule(
                interval_ms=sched.get("interval_ms", sched.get("intervalMs", 0)),
                anchor=sched.get("anchor"),
            )
        elif stype == "cron":
            job.schedule = CronSchedule(
                expression=sched.get("expression", ""),
                timezone=sched.get("timezone", "UTC"),
            )

    # Shorthand schedule patches
    if "cronExpression" in patch:
        if isinstance(job.schedule, CronSchedule):
            job.schedule.expression = patch["cronExpression"]
    if "timezone" in patch:
        if isinstance(job.schedule, CronSchedule):
            job.schedule.timezone = patch["timezone"]
    if "intervalMs" in patch or "interval_ms" in patch:
        if isinstance(job.schedule, EverySchedule):
            job.schedule.interval_ms = patch.get("intervalMs", patch.get("interval_ms", 0))

    # Payload patch
    if "payload" in patch:
        from .types import SystemEventPayload, AgentTurnPayload
        p = patch["payload"]
        kind = p.get("kind")
        if kind == "systemEvent":
            job.payload = SystemEventPayload(text=p.get("text", ""))
        elif kind == "agentTurn":
            job.payload = AgentTurnPayload(
                prompt=p.get("prompt", p.get("message", "")),
                model=p.get("model"),
            )

    # Delivery patch
    if "delivery" in patch:
        d = patch["delivery"]
        if d is None:
            job.delivery = None
        else:
            job.delivery = CronDelivery(
                channel=d.get("channel", ""),
                target=d.get("target"),
                best_effort=d.get("best_effort", d.get("bestEffort", False)),
            )


def _is_job_due(job: CronJob, now_ms: int, *, forced: bool = False) -> bool:
    """Check if a job is due to run."""
    if forced:
        return True
    if not job.enabled:
        return False
    if job.state.running_at_ms is not None:
        return False
    nxt = job.state.next_run_ms
    return nxt is not None and now_ms >= nxt


def _resolve_job_payload_text_for_main(job: CronJob) -> str | None:
    """Resolve payload text for main session jobs."""
    if isinstance(job.payload, SystemEventPayload):
        text = (job.payload.text or "").strip()
        return text if text else None
    return None


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

_cron_service: Optional[CronService] = None


def get_cron_service() -> CronService:
    global _cron_service
    if _cron_service is None:
        _cron_service = CronService()
    return _cron_service


def set_cron_service(service: CronService) -> None:
    global _cron_service
    _cron_service = service

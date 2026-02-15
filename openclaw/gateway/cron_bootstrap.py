"""Cron service bootstrap for Gateway

Aligned with TypeScript openclaw/src/gateway/server-cron.ts (buildGatewayCronService).

Key responsibilities:
1. Resolve store path from config
2. Create CronService with properly wired callbacks:
   - enqueue_system_event
   - request_heartbeat_now
   - run_heartbeat_once
   - run_isolated_agent_job
   - on_event (broadcast + run log)
3. Load existing jobs from store
4. Return GatewayCronState (start is deferred)
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..cron import CronService
    from ..cron.types import CronJob
    from .types import GatewayDeps, GatewayCronState, BroadcastFn

logger = logging.getLogger(__name__)


async def build_gateway_cron_service(
    config: dict[str, Any] | Any,
    deps: "GatewayDeps",
    broadcast: "BroadcastFn",
) -> "GatewayCronState":
    """
    Build and initialize cron service for Gateway.

    Matches TypeScript buildGatewayCronService():
    - Wires enqueueSystemEvent, requestHeartbeatNow, runHeartbeatOnce,
      runIsolatedAgentJob, and onEvent callbacks.
    - Loads jobs from disk.
    - Returns GatewayCronState (service.start() is deferred to after
      channel_manager is ready).
    """
    from ..cron import CronService
    from ..cron.store import CronStore, CronRunLog
    from ..cron.isolated_agent.run import run_isolated_agent_turn
    from ..cron.isolated_agent.delivery import deliver_result
    from .types import GatewayCronState

    # ------------------------------------------------------------------
    # Resolve config dict (guaranteed to return a dict)
    # ------------------------------------------------------------------
    try:
        config_dict = _resolve_config_dict(config)
        logger.debug(f"Resolved config_dict type: {type(config_dict)}, is dict: {isinstance(config_dict, dict)}")
        
        # Handle case where config has cron: null explicitly
        cron_config = (config_dict or {}).get("cron") or {}
        logger.debug(f"Resolved cron_config: {type(cron_config)}")
        
        store_path = _resolve_store_path(cron_config)
        store_path.parent.mkdir(parents=True, exist_ok=True)
        log_dir = store_path.parent / "logs"

        logger.info(f"Cron store path: {store_path}")

        cron_enabled = (
            os.getenv("OPENCLAW_SKIP_CRON") != "1"
            and (cron_config or {}).get("enabled", True)
        )
    except Exception as e:
        logger.error(f"Error in config resolution: {e}", exc_info=True)
        raise

    if not cron_enabled:
        logger.info("Cron service is disabled")
        service = CronService(cron_enabled=False)
        return GatewayCronState(cron=service, store_path=store_path, enabled=False)

    # ------------------------------------------------------------------
    # Migrate store if needed
    # ------------------------------------------------------------------
    store = CronStore(store_path)
    store.migrate_if_needed()

    # ------------------------------------------------------------------
    # Callback: enqueue_system_event
    # ------------------------------------------------------------------
    async def enqueue_system_event(text: str, agent_id: str | None = None) -> None:
        """Enqueue system event to main session."""
        try:
            agent_id = agent_id or "main"
            logger.info(f"Enqueuing system event to agent '{agent_id}': {text[:100]}...")
            session_key = f"{agent_id}-main"

            if deps.session_manager:
                session = deps.session_manager.get_session(session_key)
                if session:
                    session.add_system_message(text)
                    logger.info(f"System event added to session '{session_key}'")
                else:
                    logger.warning(f"Session '{session_key}' not found for system event")
            else:
                logger.warning("Session manager not available for system event")
        except Exception as e:
            logger.error(f"Error enqueuing system event: {e}", exc_info=True)

    # ------------------------------------------------------------------
    # Callback: request_heartbeat_now
    # ------------------------------------------------------------------
    def request_heartbeat_now(reason: str | None = None) -> None:
        """Request immediate heartbeat processing."""
        logger.info(f"Heartbeat requested (reason={reason})")
        # Fire-and-forget: trigger heartbeat runner if available
        try:
            import asyncio
            from openclaw.infra.heartbeat_runner import (
                request_heartbeat_now as hb_request,
            )
            hb_request(reason=reason)
        except ImportError:
            logger.debug("heartbeat_runner not available")
        except Exception as e:
            logger.error(f"Error requesting heartbeat: {e}", exc_info=True)

    # ------------------------------------------------------------------
    # Callback: run_heartbeat_once
    # ------------------------------------------------------------------
    async def run_heartbeat_once(reason: str | None = None) -> dict[str, Any]:
        """Run heartbeat once, waiting for result."""
        try:
            from openclaw.infra.heartbeat_runner import (
                run_heartbeat_once as runner_run_once,
            )

            agent_id = "main"
            agent_config = (config_dict or {}).get("agent", {})
            if not agent_config.get("heartbeat", {}).get("enabled", False):
                return {"status": "skipped", "reason": "not-enabled"}

            async def execute_heartbeat(agent_id_inner: str, prompt: str) -> Any:
                session_key = f"{agent_id_inner}-main"
                if not deps.session_manager:
                    return None
                session = deps.session_manager.get_session(session_key)
                if not session:
                    return None

                response_text = ""
                async for event in deps.provider.prompt(
                    messages=[{"role": "user", "content": prompt}],
                    tools=None,
                ):
                    if event.type == "text_delta":
                        response_text += event.content
                    elif event.type == "done":
                        break

                if response_text:
                    session.add_user_message(prompt)
                    session.add_assistant_message(response_text)
                return response_text

            await runner_run_once(
                agent_id=agent_id,
                agent_config=agent_config,
                execute_fn=execute_heartbeat,
            )
            return {"status": "ran", "reason": reason}
        except ImportError:
            return {"status": "skipped", "reason": "heartbeat_runner not available"}
        except Exception as e:
            logger.error(f"Error running heartbeat: {e}", exc_info=True)
            return {"status": "error", "reason": str(e)}

    # ------------------------------------------------------------------
    # Callback: run_isolated_agent_job
    # ------------------------------------------------------------------
    async def run_isolated_agent(job: "CronJob") -> dict[str, Any]:
        """Run isolated agent for cron job."""
        try:
            sessions_dir = getattr(
                deps.session_manager, "sessions_dir",
                Path.home() / ".openclaw" / "sessions",
            )

            result = await run_isolated_agent_turn(
                job=job,
                provider=deps.provider,
                tools=deps.tools,
                sessions_dir=sessions_dir,
                system_prompt=None,
            )

            # Deliver result if delivery configured
            if job.delivery and result.get("success"):
                try:
                    delivery_success = await deliver_result(
                        job=job,
                        result=result,
                        get_channel_manager=deps.get_channel_manager,
                        session_history=None,
                    )
                    result["delivered"] = delivery_success
                except Exception as e:
                    logger.error(f"Error delivering result: {e}", exc_info=True)
                    result["delivery_error"] = str(e)

            return result
        except Exception as e:
            logger.error(f"Error running isolated agent: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    # Callback: on_event (broadcast + run log on "finished")
    # ------------------------------------------------------------------
    def on_event(event: dict[str, Any]) -> None:
        """Handle cron events: broadcast to WS clients and persist run logs."""
        if event is None:
            logger.warning("on_event received None event")
            return
            
        try:
            # Broadcast to WebSocket clients
            broadcast("cron", event, {"dropIfSlow": True})

            action = event.get("action")
            job_id = event.get("jobId")

            if action == "started":
                logger.info(f"Cron job started: {job_id}")

            elif action == "finished":
                status = event.get("status")
                duration_ms = event.get("durationMs", 0)
                logger.info(
                    f"Cron job finished: {job_id}, status={status}, duration={duration_ms}ms"
                )
                if status == "error":
                    logger.error(f"Cron job error: {job_id}: {event.get('error')}")

                # Append to run log (matches TypeScript onEvent "finished" handler)
                try:
                    run_log = CronRunLog(log_dir, job_id)
                    run_log.append({
                        "ts": event.get("runAtMs", 0),
                        "jobId": job_id,
                        "action": "finished",
                        "status": status,
                        "error": event.get("error"),
                        "summary": event.get("summary"),
                        "durationMs": duration_ms,
                        "nextRunAtMs": event.get("nextRunAtMs"),
                    })
                except Exception as e:
                    logger.warning(f"Failed to append run log: {e}")

        except Exception as e:
            logger.error(f"Error handling cron event: {e}", exc_info=True)

    # ------------------------------------------------------------------
    # Create service with all callbacks
    # ------------------------------------------------------------------
    service = CronService(
        store_path=store_path,
        log_dir=log_dir,
        cron_enabled=cron_enabled,
        enqueue_system_event=enqueue_system_event,
        request_heartbeat_now=request_heartbeat_now,
        run_heartbeat_once=run_heartbeat_once,
        run_isolated_agent_job=run_isolated_agent,
        on_event=on_event,
    )

    # Load jobs
    logger.info("Loading cron jobs from store...")
    jobs = store.load()
    logger.info(f"Loaded {len(jobs)} cron jobs")

    for job in jobs:
        service.jobs[job.id] = job

    logger.info(f"Cron service initialized with {len(jobs)} jobs (start deferred)")

    return GatewayCronState(
        cron=service,
        store_path=store_path,
        enabled=cron_enabled,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_config_dict(config: Any) -> dict[str, Any]:
    """Normalize config to a plain dict."""
    if config is None:
        return {}
    if hasattr(config, "model_dump"):
        return config.model_dump()
    if hasattr(config, "__dict__") and not isinstance(config, dict):
        return config.__dict__
    if isinstance(config, dict):
        return config
    return {}


def _resolve_store_path(cron_config: dict[str, Any] | None) -> Path:
    """Resolve cron store path from config (handles None config)."""
    if not cron_config:
        cron_config = {}
    store_path_str = cron_config.get("store", "~/.openclaw/cron/jobs.json")
    if store_path_str.startswith("~"):
        return Path.home() / store_path_str[2:]
    return Path(store_path_str).expanduser()


def resolve_cron_store_path(config: dict[str, Any] | None) -> Path:
    """Resolve cron store path from config (public helper)."""
    if not config:
        config = {}
    cron_config = config.get("cron") or {}
    return _resolve_store_path(cron_config)


def is_cron_enabled(config: dict[str, Any] | None) -> bool:
    """Check if cron is enabled in config (public helper)."""
    if os.getenv("OPENCLAW_SKIP_CRON") == "1":
        return False
    if not config:
        return True  # Default to enabled if no config
    cron_config = config.get("cron") or {}
    return cron_config.get("enabled", True)

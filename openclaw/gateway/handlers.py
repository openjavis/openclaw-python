"""Gateway method handlers"""
from __future__ import annotations


import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
import sys

# Python 3.9 compatibility
if sys.version_info >= (3, 11):
    from datetime import UTC
else:
    UTC = timezone.utc
from typing import Any

# Import store-based session methods
from openclaw.gateway.api.sessions_methods import (
    SessionsListMethod,
    SessionsPreviewMethod,
    SessionsResolveMethod,
    SessionsPatchMethod,
    SessionsResetMethod,
    SessionsDeleteMethod,
    SessionsCompactMethod,
)

# Import chat methods
from openclaw.gateway.api.chat import CHAT_METHODS

logger = logging.getLogger(__name__)

# Type alias for handler functions
Handler = Callable[[Any, dict[str, Any]], Awaitable[Any]]

# Registry of method handlers
_handlers: dict[str, Handler] = {}

# Global instances (set by gateway server)
_session_manager: Any | None = None
_tool_registry: Any | None = None
_channel_registry: Any | None = None
_agent_runtime: Any | None = None
_wizard_handler: Any | None = None


def set_global_instances(session_manager, tool_registry, channel_registry, agent_runtime, wizard_handler=None):
    """Set global instances for handlers to use"""
    global _session_manager, _tool_registry, _channel_registry, _agent_runtime, _wizard_handler
    _session_manager = session_manager
    _tool_registry = tool_registry
    _channel_registry = channel_registry
    _agent_runtime = agent_runtime
    _wizard_handler = wizard_handler


def register_handler(method: str) -> Callable[[Handler], Handler]:
    """Decorator to register a method handler"""

    def decorator(func: Handler) -> Handler:
        _handlers[method] = func
        return func

    return decorator


def get_method_handler(method: str) -> Handler | None:
    """Get handler for a method"""
    return _handlers.get(method)


# Initialize store-based session method instances
_sessions_list_method = SessionsListMethod()
_sessions_preview_method = SessionsPreviewMethod()
_sessions_resolve_method = SessionsResolveMethod()
_sessions_patch_method = SessionsPatchMethod()
_sessions_reset_method = SessionsResetMethod()
_sessions_delete_method = SessionsDeleteMethod()
_sessions_compact_method = SessionsCompactMethod()


# Register chat methods
def _register_chat_methods():
    """Register all chat methods from api/chat.py"""
    for chat_method in CHAT_METHODS:
        # Create wrapper that calls method.execute
        def make_handler(method_obj):
            async def handler(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
                try:
                    return await method_obj.execute(connection, params)
                except Exception as e:
                    logger.error(f"Chat method {method_obj.name} error: {e}", exc_info=True)
                    raise
            return handler
        
        _handlers[chat_method.name] = make_handler(chat_method)
        logger.debug(f"Registered chat method: {chat_method.name}")


# Register chat methods on module load
_register_chat_methods()


# Core method handlers


@register_handler("health")
async def handle_health(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Health check"""
    return {
        "status": "ok",
        "uptime": 0,  # TODO: Track actual uptime
        "connections": len(connection.config.gateway.__dict__),
    }


@register_handler("status")
async def handle_status(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Get server status"""
    return {
        "gateway": {
            "running": True,
            "port": connection.config.gateway.port,
            "connections": 1,  # TODO: Track actual connections
        },
        "agents": {
            "count": len(connection.config.agents.agents) if connection.config.agents.agents else 0
        },
        "channels": {"active": []},  # TODO: Track active channels
    }


@register_handler("config.get")
async def handle_config_get(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Get configuration"""
    return connection.config.model_dump(exclude_none=True)


@register_handler("sessions.list")
async def handle_sessions_list(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """List active sessions - using store-based implementation"""
    return await _sessions_list_method.execute(connection, params)


@register_handler("channels.list")
async def handle_channels_list(connection: Any, params: dict[str, Any]) -> list[dict[str, Any]]:
    """List available channels"""
    if not _channel_registry:
        return []

    return _channel_registry.get_all_channels()


# Placeholder handlers for methods to be implemented


@register_handler("agent")
async def handle_agent(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Run agent turn (synchronous - waits for completion)"""
    message = params.get("message", "")
    session_id = params.get("sessionId") or params.get("sessionKey", "main")
    model = params.get("model")
    stream = params.get("stream", False)

    if not message:
        raise ValueError("message required")

    if not _agent_runtime or not _session_manager or not _tool_registry:
        raise RuntimeError("Agent runtime not initialized")

    # Get session
    session = _session_manager.get_session(session_id)

    # Get tools
    tools = _tool_registry.list_tools()

    # If streaming requested, use async background execution
    if stream:
        run_id = params.get("runId") or f"run-{int(datetime.now(UTC).timestamp() * 1000)}"
        accepted_at = datetime.now(UTC).isoformat() + "Z"
        
        # Create task and track it for abort capability
        task = asyncio.create_task(_run_agent_turn(connection, run_id, session, message, tools, model))
        
        # Store in connection's gateway server for abort tracking
        if hasattr(connection, "gateway") and hasattr(connection.gateway, "active_runs"):
            connection.gateway.active_runs[run_id] = task
            
            # Clean up when done
            def cleanup_run(future):
                if run_id in connection.gateway.active_runs:
                    del connection.gateway.active_runs[run_id]
            task.add_done_callback(cleanup_run)
        
        return {"runId": run_id, "acceptedAt": accepted_at, "streaming": True}

    # Otherwise, execute synchronously and return full result
    response_text = ""
    tool_calls = []
    usage = {}
    
    try:
        from openclaw.events import EventType
        
        async for event in _agent_runtime.run_turn(session, message, tools, model):
            # Handle text events (check for EventType.AGENT_TEXT enum or string "text")
            if event.type == EventType.AGENT_TEXT or event.type == "text":
                # Extract text from delta structure: data.delta.text or data.text
                if "delta" in event.data and "text" in event.data["delta"]:
                    response_text += event.data["delta"]["text"]
                elif "text" in event.data:
                    response_text += event.data["text"]
            elif event.type == "tool_call":
                tool_calls.append(event.data)
            elif event.type == "usage":
                usage = event.data
        
        return {
            "response": {
                "text": response_text,
                "toolCalls": tool_calls
            },
            "usage": usage,
            "sessionId": session_id
        }
    except Exception as e:
        logger.error(f"Agent turn error: {e}", exc_info=True)
        return {"error": str(e)}


async def _run_agent_turn(connection, run_id, session, message, tools, model):
    """Execute agent turn and stream results"""
    try:
        # Stream events to client
        async for event in _agent_runtime.run_turn(session, message, tools, model):
            # Send event to client
            await connection.send_event(
                "agent", {"runId": run_id, "type": event.type, "data": event.data}
            )
    except asyncio.CancelledError:
        logger.info(f"Agent turn {run_id} was aborted")
        # Send abort event to client
        await connection.send_event(
            "agent",
            {
                "runId": run_id,
                "type": "turn_aborted",
                "data": {"reason": "User requested abort"}
            }
        )
        raise  # Re-raise to properly handle cancellation
    except Exception as e:
        logger.error(f"Agent turn error: {e}", exc_info=True)
        await connection.send_event("agent", {"runId": run_id, "type": "error", "error": str(e)})


# Old chat handlers removed - now using openclaw/gateway/api/chat.py
# The new chat methods (chat.send, chat.history, chat.abort, chat.inject) 
# are registered by _register_chat_methods() above


@register_handler("agent.identity.get")
async def handle_agent_identity_get(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Get agent identity"""
    agent_id = params.get("agentId")
    config = connection.config

    return {
        "agentId": agent_id or "default",
        "model": str(config.agent.model) if config.agent else "unknown",
    }


@register_handler("agent.wait")
async def handle_agent_wait(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Wait for agent to complete"""
    run_id = params.get("runId")
    timeout = params.get("timeout", 600)
    return {"runId": run_id, "status": "completed"}


@register_handler("agents.list")
async def handle_agents_list(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """List available agents (matches TypeScript agents.ts format)"""
    # Return configured agents from config in the correct format
    agents_data = [
        {
            "id": "main",
            "name": "Main Agent",
            "identity": {
                "name": "OpenClaw Assistant",
                "theme": None,
                "emoji": None,
                "avatar": None,
                "avatarUrl": None,
            }
        }
    ]
    
    # Return in TypeScript-aligned format
    return {
        "defaultId": "main",
        "mainKey": "main",
        "scope": "user",
        "agents": agents_data
    }


@register_handler("agent.queue.status")
async def handle_agent_queue_status(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Get agent queue status"""
    if not _agent_runtime:
        return {"enabled": False}
    
    # Check if queue manager is enabled
    if not hasattr(_agent_runtime, "queue_manager") or not _agent_runtime.queue_manager:
        return {"enabled": False}
    
    # Get queue statistics
    stats = _agent_runtime.queue_manager.get_stats()
    
    return {
        "enabled": True,
        "global": stats.get("global", {}),
        "sessions": stats.get("sessions", {}),
        "total_sessions": stats.get("total_sessions", 0)
    }


@register_handler("agents.files.list")
async def handle_agents_files_list(connection: Any, params: dict[str, Any]) -> list[str]:
    """List agent files"""
    from pathlib import Path
    agent_dir = Path.home() / ".openclaw" / "agents"
    if not agent_dir.exists():
        return []
    return [f.name for f in agent_dir.iterdir() if f.is_file()]


@register_handler("agents.files.get")
async def handle_agents_files_get(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Get agent file content"""
    from pathlib import Path
    filename = params.get("filename", "")
    agent_dir = Path.home() / ".openclaw" / "agents"
    filepath = agent_dir / filename
    if filepath.exists():
        return {"filename": filename, "content": filepath.read_text(encoding="utf-8")}
    raise FileNotFoundError(f"Agent file not found: {filename}")


@register_handler("agents.files.set")
async def handle_agents_files_set(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Set agent file content"""
    from pathlib import Path
    filename = params.get("filename", "")
    content = params.get("content", "")
    agent_dir = Path.home() / ".openclaw" / "agents"
    agent_dir.mkdir(parents=True, exist_ok=True)
    filepath = agent_dir / filename
    filepath.write_text(content, encoding="utf-8")
    return {"filename": filename, "written": True}


@register_handler("browser.request")
async def handle_browser_request(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Handle browser automation request"""
    action = params.get("action", "navigate")
    url = params.get("url")
    return {"action": action, "url": url, "status": "accepted"}


@register_handler("channels.status")
async def handle_channels_status(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Get channel connection status"""
    if not _channel_registry:
        return {"channels": []}

    channels = _channel_registry.get_all_channels()
    return {
        "channels": [
            {
                "id": ch["id"],
                "running": ch.get("running", False),
                "label": ch.get("label", ch["id"]),
                "connected": ch.get("connected", False),
                "state": ch.get("state", "unknown"),
            }
            for ch in channels
        ]
    }


@register_handler("channels.logout")
async def handle_channels_logout(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Logout from a channel"""
    channel_id = params.get("channelId")
    if not _channel_registry:
        raise RuntimeError("Channel registry not initialized")
    return {"channelId": channel_id, "loggedOut": True}


@register_handler("config.set")
async def handle_config_set(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Set full configuration"""
    from openclaw.gateway.config_service import get_config_service
    
    config_data = params.get("config", {})
    config_service = get_config_service()
    success = config_service.save_config(config_data)
    
    return {
        "set": success,
        "restartRequired": True  # Most config changes require restart
    }


@register_handler("config.patch")
async def handle_config_patch(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Apply patch to configuration"""
    from openclaw.gateway.config_service import get_config_service
    
    patch = params.get("patch", {})
    config_service = get_config_service()
    updated_config = config_service.patch_config(patch)
    
    return {
        "applied": len(patch),
        "restartRequired": True
    }


@register_handler("config.apply")
async def handle_config_apply(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Apply configuration (alias for config.set)"""
    return await handle_config_set(connection, params)


@register_handler("config.schema")
async def handle_config_schema(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Get configuration schema"""
    from openclaw.gateway.config_service import get_config_service
    
    config_service = get_config_service()
    schema = config_service.get_config_schema()
    
    # Add channels schema (matching TypeScript config.schema format)
    channels_schema = [
        {
            "id": "telegram",
            "label": "Telegram",
            "description": "Telegram bot channel integration",
            "configSchema": {
                "type": "object",
                "properties": {
                    "enabled": {"type": "boolean", "description": "Enable Telegram channel"},
                    "bot_token": {"type": "string", "description": "Telegram bot token"},
                    "owner_id": {"type": "string", "description": "Owner user ID"},
                    "allowed_user_ids": {"type": "array", "items": {"type": "string"}, "description": "Allowed user IDs"},
                    "group_activation_mode": {
                        "type": "string",
                        "enum": ["mention", "always"],
                        "description": "Group activation mode"
                    }
                },
                "required": ["bot_token"]
            },
            "configUiHints": {
                "bot_token": {"type": "password"}
            }
        },
        {
            "id": "discord",
            "label": "Discord",
            "description": "Discord bot channel integration",
            "configSchema": {
                "type": "object",
                "properties": {
                    "enabled": {"type": "boolean"},
                    "bot_token": {"type": "string"},
                },
                "required": ["bot_token"]
            },
            "configUiHints": {
                "bot_token": {"type": "password"}
            }
        },
        {
            "id": "slack",
            "label": "Slack",
            "description": "Slack bot channel integration",
            "configSchema": {
                "type": "object",
                "properties": {
                    "enabled": {"type": "boolean"},
                    "bot_token": {"type": "string"},
                    "app_token": {"type": "string"},
                },
                "required": ["bot_token"]
            },
            "configUiHints": {
                "bot_token": {"type": "password"},
                "app_token": {"type": "password"}
            }
        }
    ]
    
    schema["channels"] = channels_schema
    
    return {"schema": schema}


@register_handler("cron.list")
async def handle_cron_list(connection: Any, params: dict[str, Any]) -> list[dict[str, Any]]:
    """List cron jobs"""
    from openclaw.cron.service import get_cron_service
    cron_service = get_cron_service()
    return await cron_service.list_jobs()


@register_handler("cron.status")
async def handle_cron_status(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Get cron status"""
    from openclaw.cron.service import get_cron_service
    job_id = params.get("jobId")
    cron_service = get_cron_service()
    
    if job_id:
        status = cron_service.get_job_status(job_id)
        if not status:
            raise ValueError(f"Job not found: {job_id}")
        return status
    
    # Return overall status
    jobs = await cron_service.list_jobs()
    return {
        "enabled": True,
        "totalJobs": len(jobs),
        "jobs": jobs
    }


@register_handler("cron.add")
async def handle_cron_add(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """
    Add cron job (matches TypeScript API)
    
    Expects: { job: CronJobCreate }
    Returns: CronJob
    """
    from openclaw.cron.types import CronJob
    from openclaw.cron.service import get_cron_service
    from openclaw.cron.serialization import convert_job_to_api
    import uuid
    from datetime import datetime, UTC
    
    job_data = params.get("job", {})
    
    # Generate id if not provided
    if "id" not in job_data:
        job_data["id"] = str(uuid.uuid4())
    
    # Add timestamps if not provided
    now_ms = int(datetime.now(UTC).timestamp() * 1000)
    if "createdAtMs" not in job_data and "created_at_ms" not in job_data:
        job_data["created_at_ms"] = now_ms
    if "updatedAtMs" not in job_data and "updated_at_ms" not in job_data:
        job_data["updated_at_ms"] = now_ms
    
    # Convert from TypeScript format to Python format for CronJob.from_dict
    # This is needed because from_dict expects snake_case
    python_job_data = _convert_ts_to_python_job(job_data)
    
    # Create CronJob from dict
    job = CronJob.from_dict(python_job_data)
    
    # Add to service
    cron_service = get_cron_service()
    if not cron_service:
        raise RuntimeError("Cron service not available")
    
    created_job = await cron_service.add_job(job)
    
    # Convert back to TypeScript API format
    return convert_job_to_api(created_job.to_dict())


def _convert_ts_to_python_job(ts_job: dict[str, Any]) -> dict[str, Any]:
    """Convert TypeScript job format to Python format"""
    python_job = {}
    
    # Simple fields
    for ts_key, py_key in [
        ("id", "id"),
        ("name", "name"),
        ("description", "description"),
        ("enabled", "enabled"),
        ("agentId", "agent_id"),
        ("deleteAfterRun", "delete_after_run"),
        ("createdAtMs", "created_at_ms"),
        ("updatedAtMs", "updated_at_ms"),
        ("sessionTarget", "session_target"),
        ("wakeMode", "wake_mode"),
    ]:
        if ts_key in ts_job:
            python_job[py_key] = ts_job[ts_key]
    
    # Schedule (convert kind → type, etc.)
    if "schedule" in ts_job:
        ts_schedule = ts_job["schedule"]
        py_schedule = {"type": ts_schedule.get("kind", "at")}
        
        if ts_schedule.get("kind") == "at":
            py_schedule["timestamp"] = ts_schedule.get("at", "")
        elif ts_schedule.get("kind") == "every":
            py_schedule["interval_ms"] = ts_schedule.get("everyMs", 0)
            if "anchorMs" in ts_schedule:
                py_schedule["anchor"] = ts_schedule["anchorMs"]
        elif ts_schedule.get("kind") == "cron":
            py_schedule["expression"] = ts_schedule.get("expr", "")
            if "tz" in ts_schedule:
                py_schedule["timezone"] = ts_schedule["tz"]
        
        python_job["schedule"] = py_schedule
    
    # Payload (convert message → prompt, etc.)
    if "payload" in ts_job:
        ts_payload = ts_job["payload"]
        py_payload = {"kind": ts_payload.get("kind", "systemEvent")}
        
        if ts_payload.get("kind") == "systemEvent":
            py_payload["text"] = ts_payload.get("text", "")
        elif ts_payload.get("kind") == "agentTurn":
            py_payload["prompt"] = ts_payload.get("message", "")
            if "model" in ts_payload:
                py_payload["model"] = ts_payload["model"]
        
        python_job["payload"] = py_payload
    
    # Delivery (convert to → target, bestEffort → best_effort)
    if "delivery" in ts_job:
        ts_delivery = ts_job["delivery"]
        py_delivery = {"mode": ts_delivery.get("mode", "none")}
        
        if "channel" in ts_delivery:
            py_delivery["channel"] = ts_delivery["channel"]
        if "to" in ts_delivery:
            py_delivery["target"] = ts_delivery["to"]
        if "bestEffort" in ts_delivery:
            py_delivery["best_effort"] = ts_delivery["bestEffort"]
        
        python_job["delivery"] = py_delivery
    
    # State
    if "state" in ts_job:
        ts_state = ts_job["state"]
        py_state = {}
        for ts_key, py_key in [
            ("nextRunAtMs", "next_run_ms"),
            ("runningAtMs", "running_at_ms"),
            ("lastRunAtMs", "last_run_at_ms"),
            ("lastStatus", "last_status"),
            ("lastError", "last_error"),
            ("lastDurationMs", "last_duration_ms"),
        ]:
            if ts_key in ts_state:
                py_state[py_key] = ts_state[ts_key]
        
        python_job["state"] = py_state
    
    return python_job


@register_handler("cron.update")
async def handle_cron_update(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """
    Update cron job (matches TypeScript API)
    
    Expects: { id: string, patch: Partial<CronJob> }
    Returns: CronJob
    """
    from openclaw.cron.service import get_cron_service
    from openclaw.cron.serialization import convert_job_to_api
    from datetime import datetime, UTC
    
    job_id = params.get("jobId")
    if not job_id:
        raise ValueError("jobId is required")
    
    patch = params.get("patch", {})
    if not patch:
        raise ValueError("patch is required")
    
    # Convert TypeScript patch format to Python format
    python_patch = _convert_ts_to_python_job(patch)
    
    # Add updated timestamp
    python_patch["updated_at_ms"] = int(datetime.now(UTC).timestamp() * 1000)
    
    # Update via service
    cron_service = get_cron_service()
    if not cron_service:
        raise RuntimeError("Cron service not available")
    
    updated_job = await cron_service.update_job(job_id, python_patch)
    
    # Convert back to TypeScript API format
    return convert_job_to_api(updated_job.to_dict())


@register_handler("cron.remove")
async def handle_cron_remove(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Remove cron job"""
    from openclaw.cron.service import get_cron_service
    
    job_id = params.get("jobId")
    if not job_id:
        raise ValueError("jobId is required")
    
    cron_service = get_cron_service()
    result = await cron_service.remove_job(job_id)  # Added await
    
    return {"jobId": job_id, "removed": result.get("removed", False)}


@register_handler("cron.run")
async def handle_cron_run(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """
    Manually run cron job (matches TypeScript API)
    
    Expects: { jobId: string, mode?: "due" | "force" }
    Returns: { ok: boolean, ran: boolean, reason?: "not-due" }
    """
    from openclaw.cron.service import get_cron_service
    
    job_id = params.get("jobId")
    if not job_id:
        raise ValueError("jobId is required")
    
    mode = params.get("mode", "force")
    
    cron_service = get_cron_service()
    if not cron_service:
        raise RuntimeError("Cron service not available")
    
    # Use service's run method
    result = await cron_service.run(job_id, mode=mode)
    
    return result


@register_handler("cron.runs")
async def handle_cron_runs(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """List cron run history (matches TypeScript format)"""
    from openclaw.cron.service import get_cron_service
    from openclaw.cron.serialization import convert_run_log_entry_to_api
    
    job_id = params.get("jobId")
    limit = params.get("limit", 50)
    
    if not job_id:
        return {"entries": []}
    
    # Get cron service from gateway
    cron_service = get_cron_service()
    if not cron_service:
        logger.warning("Cron service not available")
        return {"entries": []}
    
    try:
        from openclaw.cron.store import CronRunLog
        
        # Read run log for the job
        run_log = CronRunLog(job_id, cron_service.store.store_path.parent / "runs")
        entries = run_log.read(limit=limit)
        
        # Convert to TypeScript API format
        api_entries = [convert_run_log_entry_to_api(entry) for entry in entries]
        
        return {"entries": api_entries}
    except Exception as e:
        logger.error(f"Failed to read cron runs: {e}", exc_info=True)
        return {"entries": []}


@register_handler("device.pair.list")
async def handle_device_pair_list(connection: Any, params: dict[str, Any]) -> list[dict[str, Any]]:
    """List paired devices and pending pairs"""
    from openclaw.devices.manager import get_device_manager
    
    device_manager = get_device_manager()
    devices = device_manager.list_devices()
    pending = device_manager.list_pending_pairs()
    
    return {
        "devices": devices,
        "pending": pending
    }


@register_handler("device.pair.approve")
async def handle_device_pair_approve(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Approve device pairing"""
    from openclaw.devices.manager import get_device_manager
    
    device_id = params.get("deviceId")
    label = params.get("label")
    
    device_manager = get_device_manager()
    token = device_manager.approve_pairing(device_id, label)
    
    return {
        "deviceId": device_id,
        "approved": token is not None,
        "token": token
    }


@register_handler("device.pair.reject")
async def handle_device_pair_reject(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Reject device pairing"""
    from openclaw.devices.manager import get_device_manager
    
    device_id = params.get("deviceId")
    reason = params.get("reason")
    
    device_manager = get_device_manager()
    device_manager.reject_pairing(device_id, reason)
    
    return {"deviceId": device_id, "rejected": True}


@register_handler("device.token.rotate")
async def handle_device_token_rotate(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Rotate device token"""
    from openclaw.devices.manager import get_device_manager
    
    device_id = params.get("deviceId")
    device_manager = get_device_manager()
    new_token = device_manager.rotate_token(device_id)
    
    return {
        "deviceId": device_id,
        "rotated": new_token is not None,
        "token": new_token
    }


@register_handler("device.token.revoke")
async def handle_device_token_revoke(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Revoke device token"""
    from openclaw.devices.manager import get_device_manager
    
    token = params.get("token")
    device_manager = get_device_manager()
    success = device_manager.revoke_token(token)
    
    return {"revoked": success}


@register_handler("exec.approval.request")
async def handle_exec_approval_request(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Request exec approval"""
    from openclaw.exec.approval_manager import get_approval_manager
    
    command = params.get("command", "")
    context = params.get("context", {})
    
    approval_manager = get_approval_manager()
    request_id = approval_manager.request_approval(command, context)
    
    return {
        "requestId": request_id,
        "command": command
    }


@register_handler("exec.approval.resolve")
async def handle_exec_approval_resolve(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Resolve exec approval"""
    from openclaw.exec.approval_manager import get_approval_manager
    
    request_id = params.get("requestId")
    approved = params.get("approved", False)
    approved_by = connection.auth_context.user
    
    approval_manager = get_approval_manager()
    
    if approved:
        success = approval_manager.approve(request_id, approved_by)
    else:
        success = approval_manager.reject(request_id, approved_by)
    
    return {
        "requestId": request_id,
        "approved": approved,
        "resolved": success
    }


@register_handler("exec.approvals.get")
async def handle_exec_approvals_get(connection: Any, params: dict[str, Any]) -> list[dict[str, Any]]:
    """Get pending exec approvals"""
    from openclaw.exec.approval_manager import get_approval_manager
    
    approval_manager = get_approval_manager()
    return approval_manager.list_pending()


@register_handler("exec.approvals.set")
async def handle_exec_approvals_set(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Set exec approval policies"""
    from openclaw.exec.approval_manager import get_approval_manager, ApprovalPolicy
    
    policy_id = params.get("policyId")
    policy_data = params.get("policy", {})
    
    policy = ApprovalPolicy(
        pattern=policy_data.get("pattern"),
        auto_approve=policy_data.get("autoApprove", False),
        require_approval=policy_data.get("requireApproval", True),
        allowed_users=policy_data.get("allowedUsers")
    )
    
    approval_manager = get_approval_manager()
    approval_manager.set_policy(policy_id, policy)
    
    return {"policyId": policy_id, "set": True}


@register_handler("logs.tail")
async def handle_logs_tail(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Tail gateway logs"""
    from pathlib import Path
    limit = params.get("limit", 200)
    log_file = Path.home() / ".openclaw" / "logs" / "gateway.log"
    lines = []
    if log_file.exists():
        with open(log_file) as f:
            lines = f.readlines()[-limit:]
    return {"lines": [l.rstrip() for l in lines]}


@register_handler("models.list")
async def handle_models_list(connection: Any, params: dict[str, Any]) -> list[dict[str, Any]]:
    """List available models"""
    config = connection.config
    models = []
    if config.agent:
        model_val = config.agent.model
        models.append({
            "name": "primary",
            "model": str(model_val) if isinstance(model_val, str) else model_val.primary,
            "type": "configured",
        })
    return models


@register_handler("node.list")
async def handle_node_list(connection: Any, params: dict[str, Any]) -> list[dict[str, Any]]:
    """List connected nodes"""
    from openclaw.nodes.manager import get_node_manager
    
    node_manager = get_node_manager()
    return node_manager.list_nodes()


@register_handler("node.describe")
async def handle_node_describe(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Describe a node"""
    from openclaw.nodes.manager import get_node_manager
    
    node_id = params.get("nodeId")
    node_manager = get_node_manager()
    node = node_manager.get_node(node_id)
    
    if not node:
        raise ValueError(f"Node not found: {node_id}")
    
    return {
        "nodeId": node.id,
        "capabilities": node.capabilities,
        "status": node.status,
        "metadata": node.metadata
    }


@register_handler("node.invoke")
async def handle_node_invoke(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Invoke a command on a node"""
    from openclaw.nodes.manager import get_node_manager
    
    node_id = params.get("nodeId")
    command = params.get("command", "")
    command_params = params.get("params", {})
    
    node_manager = get_node_manager()
    result = await node_manager.invoke_node(node_id, command, command_params)
    
    return result


@register_handler("node.pair.approve")
async def handle_node_pair_approve(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Approve node pairing"""
    from openclaw.nodes.manager import get_node_manager
    
    node_id = params.get("nodeId")
    node_manager = get_node_manager()
    token = node_manager.approve_pairing(node_id)
    
    return {
        "nodeId": node_id,
        "approved": token is not None,
        "token": token
    }


@register_handler("node.pair.reject")
async def handle_node_pair_reject(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Reject node pairing"""
    from openclaw.nodes.manager import get_node_manager
    
    node_id = params.get("nodeId")
    reason = params.get("reason")
    
    node_manager = get_node_manager()
    node_manager.reject_pairing(node_id, reason)
    
    return {"nodeId": node_id, "rejected": True}


@register_handler("sessions.preview")
async def handle_sessions_preview(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Preview session - using store-based implementation"""
    return await _sessions_preview_method.execute(connection, params)


@register_handler("sessions.resolve")
async def handle_sessions_resolve(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Resolve session key - using store-based implementation"""
    return await _sessions_resolve_method.execute(connection, params)


@register_handler("sessions.patch")
async def handle_sessions_patch(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Patch session metadata - using store-based implementation"""
    return await _sessions_patch_method.execute(connection, params)


@register_handler("sessions.reset")
async def handle_sessions_reset(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Reset session - using store-based implementation"""
    return await _sessions_reset_method.execute(connection, params)


@register_handler("sessions.delete")
async def handle_sessions_delete(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Delete session - using store-based implementation"""
    return await _sessions_delete_method.execute(connection, params)


@register_handler("sessions.compact")
async def handle_sessions_compact(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Compact session - using store-based implementation"""
    return await _sessions_compact_method.execute(connection, params)


@register_handler("skills.status")
async def handle_skills_status(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Get skills status"""
    from openclaw.agents.skills_status import build_workspace_skill_status
    from pathlib import Path
    
    agent_id = params.get("agentId", "main")
    workspace_dir = Path.home() / ".openclaw" / "workspace"
    
    config_dict = None
    if hasattr(connection, 'config'):
        if hasattr(connection.config, 'model_dump'):
            config_dict = connection.config.model_dump()
        elif isinstance(connection.config, dict):
            config_dict = connection.config
    
    return build_workspace_skill_status(workspace_dir, config_dict)


@register_handler("skills.install")
async def handle_skills_install(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Install a skill"""
    skill_name = params.get("name")
    return {"name": skill_name, "installed": True}


@register_handler("skills.update")
async def handle_skills_update(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Update a skill"""
    skill_name = params.get("name")
    return {"name": skill_name, "updated": True}


@register_handler("system")
async def handle_system(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Get system information"""
    import platform
    return {
        "platform": platform.system(),
        "python": platform.python_version(),
        "machine": platform.machine(),
        "hostname": platform.node(),
    }


@register_handler("talk")
async def handle_talk(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Voice talk handler"""
    return {"status": "not_configured"}


@register_handler("tts.status")
async def handle_tts_status(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Get TTS status"""
    return {"enabled": False, "provider": None}


@register_handler("tts.enable")
async def handle_tts_enable(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Enable TTS"""
    return {"enabled": True}


@register_handler("tts.disable")
async def handle_tts_disable(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Disable TTS"""
    return {"enabled": False}


@register_handler("tts.convert")
async def handle_tts_convert(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Convert text to speech"""
    text = params.get("text", "")
    return {"text": text, "status": "queued"}


@register_handler("tts.providers")
async def handle_tts_providers(connection: Any, params: dict[str, Any]) -> list[dict[str, Any]]:
    """List TTS providers"""
    return [
        {"name": "openai", "available": True},
        {"name": "elevenlabs", "available": False},
    ]


@register_handler("update.run")
async def handle_update_run(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Run update check"""
    return {"updateAvailable": False, "currentVersion": "1.0.0"}


@register_handler("usage.status")
async def handle_usage_status(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Get usage status"""
    return {"totalTokens": 0, "totalCost": 0.0, "sessions": 0}


@register_handler("usage.cost")
async def handle_usage_cost(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Get usage cost"""
    return {"total_tokens": 0, "total_cost": 0.0, "by_model": {}}


@register_handler("voicewake.get")
async def handle_voicewake_get(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Get voice wake status"""
    return {"enabled": False, "keyword": None}


@register_handler("voicewake.set")
async def handle_voicewake_set(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Set voice wake configuration"""
    enabled = params.get("enabled", False)
    keyword = params.get("keyword")
    return {"enabled": enabled, "keyword": keyword}


@register_handler("web.login.start")
async def handle_web_login_start(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Start web login flow"""
    return {"loginUrl": "http://localhost:18789/login", "token": "pending"}


@register_handler("web.login.wait")
async def handle_web_login_wait(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Wait for web login completion"""
    return {"authenticated": False}


@register_handler("wizard.start")
async def handle_wizard_start(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Start setup wizard"""
    if _wizard_handler:
        return await _wizard_handler.wizard_start(params)
    
    # Fallback if wizard handler not available
    from ..wizard.session import WizardSession
    try:
        session = WizardSession(
            mode=params.get("mode", "quickstart"),
            workspace=params.get("workspace")
        )
        return session.to_dict()
    except Exception as e:
        logger.error(f"Error starting wizard: {e}", exc_info=True)
        return {"error": str(e)}


@register_handler("wizard.next")
async def handle_wizard_next(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Advance wizard to next step"""
    if _wizard_handler:
        return await _wizard_handler.wizard_next(params)
    return {"error": "Wizard handler not available"}


@register_handler("wizard.cancel")
async def handle_wizard_cancel(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Cancel wizard session"""
    if _wizard_handler:
        return await _wizard_handler.wizard_cancel(params)
    return {"status": "cancelled"}


@register_handler("wizard.status")
async def handle_wizard_status(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Get wizard status"""
    if _wizard_handler:
        return await _wizard_handler.wizard_status(params)
    return {"error": "Wizard handler not available"}

# Additional Talk Mode handlers
@register_handler("talk.mode.get")
async def handle_talk_mode_get(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Get talk mode configuration"""
    return {
        "enabled": False,  # TODO: Get from config
        "provider": "openai",
        "model": "whisper-1",
        "language": "en",
    }


@register_handler("talk.mode.set")
async def handle_talk_mode_set(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Set talk mode configuration"""
    # TODO: Update config
    return {"success": True, "config": params}


# Node Management handlers
@register_handler("node.register")
async def handle_node_register(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Register a new node"""
    node_id = params.get("nodeId", "node-1")
    node_type = params.get("type", "compute")
    
    logger.info(f"Registering node: {node_id} ({node_type})")
    
    # TODO: Implement node registry
    return {
        "nodeId": node_id,
        "registered": True,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@register_handler("node.unregister")
async def handle_node_unregister(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Unregister a node"""
    node_id = params.get("nodeId")
    
    logger.info(f"Unregistering node: {node_id}")
    
    # TODO: Implement node unregistry
    return {"success": True, "nodeId": node_id}


@register_handler("node.status")
async def handle_node_status(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Get node status"""
    node_id = params.get("nodeId")
    
    return {
        "nodeId": node_id,
        "status": "online",
        "uptime": 0,
        "load": {"cpu": 0.0, "memory": 0.0},
    }


@register_handler("node.update")
async def handle_node_update(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Update node configuration"""
    node_id = params.get("nodeId")
    config = params.get("config", {})
    
    logger.info(f"Updating node {node_id}: {config}")
    
    return {"success": True, "nodeId": node_id}


@register_handler("node.capabilities")
async def handle_node_capabilities(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Get node capabilities"""
    node_id = params.get("nodeId")
    
    return {
        "nodeId": node_id,
        "capabilities": ["compute", "storage", "browser"],
    }


# Exec Approval handlers
@register_handler("exec.approval.list")
async def handle_exec_approval_list(connection: Any, params: dict[str, Any]) -> list[dict[str, Any]]:
    """List pending execution approvals"""
    # Get approval manager from gateway (would need to be added)
    if not connection.gateway or not hasattr(connection.gateway, 'approval_manager'):
        return []
    
    approval_manager = connection.gateway.approval_manager
    if not approval_manager:
        return []
    
    try:
        # Get all pending approvals
        return [
            {
                "id": req.id,
                "command": req.command,
                "context": req.context,
                "requestedAt": req.requested_at,
                "status": req.status
            }
            for req in approval_manager.pending_approvals.values()
            if req.status == "pending"
        ]
    except Exception as e:
        logger.error(f"Failed to list approvals: {e}", exc_info=True)
        return []


@register_handler("exec.approval.approve")
async def handle_exec_approval_approve(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Approve pending execution"""
    approval_id = params.get("approvalId")
    approved_by = params.get("approvedBy", "user")
    
    logger.info(f"Approving execution: {approval_id} by {approved_by}")
    
    # Get approval manager from gateway
    if not connection.gateway or not hasattr(connection.gateway, 'approval_manager'):
        return {"success": False, "error": "Approval manager not available"}
    
    approval_manager = connection.gateway.approval_manager
    if not approval_manager:
        return {"success": False, "error": "Approval manager not initialized"}
    
    try:
        # Approve the request
        success = approval_manager.approve(approval_id, approved_by=approved_by)
        
        return {
            "success": success,
            "approvalId": approval_id,
            "approvedBy": approved_by
        }
    except Exception as e:
        logger.error(f"Failed to approve: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@register_handler("exec.approval.deny")
async def handle_exec_approval_deny(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Deny pending execution"""
    approval_id = params.get("approvalId")
    reason = params.get("reason", "Denied by user")
    
    logger.info(f"Denying execution: {approval_id} - {reason}")
    
    return {"success": True, "approvalId": approval_id, "denied": True, "reason": reason}


@register_handler("exec.approval.timeout")
async def handle_exec_approval_timeout(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Get/set approval timeout"""
    if "timeout" in params:
        # Set timeout
        timeout = params["timeout"]
        logger.info(f"Setting approval timeout: {timeout}s")
        return {"success": True, "timeout": timeout}
    else:
        # Get timeout
        return {"timeout": 30}  # Default 30s


# System handlers
@register_handler("system.presence")
@register_handler("system-presence")  # Support hyphen format for frontend
async def handle_system_presence_list(connection: Any, params: dict[str, Any]) -> list[dict[str, Any]]:
    """List system presences"""
    try:
        from openclaw.infra.system_presence import list_system_presence
        return list_system_presence()
    except Exception as e:
        logger.error(f"Failed to get system presence: {e}", exc_info=True)
        # Return basic status if system_presence module fails
        return [{
            "online": True,
            "since": datetime.now(UTC).isoformat(),
            "connections": 1,
        }]


@register_handler("system.event")
async def handle_system_event(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Broadcast system event"""
    event_type = params.get("type", "notification")
    data = params.get("data", {})
    
    logger.info(f"Broadcasting system event: {event_type}")
    
    if not connection.gateway:
        return {"success": False, "error": "Gateway not available"}
    
    try:
        # Broadcast to all connected clients
        await connection.gateway.broadcast_event(event_type, data)
        return {
            "success": True,
            "type": event_type,
            "broadcasted": True,
            "connections": len(connection.gateway.connections)
        }
    except Exception as e:
        logger.error(f"Failed to broadcast event: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@register_handler("system.shutdown")
async def handle_system_shutdown(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Initiate graceful shutdown"""
    logger.warning("Shutdown requested")
    
    # TODO: Implement graceful shutdown
    return {"success": True, "shutting_down": True}


@register_handler("system.restart")
async def handle_system_restart(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Restart system"""
    logger.warning("Restart requested")
    
    # TODO: Implement restart
    return {"success": True, "restarting": True}


# Channel advanced handlers
@register_handler("channels.connect")
async def handle_channels_connect(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Connect a channel"""
    channel_id = params.get("channelId")
    
    logger.info(f"Connecting channel: {channel_id}")
    
    if not connection.gateway:
        return {"success": False, "error": "Gateway not available"}
    
    try:
        # Start the channel via channel_manager
        await connection.gateway.channel_manager.start_channel(channel_id)
        return {"success": True, "channelId": channel_id, "connected": True}
    except Exception as e:
        logger.error(f"Failed to connect channel: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@register_handler("channels.disconnect")
async def handle_channels_disconnect(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Disconnect a channel"""
    channel_id = params.get("channelId")
    
    logger.info(f"Disconnecting channel: {channel_id}")
    
    if not connection.gateway:
        return {"success": False, "error": "Gateway not available"}
    
    try:
        # Stop the channel via channel_manager
        await connection.gateway.channel_manager.stop_channel(channel_id)
        return {"success": True, "channelId": channel_id, "disconnected": True}
    except Exception as e:
        logger.error(f"Failed to disconnect channel: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@register_handler("channels.send")
async def handle_channels_send(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Send message via channel"""
    channel_id = params.get("channelId")
    target = params.get("target")
    text = params.get("text", "")
    
    logger.info(f"Sending via {channel_id} to {target}: {text[:50]}...")
    
    if not connection.gateway:
        return {"success": False, "error": "Gateway not available"}
    
    try:
        # Get channel from manager
        channel = connection.gateway.channel_manager.get_channel(channel_id)
        if not channel:
            return {"success": False, "error": f"Channel '{channel_id}' not found"}
        
        # Send message
        message_id = await channel.send_text(target=target, text=text)
        
        return {
            "success": True,
            "sent": True,
            "messageId": message_id or "sent",
            "channelId": channel_id,
            "target": target
        }
    except Exception as e:
        logger.error(f"Failed to send message: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# Memory handlers
@register_handler("memory.search")
async def handle_memory_search(connection: Any, params: dict[str, Any]) -> list[dict[str, Any]]:
    """Search memory using BuiltinMemoryManager"""
    query = params.get("query", "")
    limit = params.get("limit", 5)
    use_vector = params.get("useVector", False)
    use_hybrid = params.get("useHybrid", True)
    sources = params.get("sources")
    
    logger.info(f"Memory search: query='{query}', limit={limit}, vector={use_vector}, hybrid={use_hybrid}")
    
    # Get memory manager from gateway
    if not connection.gateway:
        logger.error("No gateway reference in connection")
        return []
    
    memory_manager = connection.gateway.get_memory_manager()
    if not memory_manager:
        logger.warning("Memory manager not available")
        return []
    
    try:
        # Convert source strings to MemorySource enum if provided
        from openclaw.memory.types import MemorySource
        source_enums = None
        if sources:
            source_enums = [MemorySource(s) for s in sources if s in [e.value for e in MemorySource]]
        
        # Perform search
        results = await memory_manager.search(
            query=query,
            limit=limit,
            sources=source_enums,
            use_vector=use_vector,
            use_hybrid=use_hybrid
        )
        
        # Convert results to dict format
        return [
            {
                "id": r.id,
                "path": r.path,
                "source": r.source.value,
                "text": r.text,
                "snippet": r.snippet,
                "startLine": r.start_line,
                "endLine": r.end_line,
                "score": r.score
            }
            for r in results
        ]
    except Exception as e:
        logger.error(f"Memory search failed: {e}", exc_info=True)
        return []


@register_handler("memory.add")
async def handle_memory_add(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Add content to memory"""
    content = params.get("content", "")
    source = params.get("source", "manual")
    file_path = params.get("filePath")
    
    logger.info(f"Adding to memory: content_len={len(content)}, source={source}, file_path={file_path}")
    
    # Get memory manager from gateway
    if not connection.gateway:
        logger.error("No gateway reference in connection")
        return {"success": False, "error": "Gateway not available"}
    
    memory_manager = connection.gateway.get_memory_manager()
    if not memory_manager:
        logger.warning("Memory manager not available")
        return {"success": False, "error": "Memory manager not initialized"}
    
    try:
        from openclaw.memory.types import MemorySource
        from pathlib import Path
        import tempfile
        
        # If file_path is provided, add the file directly
        if file_path:
            path = Path(file_path)
            if path.exists():
                source_enum = MemorySource(source) if source in [e.value for e in MemorySource] else MemorySource.MANUAL
                await memory_manager.add_file(str(path), source_enum)
                return {"success": True, "chunks": 1, "path": str(path)}
            else:
                return {"success": False, "error": f"File not found: {file_path}"}
        
        # Otherwise, create a temporary file with the content
        if content:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(content)
                temp_path = f.name
            
            try:
                source_enum = MemorySource(source) if source in [e.value for e in MemorySource] else MemorySource.MANUAL
                await memory_manager.add_file(temp_path, source_enum)
                return {"success": True, "chunks": 1, "path": temp_path}
            finally:
                # Clean up temp file
                Path(temp_path).unlink(missing_ok=True)
        
        return {"success": False, "error": "No content or file_path provided"}
        
    except Exception as e:
        logger.error(f"Failed to add to memory: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@register_handler("memory.sync")
async def handle_memory_sync(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Sync memory index (rebuild index from memory files)"""
    logger.info("Starting memory sync")
    
    # Get memory manager from gateway
    if not connection.gateway:
        logger.error("No gateway reference in connection")
        return {"success": False, "error": "Gateway not available"}
    
    memory_manager = connection.gateway.get_memory_manager()
    if not memory_manager:
        logger.warning("Memory manager not available")
        return {"success": False, "error": "Memory manager not initialized"}
    
    try:
        # Trigger sync (this would typically scan MEMORY.md files and re-index)
        await memory_manager.sync()
        return {"success": True, "syncing": True}
    except Exception as e:
        logger.error(f"Memory sync failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# Plugin handlers
@register_handler("plugins.list")
async def handle_plugins_list(connection: Any, params: dict[str, Any]) -> list[dict[str, Any]]:
    """List installed plugins (placeholder implementation)"""
    # Plugins system not fully implemented yet
    # Return empty list for now
    logger.debug("Plugins list requested - returning empty list (not yet implemented)")
    return []


@register_handler("plugins.install")
async def handle_plugins_install(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Install plugin (placeholder implementation)"""
    plugin_id = params.get("pluginId")
    
    logger.info(f"Plugin install requested: {plugin_id} (not yet implemented)")
    
    # Plugins system not fully implemented yet
    # Return success placeholder
    return {
        "success": False,
        "pluginId": plugin_id,
        "error": "Plugin system not yet implemented"
    }


@register_handler("plugins.uninstall")
async def handle_plugins_uninstall(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Uninstall plugin (placeholder implementation)"""
    plugin_id = params.get("pluginId")
    
    logger.info(f"Plugin uninstall requested: {plugin_id} (not yet implemented)")
    
    # Plugins system not fully implemented yet
    return {
        "success": False,
        "pluginId": plugin_id,
        "error": "Plugin system not yet implemented"
    }


@register_handler("plugins.enable")
async def handle_plugins_enable(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Enable plugin"""
    plugin_id = params.get("pluginId")
    
    return {"success": True, "pluginId": plugin_id, "enabled": True}


@register_handler("plugins.disable")
async def handle_plugins_disable(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Disable plugin"""
    plugin_id = params.get("pluginId")
    
    return {"success": True, "pluginId": plugin_id, "disabled": True}


logger.info(f"Registered {len(_handlers)} gateway handlers")

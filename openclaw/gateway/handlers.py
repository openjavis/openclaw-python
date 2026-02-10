"""Gateway method handlers"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

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
async def handle_sessions_list(connection: Any, params: dict[str, Any]) -> list[dict[str, Any]]:
    """List active sessions"""
    if not _session_manager:
        return []

    session_ids = _session_manager.list_sessions()
    sessions = []

    for session_id in session_ids:
        session = _session_manager.get_session(session_id)
        sessions.append(
            {
                "sessionId": session_id,
                "messageCount": len(session.messages),
                "lastMessage": session.messages[-1].timestamp if session.messages else None,
            }
        )

    return sessions


@register_handler("channels.list")
async def handle_channels_list(connection: Any, params: dict[str, Any]) -> list[dict[str, Any]]:
    """List available channels"""
    if not _channel_registry:
        return []

    channels = _channel_registry.list_channels()
    return [
        {
            "id": ch.id,
            "label": ch.label,
            "running": ch.is_running(),
            "capabilities": ch.capabilities.model_dump(),
        }
        for ch in channels
    ]


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
        run_id = f"run-{int(datetime.now(UTC).timestamp() * 1000)}"
        accepted_at = datetime.now(UTC).isoformat() + "Z"
        asyncio.create_task(_run_agent_turn(connection, run_id, session, message, tools, model))
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
    except Exception as e:
        logger.error(f"Agent turn error: {e}", exc_info=True)
        await connection.send_event("agent", {"runId": run_id, "type": "error", "error": str(e)})


@register_handler("chat.send")
async def handle_chat_send(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Send chat message"""
    text = params.get("text", "")
    session_id = params.get("sessionKey", "main")

    if not text:
        raise ValueError("text required")

    if not _session_manager:
        raise RuntimeError("Session manager not initialized")

    # Get session and add message
    session = _session_manager.get_session(session_id)
    session.add_user_message(text)

    message_id = f"msg-{int(datetime.now(UTC).timestamp() * 1000)}"

    return {"messageId": message_id}


@register_handler("chat.history")
async def handle_chat_history(connection: Any, params: dict[str, Any]) -> list[dict[str, Any]]:
    """Get chat history"""
    session_id = params.get("sessionKey", "main")
    limit = params.get("limit", 50)

    if not _session_manager:
        return []

    session = _session_manager.get_session(session_id)
    messages = session.get_messages(limit=limit)

    return [
        {"role": msg.role, "content": msg.content, "timestamp": msg.timestamp} for msg in messages
    ]


@register_handler("chat.inject")
async def handle_chat_inject(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Inject a system message into chat"""
    session_id = params.get("sessionKey", "main")
    text = params.get("text", "")
    role = params.get("role", "system")

    if not _session_manager:
        raise RuntimeError("Session manager not initialized")

    session = _session_manager.get_session(session_id)
    session.add_message(role, text)

    return {"injected": True}


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

    channels = _channel_registry.list_channels()
    return {
        "channels": [
            {"id": ch.id, "running": ch.is_running(), "label": ch.label}
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
    """Set configuration value"""
    key = params.get("key", "")
    value = params.get("value")
    return {"key": key, "set": True}


@register_handler("config.patch")
async def handle_config_patch(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Apply JSON patch to configuration"""
    patch = params.get("patch", [])
    return {"applied": len(patch)}


@register_handler("config.apply")
async def handle_config_apply(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Apply full configuration"""
    config_data = params.get("config", {})
    return {"applied": True}


@register_handler("cron.list")
async def handle_cron_list(connection: Any, params: dict[str, Any]) -> list[dict[str, Any]]:
    """List cron jobs"""
    return []


@register_handler("cron.status")
async def handle_cron_status(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Get cron status"""
    return {"enabled": True, "jobs": 0}


@register_handler("cron.add")
async def handle_cron_add(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Add cron job"""
    schedule = params.get("schedule", "")
    prompt = params.get("prompt", "")
    return {"schedule": schedule, "added": True}


@register_handler("cron.update")
async def handle_cron_update(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Update cron job"""
    job_id = params.get("jobId")
    return {"jobId": job_id, "updated": True}


@register_handler("cron.remove")
async def handle_cron_remove(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Remove cron job"""
    job_id = params.get("jobId")
    return {"jobId": job_id, "removed": True}


@register_handler("cron.run")
async def handle_cron_run(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Manually run cron job"""
    job_id = params.get("jobId")
    return {"jobId": job_id, "ran": True}


@register_handler("cron.runs")
async def handle_cron_runs(connection: Any, params: dict[str, Any]) -> list[dict[str, Any]]:
    """List cron run history"""
    return []


@register_handler("device.pair.list")
async def handle_device_pair_list(connection: Any, params: dict[str, Any]) -> list[dict[str, Any]]:
    """List paired devices"""
    return []


@register_handler("device.pair.approve")
async def handle_device_pair_approve(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Approve device pairing"""
    device_id = params.get("deviceId")
    return {"deviceId": device_id, "approved": True}


@register_handler("device.pair.reject")
async def handle_device_pair_reject(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Reject device pairing"""
    device_id = params.get("deviceId")
    return {"deviceId": device_id, "rejected": True}


@register_handler("device.token.rotate")
async def handle_device_token_rotate(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Rotate device token"""
    device_id = params.get("deviceId")
    return {"deviceId": device_id, "rotated": True}


@register_handler("device.token.revoke")
async def handle_device_token_revoke(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Revoke device token"""
    device_id = params.get("deviceId")
    return {"deviceId": device_id, "revoked": True}


@register_handler("exec.approval.request")
async def handle_exec_approval_request(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Request exec approval"""
    command = params.get("command", "")
    return {"command": command, "requestId": f"req-{int(datetime.now(UTC).timestamp())}"}


@register_handler("exec.approval.resolve")
async def handle_exec_approval_resolve(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Resolve exec approval"""
    request_id = params.get("requestId")
    approved = params.get("approved", False)
    return {"requestId": request_id, "approved": approved}


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
    return []


@register_handler("node.describe")
async def handle_node_describe(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Describe a node"""
    node_id = params.get("nodeId")
    return {"nodeId": node_id, "capabilities": []}


@register_handler("node.invoke")
async def handle_node_invoke(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Invoke a command on a node"""
    node_id = params.get("nodeId")
    method = params.get("method")
    return {"nodeId": node_id, "method": method, "status": "accepted"}


@register_handler("sessions.preview")
async def handle_sessions_preview(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Preview session"""
    session_key = params.get("sessionKey", "main")
    if not _session_manager:
        return {"sessionKey": session_key, "messages": []}
    session = _session_manager.get_session(session_key)
    messages = session.get_messages(limit=5)
    return {
        "sessionKey": session_key,
        "messages": [{"role": m.role, "content": m.content[:100]} for m in messages],
    }


@register_handler("sessions.resolve")
async def handle_sessions_resolve(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Resolve session key"""
    session_key = params.get("sessionKey", "main")
    return {"sessionKey": session_key, "resolved": True}


@register_handler("sessions.patch")
async def handle_sessions_patch(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Patch session metadata"""
    session_key = params.get("sessionKey", "main")
    patch = params.get("patch", {})
    return {"sessionKey": session_key, "patched": True}


@register_handler("sessions.reset")
async def handle_sessions_reset(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Reset session"""
    session_key = params.get("sessionKey", "main")
    if _session_manager:
        _session_manager.clear_session(session_key)
    return {"sessionKey": session_key, "reset": True}


@register_handler("sessions.delete")
async def handle_sessions_delete(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Delete session"""
    session_key = params.get("sessionKey", "main")
    if _session_manager:
        _session_manager.clear_session(session_key)
    return {"sessionKey": session_key, "deleted": True}


@register_handler("sessions.compact")
async def handle_sessions_compact(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Compact session (reduce context)"""
    session_key = params.get("sessionKey", "main")
    return {"sessionKey": session_key, "compacted": True}


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
    # TODO: Implement approval queue
    return []


@register_handler("exec.approval.approve")
async def handle_exec_approval_approve(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Approve pending execution"""
    approval_id = params.get("approvalId")
    
    logger.info(f"Approving execution: {approval_id}")
    
    # TODO: Execute approved command
    return {"success": True, "approvalId": approval_id, "executed": True}


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
async def handle_system_presence(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """System presence/online status"""
    return {
        "online": True,
        "since": datetime.now(UTC).isoformat(),
        "connections": 1,
    }


@register_handler("system.event")
async def handle_system_event(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Broadcast system event"""
    event_type = params.get("type", "notification")
    data = params.get("data", {})
    
    logger.info(f"System event: {event_type}")
    
    # TODO: Broadcast to all connections
    return {"success": True, "type": event_type, "broadcasted": True}


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
    
    # TODO: Connect channel
    return {"success": True, "channelId": channel_id, "connected": True}


@register_handler("channels.disconnect")
async def handle_channels_disconnect(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Disconnect a channel"""
    channel_id = params.get("channelId")
    
    logger.info(f"Disconnecting channel: {channel_id}")
    
    # TODO: Disconnect channel
    return {"success": True, "channelId": channel_id, "disconnected": True}


@register_handler("channels.send")
async def handle_channels_send(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Send message via channel"""
    channel_id = params.get("channelId")
    target = params.get("target")
    text = params.get("text", "")
    
    logger.info(f"Sending via {channel_id} to {target}")
    
    # TODO: Send message
    return {"success": True, "sent": True, "messageId": "msg-1"}


# Memory handlers
@register_handler("memory.search")
async def handle_memory_search(connection: Any, params: dict[str, Any]) -> list[dict[str, Any]]:
    """Search memory"""
    query = params.get("query", "")
    limit = params.get("limit", 5)
    use_vector = params.get("useVector", False)
    
    logger.info(f"Memory search: {query} (vector={use_vector})")
    
    # TODO: Implement memory search
    return []


@register_handler("memory.add")
async def handle_memory_add(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Add to memory"""
    content = params.get("content", "")
    source = params.get("source", "manual")
    
    logger.info(f"Adding to memory: {len(content)} chars")
    
    # TODO: Add to memory
    return {"success": True, "chunks": 1}


@register_handler("memory.sync")
async def handle_memory_sync(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Sync memory index"""
    logger.info("Starting memory sync")
    
    # TODO: Trigger memory sync
    return {"success": True, "syncing": True}


# Plugin handlers
@register_handler("plugins.list")
async def handle_plugins_list(connection: Any, params: dict[str, Any]) -> list[dict[str, Any]]:
    """List installed plugins"""
    # TODO: List plugins
    return []


@register_handler("plugins.install")
async def handle_plugins_install(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Install plugin"""
    plugin_id = params.get("pluginId")
    
    logger.info(f"Installing plugin: {plugin_id}")
    
    # TODO: Install plugin
    return {"success": True, "pluginId": plugin_id, "installed": True}


@register_handler("plugins.uninstall")
async def handle_plugins_uninstall(connection: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Uninstall plugin"""
    plugin_id = params.get("pluginId")
    
    logger.info(f"Uninstalling plugin: {plugin_id}")
    
    # TODO: Uninstall plugin
    return {"success": True, "pluginId": plugin_id, "uninstalled": True}


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

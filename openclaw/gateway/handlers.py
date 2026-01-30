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


def set_global_instances(session_manager, tool_registry, channel_registry, agent_runtime):
    """Set global instances for handlers to use"""
    global _session_manager, _tool_registry, _channel_registry, _agent_runtime
    _session_manager = session_manager
    _tool_registry = tool_registry
    _channel_registry = channel_registry
    _agent_runtime = agent_runtime


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
            "count": len(connection.config.agents.list) if connection.config.agents.list else 0
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
    """Run agent turn"""
    message = params.get("message", "")
    session_id = params.get("sessionId") or params.get("sessionKey", "main")
    model = params.get("model")

    if not message:
        raise ValueError("message required")

    if not _agent_runtime or not _session_manager or not _tool_registry:
        raise RuntimeError("Agent runtime not initialized")

    # Get session
    session = _session_manager.get_session(session_id)

    # Get tools
    tools = _tool_registry.list_tools()

    # Create run ID
    run_id = f"run-{int(datetime.now(UTC).timestamp() * 1000)}"
    accepted_at = datetime.now(UTC).isoformat() + "Z"

    # Execute agent turn in background
    asyncio.create_task(_run_agent_turn(connection, run_id, session, message, tools, model))

    return {"runId": run_id, "acceptedAt": accepted_at}


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

"""Session management tools"""

import logging
from typing import Any

from ..session import SessionManager
from .base import AgentTool, ToolResult

logger = logging.getLogger(__name__)


class SessionsListTool(AgentTool):
    """List all sessions"""

    def __init__(self, session_manager: SessionManager):
        super().__init__()
        self.name = "sessions_list"
        self.description = "List all available sessions with their message counts"
        self.session_manager = session_manager

    def get_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}, "required": []}

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        """List sessions"""
        try:
            session_ids = self.session_manager.list_sessions()

            sessions_info = []
            for session_id in session_ids:
                session = self.session_manager.get_session(session_id)
                sessions_info.append(
                    {
                        "session_id": session_id,
                        "message_count": len(session.messages),
                        "last_message": (
                            session.messages[-1].timestamp if session.messages else None
                        ),
                    }
                )

            # Format output
            if sessions_info:
                output = f"Found {len(sessions_info)} session(s):\n\n"
                for info in sessions_info:
                    output += f"- **{info['session_id']}**: {info['message_count']} messages"
                    if info["last_message"]:
                        output += f" (last: {info['last_message']})"
                    output += "\n"
            else:
                output = "No sessions found"

            return ToolResult(success=True, content=output, metadata={"sessions": sessions_info})

        except Exception as e:
            logger.error(f"Sessions list error: {e}", exc_info=True)
            return ToolResult(success=False, content="", error=str(e))


class SessionsHistoryTool(AgentTool):
    """Get session history"""

    def __init__(self, session_manager: SessionManager):
        super().__init__()
        self.name = "sessions_history"
        self.description = "Get conversation history from a session"
        self.session_manager = session_manager

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session ID to get history from"},
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of messages to return",
                    "default": 50,
                },
            },
            "required": ["session_id"],
        }

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        """Get session history"""
        session_id = params.get("session_id", "")
        limit = params.get("limit", 50)

        if not session_id:
            return ToolResult(success=False, content="", error="session_id required")

        try:
            session = self.session_manager.get_session(session_id)
            messages = session.get_messages(limit=limit)

            if not messages:
                return ToolResult(
                    success=True,
                    content=f"No messages in session '{session_id}'",
                    metadata={"session_id": session_id, "count": 0},
                )

            # Format messages
            output = f"Session '{session_id}' history ({len(messages)} messages):\n\n"
            for msg in messages:
                output += f"**{msg.role.upper()}** ({msg.timestamp}):\n{msg.content}\n\n"

            return ToolResult(
                success=True,
                content=output,
                metadata={"session_id": session_id, "count": len(messages)},
            )

        except Exception as e:
            logger.error(f"Sessions history error: {e}", exc_info=True)
            return ToolResult(success=False, content="", error=str(e))


class SessionsSendTool(AgentTool):
    """Send message to another session (agent-to-agent communication)"""

    def __init__(self, session_manager: SessionManager):
        super().__init__()
        self.name = "sessions_send"
        self.description = "Send a message to another session for agent-to-agent communication"
        self.session_manager = session_manager

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Target session ID"},
                "message": {"type": "string", "description": "Message content to send"},
                "from_session": {
                    "type": "string",
                    "description": "Source session ID",
                    "default": "system",
                },
            },
            "required": ["session_id", "message"],
        }

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        """Send message to session"""
        session_id = params.get("session_id", "")
        message = params.get("message", "")
        from_session = params.get("from_session", "system")

        if not session_id or not message:
            return ToolResult(success=False, content="", error="session_id and message required")

        try:
            # Get target session
            session = self.session_manager.get_session(session_id)

            # Add message as user message with metadata
            prefix = f"[From {from_session}] "
            session.add_user_message(prefix + message)

            return ToolResult(
                success=True,
                content=f"Message sent to session '{session_id}'",
                metadata={"session_id": session_id, "from_session": from_session},
            )

        except Exception as e:
            logger.error(f"Sessions send error: {e}", exc_info=True)
            return ToolResult(success=False, content="", error=str(e))


class SessionsSpawnTool(AgentTool):
    """Spawn a new session"""

    def __init__(self, session_manager: SessionManager):
        super().__init__()
        self.name = "sessions_spawn"
        self.description = "Create a new session with optional initial context"
        self.session_manager = session_manager

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "New session ID (optional, will generate if not provided)",
                },
                "initial_message": {
                    "type": "string",
                    "description": "Initial message to seed the session",
                },
            },
            "required": [],
        }

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        """Spawn new session"""
        session_id = params.get("session_id") or f"spawned-{int(__import__('time').time())}"
        initial_message = params.get("initial_message")

        try:
            # Create session
            session = self.session_manager.get_session(session_id)

            # Add initial message if provided
            if initial_message:
                session.add_user_message(initial_message)

            return ToolResult(
                success=True,
                content=f"Created new session '{session_id}'",
                metadata={"session_id": session_id, "has_initial_message": bool(initial_message)},
            )

        except Exception as e:
            logger.error(f"Sessions spawn error: {e}", exc_info=True)
            return ToolResult(success=False, content="", error=str(e))

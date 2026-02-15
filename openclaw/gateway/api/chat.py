"""
Gateway Chat Methods - Aligned with TypeScript openclaw/src/gateway/server-methods/chat.ts

Implements WebSocket RPC methods for chat interactions:
- chat.send: Send message and execute agent
- chat.history: Get chat history from session
- chat.abort: Abort running agent execution
- chat.inject: Inject message into session transcript
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..server import GatewayConnection

logger = logging.getLogger(__name__)


# =============================================================================
# Helper Functions
# =============================================================================

def resolve_transcript_path(
    session_id: str,
    sessions_dir: Path,
    session_file: str | None = None,
) -> Path:
    """Resolve transcript file path for session"""
    if session_file:
        return Path(session_file)
    return sessions_dir / f"{session_id}.jsonl"


def ensure_transcript_file(transcript_path: Path, session_id: str) -> tuple[bool, str | None]:
    """Ensure transcript file exists"""
    if transcript_path.exists():
        return True, None
    
    try:
        transcript_path.parent.mkdir(parents=True, exist_ok=True)
        # Write session header
        header = {
            "type": "session",
            "version": 1,
            "id": session_id,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(header) + "\n")
        return True, None
    except Exception as e:
        return False, str(e)


def read_session_messages(transcript_path: Path, limit: int = 200) -> list[dict[str, Any]]:
    """Read messages from session transcript"""
    if not transcript_path.exists():
        return []
    
    messages = []
    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    entry = json.loads(line)
                    if entry.get("type") == "message" and "message" in entry:
                        messages.append(entry["message"])
                except json.JSONDecodeError:
                    continue
        
        # Return last N messages
        return messages[-limit:] if len(messages) > limit else messages
    
    except Exception as e:
        logger.error(f"Failed to read session messages: {e}")
        return []


def append_message_to_transcript(
    transcript_path: Path,
    message: dict[str, Any],
    create_if_missing: bool = True,
) -> tuple[bool, str | None, str | None]:
    """
    Append message to transcript
    
    Returns:
        (success, message_id, error)
    """
    message_id = str(uuid.uuid4())[:8]
    now = datetime.now(UTC)
    
    # Ensure file exists
    if not transcript_path.exists() and create_if_missing:
        # Extract session_id from path (filename without .jsonl)
        session_id = transcript_path.stem
        success, error = ensure_transcript_file(transcript_path, session_id)
        if not success:
            return False, None, error
    
    # Build transcript entry
    entry = {
        "type": "message",
        "id": message_id,
        "timestamp": now.isoformat(),
        "message": message,
    }
    
    try:
        with open(transcript_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        return True, message_id, None
    except Exception as e:
        return False, None, str(e)


def broadcast_chat_event(
    connection: GatewayConnection,
    event_type: str,  # "delta" | "final" | "error" | "aborted" | "start"
    run_id: str,
    session_key: str,
    message: dict[str, Any] | None = None,
    error_message: str | None = None,
    text: str | None = None,  # For delta events
) -> None:
    """Broadcast chat event to WebSocket clients"""
    payload: dict[str, Any] = {
        "runId": run_id,
        "sessionKey": session_key,
        "state": event_type,
    }
    
    # For delta events with text, create a proper message structure
    if text is not None and event_type == "delta":
        payload["message"] = {
            "role": "assistant",
            "content": [{"type": "text", "text": text}],
            "timestamp": int(datetime.now(UTC).timestamp() * 1000),
        }
    elif message is not None:
        payload["message"] = message
    
    if error_message is not None:
        payload["errorMessage"] = error_message
    
    # Broadcast to all connected clients
    if connection.gateway:
        asyncio.create_task(connection.gateway.broadcast_event("chat", payload))


# =============================================================================
# Chat Method Implementations
# =============================================================================

class ChatHistoryMethod:
    """Get chat history from session"""
    
    name = "chat.history"
    description = "Get chat history for a session"
    category = "chat"
    
    async def execute(self, connection: GatewayConnection, params: dict[str, Any]) -> dict[str, Any]:
        """
        Get chat history
        
        Args:
            params: {
                "sessionKey": str,
                "limit": int (optional, default 200)
            }
        
        Returns:
            {
                "sessionKey": str,
                "sessionId": str,
                "messages": list,
                "thinkingLevel": str | None,
                "verboseLevel": str | None
            }
        """
        session_key = params.get("sessionKey")
        limit = params.get("limit", 200)
        
        if not session_key:
            raise ValueError("sessionKey is required")
        
        # Get session manager from gateway
        if not connection.gateway or not connection.gateway.channel_manager:
            return {
                "sessionKey": session_key,
                "sessionId": session_key,
                "messages": [],
            }
        
        session_manager = connection.gateway.channel_manager.session_manager
        if not session_manager:
            return {
                "sessionKey": session_key,
                "sessionId": session_key,
                "messages": [],
            }
        
        # Get or create session to get the real session_id (use session_key parameter properly)
        session = session_manager.get_or_create_session(session_key=session_key)
        session_id = session.session_id
        logger.info(f"chat.history using session: key={session_key}, id={session_id}")
        
        # Read messages from transcript
        # Check if sessions_dir attribute exists
        if not hasattr(session_manager, 'sessions_dir'):
            logger.error(f"SessionManager has no sessions_dir! Type: {type(session_manager)}, attrs: {dir(session_manager)}")
            # Fallback to _sessions_dir
            sessions_dir = Path(getattr(session_manager, '_sessions_dir', Path.home() / ".openclaw" / ".sessions"))
        else:
            sessions_dir = Path(session_manager.sessions_dir)
        transcript_path = resolve_transcript_path(session_id, sessions_dir)
        logger.info(f"chat.history: sessionKey={session_key}, sessionId={session_id}, transcript={transcript_path}")
        messages = read_session_messages(transcript_path, limit=min(limit, 1000))
        
        return {
            "sessionKey": session_key,
            "sessionId": session_id,
            "messages": messages,
            "thinkingLevel": None,
            "verboseLevel": None,
        }


class ChatSendMethod:
    """Send chat message and execute agent"""
    
    name = "chat.send"
    description = "Send message and execute agent"
    category = "chat"
    
    async def execute(self, connection: GatewayConnection, params: dict[str, Any]) -> dict[str, Any]:
        """
        Send message and execute agent
        
        Args:
            params: {
                "sessionKey": str,
                "message": str,
                "deliver": bool (optional),
                "idempotencyKey": str,
                "attachments": list (optional)
            }
        
        Returns:
            {
                "runId": str,
                "status": "started" | "error"
            }
        """
        logger.info(f"chat.send params: {list(params.keys())}")
        logger.debug(f"chat.send full params: {params}")
        
        session_key = params.get("sessionKey")
        message = params.get("message", "").strip()
        idempotency_key = params.get("idempotencyKey")
        attachments = params.get("attachments", [])
        
        if not session_key:
            raise ValueError("sessionKey is required")
        
        if not idempotency_key:
            raise ValueError("idempotencyKey is required")
        
        if not message and not attachments:
            raise ValueError("message or attachments required")
        
        # Get gateway and channel manager
        if not connection.gateway or not connection.gateway.channel_manager:
            raise RuntimeError("Gateway not initialized")
        
        channel_manager = connection.gateway.channel_manager
        run_id = idempotency_key
        
        # Get session manager
        session_manager = channel_manager.session_manager
        if not session_manager:
            raise RuntimeError("Session manager not available")
        
        # Get or create session (use session_key parameter properly)
        session = session_manager.get_or_create_session(session_key=session_key)
        session_id = session.session_id
        logger.info(f"chat.send using session: key={session_key}, id={session_id}")
        
        # Append user message to transcript
        # Check if sessions_dir attribute exists (fallback to _sessions_dir)
        if hasattr(session_manager, 'sessions_dir'):
            sessions_dir = Path(session_manager.sessions_dir)
        else:
            sessions_dir = Path(getattr(session_manager, '_sessions_dir', Path.home() / ".openclaw" / ".sessions"))
        transcript_path = resolve_transcript_path(session_id, sessions_dir)
        
        # Build user message
        now = datetime.now(UTC)
        user_message_content = []
        
        if message:
            user_message_content.append({"type": "text", "text": message})
        
        # Handle attachments (images)
        if attachments:
            for att in attachments:
                if att.get("type") == "image":
                    user_message_content.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": att.get("mimeType", "image/jpeg"),
                            "data": att.get("content", ""),
                        },
                    })
        
        user_message = {
            "role": "user",
            "content": user_message_content,
            "timestamp": int(now.timestamp() * 1000),
        }
        
        # Append user message to transcript IMMEDIATELY
        logger.info(f"Appending user message to transcript: {transcript_path}")
        success, msg_id, error = append_message_to_transcript(
            transcript_path, user_message, create_if_missing=True
        )
        
        if not success:
            logger.error(f"Failed to append user message to transcript: {error}")
            # Still continue with agent execution, but record the error
        else:
            logger.info(f"User message saved successfully: {msg_id}")
        
        # Send "started" response immediately
        asyncio.create_task(connection.send_response(
            params.get("__request_id", run_id),
            payload={"runId": run_id, "status": "started"}
        ))
        
        # Execute agent asynchronously
        asyncio.create_task(self._execute_agent_turn(
            connection=connection,
            channel_manager=channel_manager,
            session=session,
            session_key=session_key,
            session_id=session_id,
            message=message,
            run_id=run_id,
            transcript_path=transcript_path,
        ))
        
        # Return acknowledgment (already sent via send_response above)
        return {"runId": run_id, "status": "started"}
    
    async def _execute_agent_turn(
        self,
        connection: GatewayConnection,
        channel_manager: Any,
        session: Any,
        session_key: str,
        session_id: str,
        message: str,
        run_id: str,
        transcript_path: Path,
    ) -> None:
        """Execute agent turn asynchronously"""
        try:
            # Get agent runtime
            runtime = channel_manager.default_runtime
            if not runtime:
                raise RuntimeError("Agent runtime not available")
            
            # Get tools from gateway
            tools = []
            if hasattr(connection.gateway, 'tools') and connection.gateway.tools:
                tools = connection.gateway.tools
            elif hasattr(connection.gateway, 'tool_registry') and connection.gateway.tool_registry:
                tools = connection.gateway.tool_registry.list_tools()
            
            logger.info(f"🔧 Loaded {len(tools)} tools for agent turn")
            
            # Execute agent turn - runtime.run_turn will load session history internally
            logger.info(f"Executing agent turn for session {session_key}, run_id={run_id}, message={message[:50]}...")
            
            # Broadcast start event
            broadcast_chat_event(connection, "start", run_id, session_key)
            
            # Stream response
            assistant_response = ""
            tool_calls_log = []
            
            async for event in runtime.run_turn(session, message, tools):
                event_type_str = str(event.type).split(".")[-1] if hasattr(event.type, 'value') else str(event.type)
                logger.info(f"Received event: type={event_type_str}, has_data={hasattr(event, 'data')}")
                
                # Get event data
                event_data = event.data if hasattr(event, 'data') else (event.payload if hasattr(event, 'payload') else {})
                
                if event_type_str in ("AGENT_TEXT", "TEXT_DELTA", "text_delta"):
                    # Accumulate text and broadcast delta
                    # Handle both {"text": "..."} and {"delta": {"text": "..."}}
                    text_chunk = ""
                    if isinstance(event_data.get("text"), str):
                        text_chunk = event_data["text"]
                    elif isinstance(event_data.get("delta"), dict):
                        text_chunk = event_data["delta"].get("text", "")
                    elif isinstance(event_data.get("delta"), str):
                        text_chunk = event_data["delta"]
                    
                    if text_chunk:
                        assistant_response += text_chunk
                        # Broadcast text delta
                        broadcast_chat_event(connection, "delta", run_id, session_key, text=text_chunk)
                        logger.info(f"Broadcasting text delta: {text_chunk[:50]}...")
                
                elif event_type_str in ("TOOL_USE", "tool_use"):
                    # Tool called
                    if event_data:
                        tool_calls_log.append(event_data)
                        logger.info(f"Tool called: {event_data.get('name', 'unknown')}")
                
                elif event_type_str in ("AGENT_TURN_COMPLETE", "TURN_END", "turn_complete"):
                    # Agent turn completed
                    logger.info(f"Agent turn completed for {session_key}, accumulated text: {len(assistant_response)} chars")
                    break
                
                elif event_type_str in ("ERROR", "error"):
                    # Error occurred
                    error_msg = event_data.get("message", "Unknown error") if event_data else "Unknown error"
                    logger.error(f"Agent error: {error_msg}")
                    broadcast_chat_event(
                        connection, "error", run_id, session_key, error_message=error_msg
                    )
                    return
            
            # Build assistant message
            logger.info(f"Building final message with {len(assistant_response)} chars")
            now = datetime.now(UTC)
            assistant_message = {
                "role": "assistant",
                "content": [{"type": "text", "text": assistant_response}],
                "timestamp": int(now.timestamp() * 1000),
                "stopReason": "end_turn",
            }
            
            # Append to transcript
            logger.info(f"Appending assistant message to transcript: {transcript_path}")
            success, msg_id, error = append_message_to_transcript(
                transcript_path, assistant_message, create_if_missing=False
            )
            
            if not success:
                logger.warning(f"Failed to append assistant message: {error}")
            else:
                logger.info(f"Successfully appended message {msg_id}")
            
            # Broadcast final event
            logger.info(f"Broadcasting final event for run_id={run_id}")
            broadcast_chat_event(
                connection, "final", run_id, session_key, message=assistant_message
            )
            logger.info(f"Final event broadcast complete")
            
        except Exception as e:
            logger.error(f"Agent execution failed: {e}", exc_info=True)
            broadcast_chat_event(
                connection, "error", run_id, session_key, error_message=str(e)
            )


class ChatAbortMethod:
    """Abort running agent execution"""
    
    name = "chat.abort"
    description = "Abort running agent execution"
    category = "chat"
    
    async def execute(self, connection: GatewayConnection, params: dict[str, Any]) -> dict[str, Any]:
        """
        Abort agent execution
        
        Args:
            params: {
                "sessionKey": str,
                "runId": str (optional)
            }
        
        Returns:
            {
                "ok": true,
                "aborted": bool,
                "runIds": list[str]
            }
        """
        session_key = params.get("sessionKey")
        run_id = params.get("runId")
        
        if not session_key:
            raise ValueError("sessionKey is required")
        
        # TODO: Implement abort controller management
        # For now, just acknowledge
        
        return {
            "ok": True,
            "aborted": False,
            "runIds": [],
        }


class ChatInjectMethod:
    """Inject message into session transcript"""
    
    name = "chat.inject"
    description = "Inject message into session transcript"
    category = "chat"
    
    async def execute(self, connection: GatewayConnection, params: dict[str, Any]) -> dict[str, Any]:
        """
        Inject message into transcript
        
        Args:
            params: {
                "sessionKey": str,
                "message": str,
                "label": str (optional)
            }
        
        Returns:
            {
                "ok": true,
                "messageId": str
            }
        """
        session_key = params.get("sessionKey")
        message_text = params.get("message", "").strip()
        label = params.get("label")
        
        if not session_key:
            raise ValueError("sessionKey is required")
        
        if not message_text:
            raise ValueError("message is required")
        
        # Get session manager
        if not connection.gateway or not connection.gateway.channel_manager:
            raise RuntimeError("Gateway not initialized")
        
        session_manager = connection.gateway.channel_manager.session_manager
        if not session_manager:
            raise RuntimeError("Session manager not available")
        
        # Get session
        session = session_manager.get_or_create_session(session_key)
        session_id = session.session_id
        
        # Build message
        now = datetime.now(UTC)
        label_prefix = f"[{label}]\n\n" if label else ""
        message_body = {
            "role": "assistant",
            "content": [{"type": "text", "text": f"{label_prefix}{message_text}"}],
            "timestamp": int(now.timestamp() * 1000),
            "stopReason": "injected",
            "usage": {"input": 0, "output": 0, "totalTokens": 0},
        }
        
        # Append to transcript
        sessions_dir = Path(session_manager.sessions_dir)
        transcript_path = resolve_transcript_path(session_id, sessions_dir)
        
        success, message_id, error = append_message_to_transcript(
            transcript_path, message_body, create_if_missing=True
        )
        
        if not success:
            raise RuntimeError(f"Failed to write transcript: {error}")
        
        # Broadcast to WebSocket clients
        broadcast_chat_event(
            connection, "final", f"inject-{message_id}", session_key, message=message_body
        )
        
        return {
            "ok": True,
            "messageId": message_id,
        }


# =============================================================================
# Export all chat methods
# =============================================================================

CHAT_METHODS = [
    ChatHistoryMethod(),
    ChatSendMethod(),
    ChatAbortMethod(),
    ChatInjectMethod(),
]

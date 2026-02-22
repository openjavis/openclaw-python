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


_MAX_TEXT_BLOCK_CHARS = 12_000   # Per text-content block
_MAX_MESSAGE_BYTES = 128 * 1024  # 128 KB per message


def _sanitize_history_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Sanitize history messages before sending to clients.

    Mirrors TypeScript chat.history sanitization:
    - Truncates individual text blocks to 12K chars
    - Enforces 128KB budget per message
    - Removes sensitive / internal fields
    """
    result = []
    for msg in messages:
        msg = dict(msg)  # shallow copy

        # Remove sensitive internal fields
        msg.pop("_internal", None)
        msg.pop("systemPrompt", None)

        # Sanitize content blocks
        content = msg.get("content")
        if isinstance(content, list):
            sanitized_content = []
            budget = _MAX_MESSAGE_BYTES
            for block in content:
                if not isinstance(block, dict):
                    sanitized_content.append(block)
                    continue
                block = dict(block)
                if block.get("type") == "text":
                    text = block.get("text", "")
                    if len(text) > _MAX_TEXT_BLOCK_CHARS:
                        block["text"] = text[:_MAX_TEXT_BLOCK_CHARS] + "…[truncated]"
                block_bytes = len(json.dumps(block).encode())
                if block_bytes <= budget:
                    sanitized_content.append(block)
                    budget -= block_bytes
                # else: drop the block – over budget
            msg["content"] = sanitized_content

        result.append(msg)
    return result


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

        # Sanitize messages — mirrors TypeScript chat.history sanitization
        messages = _sanitize_history_messages(messages)

        # Resolve thinkingLevel and verboseLevel from SessionEntry
        thinking_level: str | None = None
        verbose_level: str | None = None
        try:
            entry = session_manager.get_session_entry(session_key)
            if entry:
                thinking_level = getattr(entry, "thinkingLevel", None)
                verbose_level = getattr(entry, "verboseLevel", None)
        except Exception:
            pass

        return {
            "sessionKey": session_key,
            "sessionId": session_id,
            "messages": messages,
            "thinkingLevel": thinking_level,
            "verboseLevel": verbose_level,
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
        
        # Create agent task and register for abort support
        task = asyncio.create_task(self._execute_agent_turn(
            connection=connection,
            channel_manager=channel_manager,
            session=session,
            session_key=session_key,
            session_id=session_id,
            message=message,
            run_id=run_id,
            transcript_path=transcript_path,
        ))

        # Tag task with metadata so abort can find it by session_key
        task._openclaw_meta = {"session_key": session_key, "run_id": run_id}  # type: ignore[attr-defined]

        # Register in gateway.active_runs for abort support
        if connection.gateway:
            if not hasattr(connection.gateway, "active_runs"):
                connection.gateway.active_runs = {}
            connection.gateway.active_runs[run_id] = task

            # Register with chat_registry if available
            chat_registry = getattr(connection.gateway, "chat_registry", None)
            if chat_registry is not None:
                chat_registry.add_run(
                    run_id=run_id,
                    client_run_id=idempotency_key,
                    session_key=session_key,
                    conn_id=getattr(connection, "id", ""),
                )

            # Clean up registration when task completes
            def _cleanup(t: asyncio.Task) -> None:
                if connection.gateway:
                    connection.gateway.active_runs.pop(run_id, None)
            task.add_done_callback(_cleanup)

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
            
            # Execute agent turn using AgentSession (pi-ai style)
            logger.info(f"Executing agent turn for session {session_key}, run_id={run_id}, message={message[:50]}...")
            
            # Broadcast start event
            broadcast_chat_event(connection, "start", run_id, session_key)
            
            # Import AgentSession
            from openclaw.agents.agent_session import AgentSession
            
            # Create AgentSession (pi-ai style automatic tool loop)
            agent_session = AgentSession(
                session=session,
                runtime=runtime,
                tools=tools,
                system_prompt=None,  # System prompt already in runtime
                max_iterations=5,
                max_tokens=4096,
                max_turns=None,
            )
            
            # Stream response
            assistant_response = ""
            tool_calls_log = []
            
            # Collect events from AgentSession
            events_queue = []
            
            def collect_event(event):
                """Collect events synchronously"""
                events_queue.append(event)
            
            # Subscribe to events
            unsubscribe = agent_session.subscribe(collect_event)
            
            try:
                # Execute prompt (pi-ai style)
                await agent_session.prompt(message)
                
                # Process collected events
                for event in events_queue:
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
                    
                    elif event_type_str in ("ERROR", "error"):
                        # Error occurred
                        error_msg = event_data.get("message", "Unknown error") if event_data else "Unknown error"
                        logger.error(f"Agent error: {error_msg}")
                        broadcast_chat_event(
                            connection, "error", run_id, session_key, error_message=error_msg
                        )
                
                logger.info(f"Processed all {len(events_queue)} events from AgentSession")
            
            finally:
                # Unsubscribe from events
                unsubscribe()
            
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
    """Abort running agent execution.

    Mirrors TypeScript chat.abort:
    1. Look up run by sessionKey or runId in gateway.active_runs
    2. Cancel the asyncio Task (or set abort Event)
    3. Collect partial snapshot from run buffer
    4. Persist aborted-partial to transcript
    5. Broadcast abort-completion event
    """

    name = "chat.abort"
    description = "Abort running agent execution"
    category = "chat"

    async def execute(self, connection: GatewayConnection, params: dict[str, Any]) -> dict[str, Any]:
        """
        Abort agent execution.

        Args:
            params: {
                "sessionKey": str,
                "runId": str (optional)
            }

        Returns:
            {"ok": True, "aborted": bool, "runIds": list[str]}
        """
        session_key = params.get("sessionKey")
        run_id = params.get("runId")

        if not session_key:
            raise ValueError("sessionKey is required")

        if not connection.gateway:
            return {"ok": True, "aborted": False, "runIds": []}

        aborted_run_ids: list[str] = []

        # -------------------------------------------------------------------
        # 1. Find matching active runs
        # -------------------------------------------------------------------
        active_runs: dict[str, asyncio.Task] = getattr(connection.gateway, "active_runs", {})
        chat_registry = getattr(connection.gateway, "chat_registry", None)

        # Build list of run_ids to abort
        target_run_ids: list[str] = []
        if run_id and run_id in active_runs:
            target_run_ids.append(run_id)
        else:
            # Abort all runs matching session_key
            for rid, task in list(active_runs.items()):
                task_meta = getattr(task, "_openclaw_meta", {})
                if task_meta.get("session_key") == session_key:
                    target_run_ids.append(rid)

        # -------------------------------------------------------------------
        # 2. Abort each run
        # -------------------------------------------------------------------
        for rid in target_run_ids:
            task = active_runs.get(rid)
            partial_text = ""

            # Signal abort via registry abort event (preferred)
            if chat_registry is not None:
                chat_registry.abort_run(rid)
                partial_text = "".join(chat_registry.get_buffer(rid))
                chat_registry.clear_buffer(rid)

            # Cancel the asyncio Task
            if task and not task.done():
                task.cancel()
                try:
                    await asyncio.wait_for(asyncio.shield(task), timeout=3.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass

            # Remove from active_runs
            active_runs.pop(rid, None)
            aborted_run_ids.append(rid)

            # -------------------------------------------------------------------
            # 3. Persist partial snapshot to transcript
            # -------------------------------------------------------------------
            if partial_text:
                try:
                    gw = connection.gateway
                    session_manager = getattr(
                        getattr(gw, "channel_manager", None), "session_manager", None
                    )
                    if session_manager:
                        session = session_manager.get_or_create_session(session_key=session_key)
                        sessions_dir = Path(
                            getattr(session_manager, "sessions_dir",
                                    getattr(session_manager, "_sessions_dir",
                                            Path.home() / ".openclaw" / ".sessions"))
                        )
                        transcript_path = resolve_transcript_path(session.session_id, sessions_dir)
                        now = datetime.now(UTC)
                        aborted_msg = {
                            "role": "assistant",
                            "content": [{"type": "text", "text": partial_text}],
                            "timestamp": int(now.timestamp() * 1000),
                            "stopReason": "aborted",
                        }
                        append_message_to_transcript(transcript_path, aborted_msg, create_if_missing=False)
                except Exception as exc:
                    logger.warning(f"Failed to persist partial abort snapshot: {exc}")

            # -------------------------------------------------------------------
            # 4. Broadcast abort event
            # -------------------------------------------------------------------
            if connection.gateway:
                abort_payload: dict[str, Any] = {
                    "runId": rid,
                    "sessionKey": session_key,
                    "state": "aborted",
                }
                if partial_text:
                    abort_payload["message"] = {
                        "role": "assistant",
                        "content": [{"type": "text", "text": partial_text}],
                        "stopReason": "aborted",
                    }
                asyncio.create_task(
                    connection.gateway.broadcast_event("chat", abort_payload)
                )

        return {
            "ok": True,
            "aborted": len(aborted_run_ids) > 0,
            "runIds": aborted_run_ids,
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

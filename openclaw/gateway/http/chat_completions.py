"""
OpenAI-compatible chat completions endpoint.

Provides /v1/chat/completions endpoint matching OpenAI's API format.
Disabled by default, enable via config: gateway.http.endpoints.chatCompletions.enabled

Reference: openclaw/docs/gateway/http-openai-chat-completions.md
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any, AsyncIterator

from pydantic import BaseModel, Field


class ChatCompletionRequest(BaseModel):
    """OpenAI chat completion request"""
    
    model: str  # "openclaw:<agentId>" or just model name
    messages: list[dict[str, Any]]
    stream: bool = False
    user: str | None = None  # For stable session routing
    temperature: float | None = None
    max_tokens: int | None = None
    top_p: float | None = None
    n: int = 1
    stop: str | list[str] | None = None
    presence_penalty: float = 0
    frequency_penalty: float = 0


class ChatCompletionResponse(BaseModel):
    """OpenAI chat completion response"""
    
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[dict[str, Any]]
    usage: dict[str, int] | None = None


class ChatCompletionStreamChunk(BaseModel):
    """OpenAI chat completion stream chunk"""
    
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: list[dict[str, Any]]


def parse_agent_id(model: str) -> str:
    """
    Parse agent ID from model string.
    
    Args:
        model: Model string (e.g., "openclaw:main" or "gpt-4")
        
    Returns:
        Agent ID
    """
    if model.startswith("openclaw:"):
        return model.split(":", 1)[1]
    return "main"  # Default agent


def resolve_session_key(agent_id: str, user: str | None) -> str:
    """
    Resolve session key for request.
    
    Args:
        agent_id: Agent ID
        user: OpenAI user field (for stable sessions)
        
    Returns:
        Session key
    """
    if user:
        # Stable session using user field
        # Hash user to create stable session key
        import hashlib
        user_hash = hashlib.sha256(user.encode()).hexdigest()[:16]
        return f"agent:{agent_id}:openai:{user_hash}"
    else:
        # Stateless - use ephemeral session
        return f"agent:{agent_id}:openai:ephemeral"


def convert_openai_messages(messages: list[dict]) -> list[dict]:
    """
    Convert OpenAI message format to agent format.
    
    Args:
        messages: OpenAI messages
        
    Returns:
        Agent messages
    """
    agent_messages = []
    
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        
        if role == "system":
            # System messages typically merged into system prompt
            continue
        elif role == "user":
            agent_messages.append({
                "role": "user",
                "content": content
            })
        elif role == "assistant":
            agent_messages.append({
                "role": "assistant",
                "content": content
            })
        elif role == "function":
            # Function results
            agent_messages.append({
                "role": "toolResult",
                "content": content,
                "toolName": msg.get("name", "unknown")
            })
    
    return agent_messages


def format_openai_response(
    run_id: str,
    model: str,
    content: str,
    usage: dict | None = None
) -> dict:
    """
    Format response in OpenAI format.
    
    Args:
        run_id: Run ID
        model: Model name
        content: Response content
        usage: Token usage
        
    Returns:
        OpenAI-formatted response
    """
    return {
        "id": run_id,
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": content
            },
            "finish_reason": "stop"
        }],
        "usage": usage or {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }
    }


async def stream_agent_events(
    agent_runtime,
    session_key: str,
    messages: list[dict],
    model: str,
    run_id: str
) -> AsyncIterator[str]:
    """
    Stream agent events in SSE format.
    
    Args:
        agent_runtime: Agent runtime
        session_key: Session key
        messages: Messages to send
        model: Model name
        run_id: Run ID
        
    Yields:
        SSE-formatted chunks
    """
    try:
        # Run agent turn
        async for event in agent_runtime.run_turn(
            session_key=session_key,
            messages=messages,
            stream=True
        ):
            # Convert agent event to OpenAI stream chunk
            if event.type == "agent_text":
                chunk = {
                    "id": run_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": model,
                    "choices": [{
                        "index": 0,
                        "delta": {
                            "content": event.data.get("text", "")
                        },
                        "finish_reason": None
                    }]
                }
                yield f"data: {json.dumps(chunk)}\n\n"
        
        # Send final chunk
        final_chunk = {
            "id": run_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model,
            "choices": [{
                "index": 0,
                "delta": {},
                "finish_reason": "stop"
            }]
        }
        yield f"data: {json.dumps(final_chunk)}\n\n"
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        # Send error
        error_chunk = {
            "error": {
                "message": str(e),
                "type": "server_error",
                "code": "internal_error"
            }
        }
        yield f"data: {json.dumps(error_chunk)}\n\n"


async def handle_chat_completions(
    request: ChatCompletionRequest,
    agent_runtime,
    authorization: str | None = None,
    x_openclaw_agent_id: str | None = None
) -> dict | AsyncIterator[str]:
    """
    Handle OpenAI chat completions request.
    
    Args:
        request: Chat completion request
        agent_runtime: Agent runtime
        authorization: Authorization header
        x_openclaw_agent_id: Optional agent ID header
        
    Returns:
        Response dict or SSE stream
    """
    # Parse agent ID
    agent_id = x_openclaw_agent_id or parse_agent_id(request.model)
    
    # Resolve session key
    session_key = resolve_session_key(agent_id, request.user)
    
    # Convert messages
    agent_messages = convert_openai_messages(request.messages)
    
    # Generate run ID
    import uuid
    run_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    
    if request.stream:
        # Return SSE stream
        return stream_agent_events(
            agent_runtime,
            session_key,
            agent_messages,
            request.model,
            run_id
        )
    else:
        # Run synchronously
        content_parts = []
        usage = None
        
        async for event in agent_runtime.run_turn(
            session_key=session_key,
            messages=agent_messages,
            stream=False
        ):
            if event.type == "agent_text":
                content_parts.append(event.data.get("text", ""))
            elif event.type == "agent_usage":
                usage = event.data
        
        content = "".join(content_parts)
        return format_openai_response(run_id, request.model, content, usage)


__all__ = [
    "ChatCompletionRequest",
    "ChatCompletionResponse",
    "ChatCompletionStreamChunk",
    "handle_chat_completions",
]

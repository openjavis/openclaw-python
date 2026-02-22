"""pi_ai stream_simple adapter for openclaw-python.

Thin adapter that maps openclaw session/tool representation to
pi_ai.stream_simple, replacing the legacy MultiProviderRuntime + providers/.

Architecture::

    openclaw AgentSession
         ↓  calls
    PiStreamAdapter.stream_turn(messages, tools, opts)
         ↓  calls
    pi_ai.stream_simple(model, context, opts)
         ↓  yields
    pi_ai AssistantMessageEvent hierarchy
         ↓  converted by
    PiStreamAdapter → openclaw Events

Mirrors how attempt.ts calls streamSimple() from @pi-ai.
"""
from __future__ import annotations

import logging
import time
from typing import Any, AsyncIterator

from pi_ai import get_model, stream_simple
from pi_ai.types import (
    AssistantMessage,
    Context,
    EventDone,
    EventError,
    EventTextDelta,
    EventToolCallEnd,
    EventThinkingDelta,
    Model,
    SimpleStreamOptions,
    TextContent,
    Tool,
    ToolCall,
    UserMessage,
)

from openclaw.events import Event, EventType

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Model resolution
# ---------------------------------------------------------------------------

# Fallback models ordered by preference
_FALLBACK_MODEL_PAIRS = [
    ("google", "gemini-2.0-flash"),
    ("anthropic", "claude-3-5-sonnet-20241022"),
    ("openai", "gpt-4o"),
]


def _resolve_model(model_str: str) -> Model:
    """Resolve a 'provider/model-id' string to a pi_ai Model object.

    Falls back to gemini-2.0-flash if the requested model is not in the
    registry (e.g. a model added after this build).
    """
    if "/" in model_str:
        provider, model_id = model_str.split("/", 1)
    else:
        # Bare model name — guess provider from prefix
        lower = model_str.lower()
        if "gemini" in lower or "google" in lower:
            provider, model_id = "google", model_str
        elif "claude" in lower or "haiku" in lower or "sonnet" in lower or "opus" in lower:
            provider, model_id = "anthropic", model_str
        else:
            provider, model_id = "openai", model_str

    try:
        return get_model(provider, model_id)
    except KeyError:
        pass

    # Try fallbacks
    for fp, fid in _FALLBACK_MODEL_PAIRS:
        try:
            return get_model(fp, fid)
        except KeyError:
            continue

    raise ValueError(f"Could not resolve any model for {model_str!r}")


# ---------------------------------------------------------------------------
# Message conversion: openclaw → pi_ai
# ---------------------------------------------------------------------------

def _now_ms() -> int:
    return int(time.time() * 1000)


def _to_pi_user_message(text: str) -> UserMessage:
    return UserMessage(role="user", content=text, timestamp=_now_ms())


def _to_pi_messages(history: list[dict[str, Any]]) -> list[Any]:
    """Convert openclaw history dicts to pi_ai message objects."""
    result: list[Any] = []
    ts = _now_ms()
    for msg in history:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if isinstance(content, list):
            # Extract text from list of content blocks
            text_parts = []
            for blk in content:
                if isinstance(blk, dict) and blk.get("type") == "text":
                    text_parts.append(blk.get("text", ""))
                elif isinstance(blk, str):
                    text_parts.append(blk)
            content_str = " ".join(text_parts)
        else:
            content_str = str(content)

        if role == "user":
            result.append(UserMessage(role="user", content=content_str, timestamp=ts))
        # tool/assistant roles are handled by pi_coding_agent internally;
        # for the pure stream adapter we only pass user messages.
    return result


def _to_pi_tools(tools: list[Any]) -> list[Tool]:
    """Convert openclaw tool objects to pi_ai Tool objects."""
    result: list[Tool] = []
    for tool in tools:
        if isinstance(tool, Tool):
            result.append(tool)
            continue

        name = ""
        description = ""
        parameters: dict[str, Any] = {"type": "object", "properties": {}}

        if hasattr(tool, "to_dict"):
            spec = tool.to_dict()
            name = spec.get("name", "")
            description = spec.get("description", "")
            parameters = spec.get("parameters", spec.get("input_schema", parameters))
        elif hasattr(tool, "schema"):
            name = getattr(tool, "name", str(tool))
            description = getattr(tool, "description", "")
            parameters = tool.schema()
        elif isinstance(tool, dict):
            name = tool.get("name", "")
            description = tool.get("description", "")
            parameters = tool.get("parameters", tool.get("input_schema", parameters))
        else:
            name = getattr(tool, "name", str(tool))
            description = getattr(tool, "description", "")

        if name:
            result.append(Tool(name=name, description=description, parameters=parameters))
    return result


# ---------------------------------------------------------------------------
# Main adapter
# ---------------------------------------------------------------------------

class PiStreamAdapter:
    """Thin adapter that calls pi_ai.stream_simple and converts events.

    Replaces providers/ + MultiProviderRuntime for openclaw's LLM calls.
    Mirrors how attempt.ts calls streamSimple() from @pi-ai.

    Usage::

        adapter = PiStreamAdapter(model="google/gemini-2.0-flash")
        async for event in adapter.stream_turn(messages, tools, system_prompt):
            ...
    """

    def __init__(
        self,
        model: str = "google/gemini-2.0-flash",
        max_tokens: int = 8192,
        temperature: float | None = None,
        reasoning: str | None = None,
    ) -> None:
        self.model_str = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.reasoning = reasoning

    async def stream_turn(
        self,
        history: list[dict[str, Any]],
        tools: list[Any],
        system_prompt: str | None = None,
        *,
        session_id: str | None = None,
    ) -> AsyncIterator[Event]:
        """Stream a single LLM turn using pi_ai.stream_simple.

        Args:
            history: List of openclaw message dicts (role/content).
            tools: List of openclaw tool objects.
            system_prompt: Optional system prompt string.
            session_id: Used for pi_ai session tracking.

        Yields:
            openclaw Event objects.
        """
        try:
            model = _resolve_model(self.model_str)
        except ValueError as exc:
            yield Event(
                type=EventType.ERROR,
                source="pi-stream-adapter",
                session_id=session_id or "",
                data={"message": str(exc)},
            )
            return

        pi_messages = _to_pi_messages(history)
        pi_tools = _to_pi_tools(tools) or None

        context = Context(
            system_prompt=system_prompt,
            messages=pi_messages,
            tools=pi_tools,
        )

        opts = SimpleStreamOptions(
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            session_id=session_id,
        )

        try:
            async for event in stream_simple(model, context, opts):
                converted = _convert_event(event, session_id or "")
                if converted is not None:
                    yield converted
        except Exception as exc:
            logger.error("PiStreamAdapter error: %s", exc, exc_info=True)
            yield Event(
                type=EventType.ERROR,
                source="pi-stream-adapter",
                session_id=session_id or "",
                data={"message": str(exc)},
            )


# ---------------------------------------------------------------------------
# Event conversion: pi_ai → openclaw
# ---------------------------------------------------------------------------

def _convert_event(event: Any, session_id: str) -> Event | None:
    """Convert a pi_ai AssistantMessageEvent to an openclaw Event."""
    etype = getattr(event, "type", None)

    if etype == "text_delta":
        ev: EventTextDelta = event
        return Event(
            type=EventType.TEXT,
            source="pi-stream-adapter",
            session_id=session_id,
            data={"delta": {"text": ev.delta}},
        )

    if etype == "thinking_delta":
        ev_think: EventThinkingDelta = event
        return Event(
            type=EventType.THINKING_UPDATE,
            source="pi-stream-adapter",
            session_id=session_id,
            data={"delta": {"text": ev_think.delta}},
        )

    if etype == "toolcall_end":
        ev_tc: EventToolCallEnd = event
        tc: ToolCall = ev_tc.tool_call
        return Event(
            type=EventType.TOOL_EXECUTION_START,
            source="pi-stream-adapter",
            session_id=session_id,
            data={
                "tool_name": tc.name,
                "tool_call_id": tc.id,
                "arguments": tc.arguments,
            },
        )

    if etype == "done":
        ev_done: EventDone = event
        stop_reason = ev_done.reason
        return Event(
            type=EventType.AGENT_TURN_COMPLETE,
            source="pi-stream-adapter",
            session_id=session_id,
            data={
                "stop_reason": stop_reason,
                "usage": {
                    "input_tokens": ev_done.message.usage.input,
                    "output_tokens": ev_done.message.usage.output,
                },
            },
        )

    if etype == "error":
        ev_err: EventError = event
        err_msg = ""
        if ev_err.error and ev_err.error.error_message:
            err_msg = ev_err.error.error_message
        return Event(
            type=EventType.ERROR,
            source="pi-stream-adapter",
            session_id=session_id,
            data={"message": err_msg, "reason": ev_err.reason},
        )

    # text_start / text_end / toolcall_start / toolcall_delta / start — skip
    return None


__all__ = ["PiStreamAdapter", "_to_pi_messages", "_to_pi_tools", "_resolve_model"]

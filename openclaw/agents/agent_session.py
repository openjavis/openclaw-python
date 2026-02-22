"""Agent Session — thin adapter over pi_coding_agent.AgentSession.

Replaces the legacy ToolLoopOrchestrator + MultiProviderRuntime stack with
the tested pi-mono-python infrastructure, while preserving openclaw's
channel/gateway hooks and session-key routing.

Mirrors how attempt.ts wraps createAgentSession() + SessionManager from
@pi-coding-agent (openclaw/src/agents/pi-embedded-runner/run/attempt.ts).

Hook lifecycle (preserved for gateway/channel hooks):
    session_start          – before any LLM call in this turn
    before_prompt_build    – before system prompt is assembled
    before_agent_start     – just before the first LLM call
    before_model_resolve   – before the model name is finalized
    llm_input              – the messages array sent to the LLM
    llm_output             – the raw LLM response
    before_tool_call       – before each tool is invoked
    after_tool_call        – after each tool completes
    tool_result_persist    – before tool result is written to transcript
    before_message_write   – before assistant message is saved
    agent_end              – after the full agent loop finishes
    session_end            – cleanup hook
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Hook registry (preserved for gateway integration)
# ---------------------------------------------------------------------------

class HookRegistry:
    """Manages lifecycle hooks for an AgentSession."""

    def __init__(self) -> None:
        self._hooks: dict[str, list[Callable]] = {}

    def register(self, hook_name: str, fn: Callable) -> None:
        self._hooks.setdefault(hook_name, []).append(fn)

    def unregister(self, hook_name: str, fn: Callable) -> None:
        lst = self._hooks.get(hook_name, [])
        if fn in lst:
            lst.remove(fn)

    async def run(self, hook_name: str, context: dict) -> dict:
        """Run all hooks and return updated context."""
        for fn in self._hooks.get(hook_name, []):
            try:
                if asyncio.iscoroutinefunction(fn):
                    result = await fn(context)
                else:
                    result = fn(context)
                if isinstance(result, dict):
                    context = {**context, **result}
            except Exception as exc:
                logger.warning("Hook %r raised: %s", hook_name, exc, exc_info=True)
        return context


# ---------------------------------------------------------------------------
# Event conversion: pi_agent AgentEvent → openclaw Event
# ---------------------------------------------------------------------------

def _convert_pi_event(pi_event: Any, session_id: str) -> Any | None:
    """Convert a pi_agent AgentEvent to an openclaw Event."""
    from openclaw.events import Event, EventType

    etype = getattr(pi_event, "type", None)
    if etype is None:
        return None

    # Agent lifecycle → pass-through (type strings match)
    if etype in ("agent_start", "agent_end", "turn_start", "turn_end",
                 "message_start", "message_end"):
        try:
            et = EventType(etype)
            return Event(type=et, source="pi-session", session_id=session_id, data={})
        except ValueError:
            return None

    # message_update → extract inner AssistantMessageEvent
    if etype == "message_update":
        ame = getattr(pi_event, "assistant_message_event", None)
        if ame is None:
            return None
        ame_type = getattr(ame, "type", None)
        if ame_type == "text_delta":
            return Event(
                type=EventType.TEXT,
                source="pi-session",
                session_id=session_id,
                data={"delta": {"text": getattr(ame, "delta", "")}},
            )
        if ame_type == "thinking_delta":
            return Event(
                type=EventType.THINKING_UPDATE,
                source="pi-session",
                session_id=session_id,
                data={"delta": {"text": getattr(ame, "delta", "")}},
            )
        return None

    # Tool events → pass-through (type strings match openclaw EventType values)
    if etype in ("tool_execution_start", "tool_execution_update", "tool_execution_end"):
        try:
            et = EventType(etype)
        except ValueError:
            return None
        data: dict[str, Any] = {
            "tool_call_id": getattr(pi_event, "tool_call_id", ""),
            "tool_name": getattr(pi_event, "tool_name", ""),
        }
        if etype == "tool_execution_start":
            data["arguments"] = getattr(pi_event, "args", {})
        elif etype == "tool_execution_end":
            data["result"] = str(getattr(pi_event, "result", ""))
            data["is_error"] = bool(getattr(pi_event, "is_error", False))
        return Event(type=et, source="pi-session", session_id=session_id, data=data)

    # auto_retry / auto_compaction synthetic events from pi AgentSession
    if etype in ("auto_retry_start", "auto_retry_end",
                 "auto_compaction_start", "auto_compaction_end"):
        return None  # internal pi events — don't forward to openclaw

    return None


# ---------------------------------------------------------------------------
# Tool adapter: openclaw AgentToolBase → pi_agent AgentTool
# ---------------------------------------------------------------------------

def _wrap_openclaw_tool(oc_tool: Any) -> Any:
    """Wrap an openclaw tool in a pi_agent.AgentTool-compatible object."""
    from pi_agent.types import AgentTool, AgentToolResult
    from pi_ai.types import TextContent

    name = getattr(oc_tool, "name", str(oc_tool))
    description = getattr(oc_tool, "description", "")
    label = getattr(oc_tool, "label", name)
    parameters: dict[str, Any] = {}
    if hasattr(oc_tool, "parameters"):
        parameters = oc_tool.parameters
    elif hasattr(oc_tool, "get_schema"):
        parameters = oc_tool.get_schema()

    async def _execute(
        tool_call_id: str,
        args: dict[str, Any],
        signal: asyncio.Event | None = None,
        on_update: Any | None = None,
    ) -> AgentToolResult:
        try:
            raw = await oc_tool.execute(
                tool_call_id=tool_call_id,
                params=args,
                signal=signal,
                on_update=on_update,
            )
            # Convert openclaw AgentToolResult to pi_agent AgentToolResult
            if hasattr(raw, "content"):
                content = [TextContent(text=str(c)) for c in raw.content]
            elif isinstance(raw, str):
                content = [TextContent(text=raw)]
            else:
                content = [TextContent(text=str(raw))]
            return AgentToolResult(content=content, details=getattr(raw, "details", None))
        except Exception as exc:
            logger.error("Tool %r execute error: %s", name, exc, exc_info=True)
            return AgentToolResult(content=[TextContent(text=f"Error: {exc}")], details=None)

    return AgentTool(
        name=name,
        description=description,
        label=label,
        parameters=parameters,
        execute=_execute,
    )


# ---------------------------------------------------------------------------
# AgentSession
# ---------------------------------------------------------------------------

class AgentSession:
    """Pi-coding-agent style session with automatic tool loop.

    Thin adapter over ``pi_coding_agent.AgentSession`` — exactly mirrors
    the relationship between openclaw TypeScript's ``AgentSession``
    (attempt.ts) and ``@pi-coding-agent``.

    Usage::

        session = AgentSession(
            session_key="agent:main:telegram:dm:123",
            cwd="/workspace",
            extra_tools=openclaw_tools,
        )

        def handle(event):
            if event.type == EventType.TEXT:
                print(event.data["delta"]["text"], end="")

        unsub = session.subscribe(handle)
        await session.prompt("What files are here?")
        unsub()
    """

    def __init__(
        self,
        session_key: str | None = None,
        cwd: str | None = None,
        model: str | None = None,
        system_prompt: str | None = None,
        extra_tools: list[Any] | None = None,
        session_id: str | None = None,
        # Legacy params (kept for backward compatibility)
        session: Any = None,
        runtime: Any = None,
        tools: list[Any] | None = None,
        max_iterations: int = 5,
        max_tokens: int = 8192,
        max_turns: int | None = None,
    ) -> None:
        self.session_key = session_key
        self.cwd = cwd
        self._model_str = model
        self._system_prompt = system_prompt
        self._extra_tools = list(extra_tools or tools or [])
        self._external_session_id = session_id

        # Legacy: if a Session object was passed, extract its session_id
        if session is not None and session_id is None:
            self._external_session_id = getattr(session, "session_id", None)

        self._pi_session: Any | None = None
        self._subscribers: list[Callable] = []
        self.hooks: HookRegistry = HookRegistry()
        self._is_streaming = False

    # ------------------------------------------------------------------
    # Lazy pi_coding_agent.AgentSession creation
    # ------------------------------------------------------------------

    def _get_pi_session(self) -> Any:
        """Lazily create the underlying pi_coding_agent.AgentSession."""
        if self._pi_session is not None:
            return self._pi_session

        from pi_coding_agent import AgentSession as PiAgentSession
        from pi_coding_agent.core.session_manager import SessionManager as PiSessionManager

        sm: Any | None = None
        if self._external_session_id:
            sm = PiSessionManager()
            sm._session_id = self._external_session_id

        model: Any | None = None
        if self._model_str:
            from pi_ai import get_model as _get_model
            try:
                if "/" in self._model_str:
                    prov, mid = self._model_str.split("/", 1)
                    model = _get_model(prov, mid)
                else:
                    model = _get_model("google", self._model_str)
            except (KeyError, ValueError):
                model = None

        self._pi_session = PiAgentSession(
            cwd=self.cwd,
            model=model,
            session_id=self._external_session_id,
            session_manager=sm,
        )

        # Override system prompt if provided
        if self._system_prompt:
            self._pi_session._agent.set_system_prompt(self._system_prompt)

        # Inject openclaw-specific extra tools alongside pi_coding_agent defaults
        if self._extra_tools:
            existing = list(self._pi_session._all_tools)
            wrapped = []
            for t in self._extra_tools:
                try:
                    # Skip tools already in pi_coding_agent format
                    if "pi_coding_agent" in type(t).__module__ or "pi_agent" in type(t).__module__:
                        wrapped.append(t)
                    else:
                        wrapped.append(_wrap_openclaw_tool(t))
                except Exception as exc:
                    logger.warning("Skipping extra tool %r: %s", getattr(t, "name", t), exc)
            all_tools = existing + wrapped
            self._pi_session._all_tools = all_tools
            self._pi_session._agent.set_tools(all_tools)

        # Subscribe to pi events and fan out to openclaw subscribers
        self._pi_session.subscribe(self._on_pi_event)

        return self._pi_session

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def session_id(self) -> str:
        if self._pi_session is not None:
            return getattr(self._pi_session, "session_id", "") or ""
        return self._external_session_id or ""

    @property
    def is_streaming(self) -> bool:
        return self._is_streaming

    @property
    def messages(self) -> list:
        if self._pi_session is not None:
            try:
                return self._pi_session._session_manager.get_messages()
            except Exception:
                return []
        return []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def subscribe(self, handler: Callable) -> Callable[[], None]:
        """Subscribe to session events. Returns unsubscribe function."""
        self._subscribers.append(handler)

        def _unsub() -> None:
            if handler in self._subscribers:
                self._subscribers.remove(handler)

        return _unsub

    async def prompt(self, text: str, images: list[str] | None = None) -> None:
        """Send a prompt and handle the full agent turn (mirrors pi-coding-agent's prompt()).

        Hook sequence:
        1. session_start
        2. before_prompt_build → before_model_resolve → before_agent_start
        3. [pi_coding_agent handles tool loop internally]
        4. agent_end → session_end
        """
        ctx: dict[str, Any] = {
            "text": text,
            "images": images,
            "session_id": self.session_id,
            "system_prompt": self._system_prompt,
        }

        self._is_streaming = True
        try:
            ctx = await self.hooks.run("session_start", ctx)
            ctx = await self.hooks.run("before_prompt_build", ctx)
            ctx = await self.hooks.run("before_model_resolve", ctx)
            ctx = await self.hooks.run("before_agent_start", ctx)

            pi_session = self._get_pi_session()
            await pi_session.prompt(ctx.get("text", text))

            ctx = await self.hooks.run("agent_end", ctx)
        except Exception as exc:
            logger.error("AgentSession.prompt error: %s", exc, exc_info=True)
            from openclaw.events import Event, EventType
            await self._notify(Event(
                type=EventType.ERROR,
                source="agent-session",
                session_id=self.session_id,
                data={"message": str(exc)},
            ))
        finally:
            self._is_streaming = False
            try:
                await self.hooks.run("session_end", ctx)
            except Exception:
                pass

    async def abort(self) -> None:
        """Abort the current run."""
        if self._pi_session is not None:
            try:
                await self._pi_session.abort()
            except Exception as exc:
                logger.warning("Abort error: %s", exc)

    def reset(self) -> None:
        """Reset session (clears conversation history)."""
        self._pi_session = None

    def get_message_count(self) -> int:
        return len(self.messages)

    # ------------------------------------------------------------------
    # Internal event fan-out
    # ------------------------------------------------------------------

    def _on_pi_event(self, pi_event: Any) -> None:
        """Called by pi_coding_agent for every AgentEvent."""
        from openclaw.events import Event, EventType
        oc_event = _convert_pi_event(pi_event, self.session_id)
        if oc_event is not None:
            asyncio.ensure_future(self._notify(oc_event))

    async def _notify(self, event: Any) -> None:
        for handler in list(self._subscribers):
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as exc:
                logger.warning("Subscriber error: %s", exc)

    def __repr__(self) -> str:
        return (
            f"AgentSession("
            f"key={self.session_key!r}, "
            f"id={self.session_id[:8] if self.session_id else 'none'}..., "
            f"streaming={self._is_streaming}"
            f")"
        )

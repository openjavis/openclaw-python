"""pi_coding_agent bridge for openclaw-python.

Wraps pi_coding_agent.AgentSession and pi_coding_agent.SessionManager so
openclaw can use the tested infrastructure from pi-mono-python as its
underlying agent/session engine.

Usage::

    from openclaw.agents.pi_bridge import PiBridgeSession

    session = PiBridgeSession(
        session_key="agent:main:default",
        model="google/gemini-2.0-flash",
        cwd="/path/to/workspace",
        system_prompt="You are openclaw...",
        tools=openclaw_tools,
    )
    async for event in session.prompt("What files are here?"):
        print(event)
"""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, AsyncIterator, Callable

logger = logging.getLogger(__name__)


class PiBridgeSession:
    """
    OpenClaw AgentSession built on top of pi_coding_agent.AgentSession.

    This replaces the legacy ToolLoopOrchestrator + MultiProviderRuntime
    stack with the battle-tested pi-mono-python implementation while
    preserving the openclaw session_key / SessionEntry metadata model.
    """

    def __init__(
        self,
        session_key: str,
        model: str = "google/gemini-2.0-flash",
        cwd: str | Path | None = None,
        system_prompt: str | None = None,
        tools: list[Any] | None = None,
        session_id: str | None = None,
    ) -> None:
        self.session_key = session_key
        self.model_name = model
        self.cwd = str(cwd) if cwd else None
        self.system_prompt = system_prompt
        self._tools = tools or []
        self._external_session_id = session_id

        self._pi_session: Any | None = None
        self._subscribers: list[Callable] = []

    # ------------------------------------------------------------------
    # Lazy initialization
    # ------------------------------------------------------------------

    def _ensure_pi_session(self) -> Any:
        """Lazily create the underlying pi_coding_agent.AgentSession."""
        if self._pi_session is not None:
            return self._pi_session

        try:
            from pi_coding_agent import AgentSession as _PiSession
            from pi_ai import get_model as _get_model

            model: Any = None
            if self.model_name:
                try:
                    if "/" in self.model_name:
                        prov, mid = self.model_name.split("/", 1)
                        model = _get_model(prov, mid)
                    else:
                        model = _get_model("google", self.model_name)
                except (KeyError, ValueError):
                    model = None

            self._pi_session = _PiSession(
                cwd=self.cwd,
                model=model,
                session_id=self._external_session_id,
            )

            # Override system prompt if provided
            if self.system_prompt:
                self._pi_session._agent.set_system_prompt(self.system_prompt)

        except Exception as exc:
            logger.error(f"Failed to create pi_coding_agent.AgentSession: {exc}")
            raise

        return self._pi_session

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def session_id(self) -> str:
        try:
            ps = self._ensure_pi_session()
            return getattr(ps, "session_id", "") or self._external_session_id or ""
        except Exception:
            return self._external_session_id or ""

    def subscribe(self, handler: Callable) -> Callable[[], None]:
        """Subscribe to events. Returns an unsubscribe function."""
        self._subscribers.append(handler)

        def _unsub() -> None:
            if handler in self._subscribers:
                self._subscribers.remove(handler)

        return _unsub

    async def prompt(
        self,
        text: str,
        images: list[str] | None = None,
    ) -> None:
        """Execute a prompt turn and notify subscribers with events.

        Converts pi_coding_agent events to openclaw Event objects and
        broadcasts them to all registered subscribers.
        """
        from openclaw.events import Event, EventType

        try:
            pi_session = self._ensure_pi_session()
        except Exception as exc:
            await self._notify(Event(
                type=EventType.ERROR,
                source="pi-bridge",
                session_id="",
                data={"message": f"Failed to create pi session: {exc}"},
            ))
            return

        session_id = self.session_id

        # Subscribe to pi_coding_agent events and fan out to openclaw subscribers
        def on_pi_event(pi_event: Any) -> None:
            oc_event = _convert_pi_event(pi_event)
            if oc_event is not None:
                asyncio.ensure_future(self._notify(oc_event))

        unsub = pi_session.subscribe(on_pi_event)
        try:
            await pi_session.prompt(text)
        except Exception as exc:
            logger.error(f"PiBridgeSession.prompt error: {exc}", exc_info=True)
            await self._notify(Event(
                type=EventType.ERROR,
                source="pi-bridge",
                session_id=session_id,
                data={"message": str(exc)},
            ))
        finally:
            unsub()

    async def _notify(self, event: Any) -> None:
        for handler in list(self._subscribers):
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as exc:
                logger.warning(f"Subscriber error: {exc}")


# ---------------------------------------------------------------------------
# Event conversion: pi_coding_agent → openclaw
# ---------------------------------------------------------------------------

def _convert_pi_event(pi_event: Any) -> Any:
    """Convert a pi_coding_agent event to an openclaw Event."""
    from openclaw.events import Event, EventType

    etype = getattr(pi_event, "type", None)
    if etype is None and isinstance(pi_event, dict):
        etype = pi_event.get("type")

    # Text delta
    if etype in ("textDelta", "text_delta"):
        delta = getattr(pi_event, "delta", "") or (pi_event.get("delta", "") if isinstance(pi_event, dict) else "")
        if isinstance(delta, dict):
            delta = delta.get("text", "")
        return Event(
            type=EventType.TEXT,
            source="pi-bridge",
            session_id="",
            data={"delta": {"text": str(delta)}},
        )

    # Tool call
    if etype in ("toolCall", "tool_call"):
        tc = getattr(pi_event, "tool_call", None) or (pi_event if isinstance(pi_event, dict) else {})
        return Event(
            type=EventType.TOOL_EXECUTION_START,
            source="pi-bridge",
            session_id="",
            data={
                "tool_name": getattr(tc, "name", "") or (tc.get("name", "") if isinstance(tc, dict) else ""),
                "tool_call_id": getattr(tc, "id", "") or (tc.get("id", "") if isinstance(tc, dict) else ""),
                "arguments": getattr(tc, "arguments", {}) or (tc.get("arguments", {}) if isinstance(tc, dict) else {}),
            },
        )

    # Assistant message (final)
    if etype in ("assistantMessage", "assistant_message"):
        return Event(
            type=EventType.AGENT_TURN_COMPLETE,
            source="pi-bridge",
            session_id="",
            data={"stop_reason": "stop"},
        )

    # Tool result
    if etype in ("toolResult", "tool_result"):
        return Event(
            type=EventType.TOOL_EXECUTION_END,
            source="pi-bridge",
            session_id="",
            data={
                "tool_call_id": getattr(pi_event, "tool_use_id", "") or "",
                "success": True,
                "result": str(getattr(pi_event, "content", "") or ""),
            },
        )

    return None


__all__ = ["PiBridgeSession"]

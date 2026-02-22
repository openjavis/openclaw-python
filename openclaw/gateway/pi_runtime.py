"""Pi-mono-python powered agent runtime for the gateway.

Replaces MultiProviderRuntime with a pi_coding_agent.AgentSession-based
implementation, mirroring how openclaw TypeScript uses @pi-coding-agent
as its underlying agent engine.

Architecture::

    GatewayBootstrap
         │ creates
    PiAgentRuntime              ← this module
         │ maintains pool of
    pi_coding_agent.AgentSession  per openclaw session_id
         │ subscribes to events from
    pi_agent.AgentEvent hierarchy
         │ converts to
    openclaw.events.Event → WebSocket client

Usage in bootstrap::

    from openclaw.gateway.pi_runtime import PiAgentRuntime
    self.runtime = PiAgentRuntime(model="google/gemini-2.0-flash", cwd=workspace_dir)

Usage in handlers (backward-compat run_turn interface)::

    async for event in self.runtime.run_turn(session, message, tools, model):
        await connection.send_event("agent", {...})
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, AsyncIterator

logger = logging.getLogger(__name__)


class PiAgentRuntime:
    """Gateway-level runtime powered by pi_coding_agent.AgentSession.

    Maintains a pool of pi_coding_agent.AgentSession instances, one per
    openclaw session_id.  Provides a ``run_turn()`` async-generator
    interface compatible with the old MultiProviderRuntime, so gateway
    handlers need no changes.
    """

    def __init__(
        self,
        model: str = "google/gemini-2.0-flash",
        cwd: str | Path | None = None,
        system_prompt: str | None = None,
    ) -> None:
        self.model_str = model
        self.cwd = str(cwd) if cwd else None
        self.system_prompt = system_prompt

        # Per-session pool: openclaw session_id → pi_coding_agent.AgentSession
        self._pool: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Pool management
    # ------------------------------------------------------------------

    def _get_or_create_pi_session(
        self,
        session_id: str,
        extra_tools: list[Any] | None = None,
    ) -> Any:
        """Get or create a pi_coding_agent.AgentSession for session_id."""
        if session_id in self._pool:
            return self._pool[session_id]

        try:
            from pi_coding_agent import AgentSession as PiAgentSession
            from openclaw.agents.pi_stream import _resolve_model

            model = None
            try:
                model = _resolve_model(self.model_str)
            except Exception:
                pass

            pi_session = PiAgentSession(
                cwd=self.cwd,
                model=model,
                session_id=session_id,
            )

            # Override system prompt if set
            if self.system_prompt:
                pi_session._agent.set_system_prompt(self.system_prompt)

            # Inject openclaw-specific tools
            if extra_tools:
                from openclaw.agents.agent_session import _wrap_openclaw_tool
                existing = list(pi_session._all_tools)
                wrapped = []
                for t in extra_tools:
                    try:
                        m = type(t).__module__
                        if "pi_coding_agent" in m or "pi_agent" in m:
                            wrapped.append(t)
                        else:
                            wrapped.append(_wrap_openclaw_tool(t))
                    except Exception as exc:
                        logger.warning("Skipping tool %r: %s", getattr(t, "name", t), exc)
                all_tools = existing + wrapped
                pi_session._all_tools = all_tools
                pi_session._agent.set_tools(all_tools)

            self._pool[session_id] = pi_session
            logger.info("Created pi_coding_agent.AgentSession for session %s", session_id[:8])

        except Exception as exc:
            logger.error("Failed to create pi session: %s", exc, exc_info=True)
            raise

        return self._pool[session_id]

    def evict_session(self, session_id: str) -> None:
        """Remove a session from the pool."""
        self._pool.pop(session_id, None)

    # ------------------------------------------------------------------
    # run_turn — backward-compatible async generator
    # ------------------------------------------------------------------

    async def run_turn(
        self,
        session: Any,
        message: str,
        tools: list[Any] | None = None,
        model: str | None = None,
        system_prompt: str | None = None,
    ) -> AsyncIterator[Any]:
        """Stream agent events for one conversation turn.

        Replaces MultiProviderRuntime.run_turn().  Yields openclaw Event
        objects aligned with EventType enum values.

        Args:
            session:       openclaw Session object (provides session_id)
            message:       User message text
            tools:         Optional tool list (openclaw AgentToolBase instances)
            model:         Optional model override string
            system_prompt: Optional system prompt override
        """
        session_id = getattr(session, "session_id", "") or ""
        extra_tools = list(tools) if tools else None

        try:
            pi_session = self._get_or_create_pi_session(session_id, extra_tools)
        except Exception as exc:
            from openclaw.events import Event, EventType
            yield Event(
                type=EventType.ERROR,
                source="pi-runtime",
                session_id=session_id,
                data={"message": f"Session creation failed: {exc}"},
            )
            return

        # Override model if requested
        if model and model != self.model_str:
            try:
                from openclaw.agents.pi_stream import _resolve_model
                m = _resolve_model(model)
                await pi_session.set_model(m)
            except Exception as exc:
                logger.warning("Model override failed for %r: %s", model, exc)

        # Use an async queue to bridge pi event callbacks → async generator
        event_queue: asyncio.Queue[Any] = asyncio.Queue()
        _SENTINEL = object()

        def on_event(pi_event: Any) -> None:
            from openclaw.agents.agent_session import _convert_pi_event
            oc_event = _convert_pi_event(pi_event, session_id)
            if oc_event is not None:
                event_queue.put_nowait(oc_event)

        unsub = pi_session.subscribe(on_event)

        async def _run_prompt() -> None:
            try:
                await pi_session.prompt(message)
            except Exception as exc:
                from openclaw.events import Event, EventType
                event_queue.put_nowait(Event(
                    type=EventType.ERROR,
                    source="pi-runtime",
                    session_id=session_id,
                    data={"message": str(exc)},
                ))
            finally:
                event_queue.put_nowait(_SENTINEL)

        prompt_task = asyncio.create_task(_run_prompt())

        try:
            while True:
                event = await event_queue.get()
                if event is _SENTINEL:
                    break
                yield event
        finally:
            unsub()
            if not prompt_task.done():
                prompt_task.cancel()
                try:
                    await prompt_task
                except (asyncio.CancelledError, Exception):
                    pass

    # ------------------------------------------------------------------
    # Abort running session
    # ------------------------------------------------------------------

    async def abort_session(self, session_id: str) -> None:
        """Abort any running turn for the given session."""
        pi_session = self._pool.get(session_id)
        if pi_session is not None:
            try:
                await pi_session.abort()
            except Exception as exc:
                logger.warning("Abort session %s: %s", session_id[:8], exc)


__all__ = ["PiAgentRuntime"]

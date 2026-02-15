"""Extension runtime: holds loaded extensions and dispatches events.

Matches pi-mono ExtensionRuntime role. Does not implement full ExtensionContext
(UI, session manager, etc.); that is provided by the runner when binding to agent.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from .types import ExtensionContext

logger = logging.getLogger(__name__)


class ExtensionRuntime:
    """
    Runtime for extensions: stores tools and handlers, dispatches events.
    Runner binds context (agent_id, session_id, etc.) and invokes emit().
    """

    def __init__(self):
        self._tools: list[dict[str, Any]] = []
        self._handlers: dict[str, list[Callable[..., Any]]] = {}
        self._commands: dict[str, dict[str, Any]] = {}
        self._context: ExtensionContext | None = None

    def set_context(self, context: ExtensionContext) -> None:
        """Set the context passed to event handlers."""
        self._context = context

    def register_tools(self, tools: list[dict[str, Any]]) -> None:
        """Register tools from loaded extensions."""
        self._tools.extend(tools)

    def register_handlers(self, handlers: dict[str, list[Callable[..., Any]]]) -> None:
        """Merge handlers from loaded extensions."""
        for event, hlist in handlers.items():
            self._handlers.setdefault(event, []).extend(hlist)

    def register_commands(self, commands: dict[str, dict[str, Any]]) -> None:
        """Register commands from loaded extensions."""
        self._commands.update(commands)

    def get_tools(self) -> list[dict[str, Any]]:
        """Return all registered tools (for agent to use)."""
        return self._tools.copy()

    def get_commands(self) -> dict[str, dict[str, Any]]:
        """Return all registered commands."""
        return self._commands.copy()

    async def emit(self, event: str, payload: dict[str, Any] | None = None) -> list[Any]:
        """
        Dispatch event to all registered handlers. Returns list of results.
        
        For modifying hooks (before_agent_start), results are merged:
        - prependContext: concatenated with '\n\n'
        - systemPrompt: last one wins
        """
        if self._context is None:
            logger.debug("ExtensionRuntime.emit(%s) skipped: no context", event)
            return []
        payload = payload or {}
        results: list[Any] = []
        for handler in self._handlers.get(event, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    r = await handler({**payload, "type": event}, self._context)
                else:
                    r = handler({**payload, "type": event}, self._context)
                if r is not None:
                    results.append(r)
            except Exception as e:
                logger.exception("Extension handler failed for %s: %s", event, e)
        
        # Special handling for modifying hooks
        if event == "before_agent_start":
            return self._merge_before_agent_start_results(results)
        
        return results
    
    def _merge_before_agent_start_results(
        self,
        results: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Merge results from before_agent_start hook.
        
        Matches openclaw-ts behavior: concatenate prependContext, last systemPrompt wins.
        
        Returns:
            List with single merged dict, or empty list
        """
        if not results:
            return []
        
        merged_prepend: list[str] = []
        final_system_prompt: str | None = None
        
        for result in results:
            if isinstance(result, dict):
                if result.get("prependContext"):
                    merged_prepend.append(result["prependContext"])
                if result.get("systemPrompt"):
                    final_system_prompt = result["systemPrompt"]
        
        merged: dict[str, Any] = {}
        if merged_prepend:
            merged["prependContext"] = "\n\n".join(merged_prepend)
        if final_system_prompt:
            merged["systemPrompt"] = final_system_prompt
        
        return [merged] if merged else []

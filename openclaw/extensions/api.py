"""Extension API passed to extension register().

Extensions use this to register tools, subscribe to events, and access context.
Matches pi-mono ExtensionAPI surface (subset relevant to openclaw-python).
"""
from __future__ import annotations

import logging
from typing import Any, Callable

from .types import ExtensionContext

logger = logging.getLogger(__name__)


class ExtensionAPI:
    """
    API passed to extension factory. Extensions call register(api) and use api
    to register tools and event handlers.
    """

    def __init__(self, extension_id: str, context: ExtensionContext):
        self._extension_id = extension_id
        self._context = context
        self._tools: list[dict[str, Any]] = []
        self._handlers: dict[str, list[Callable[..., Any]]] = {}
        self._commands: dict[str, dict[str, Any]] = {}

    @property
    def context(self) -> ExtensionContext:
        return self._context

    def register_tool(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        execute: Callable[..., Any],
    ) -> None:
        """
        Register a tool that the agent can call.

        Args:
            name: Tool name (used in LLM tool calls)
            description: Description for the LLM
            parameters: JSON schema for parameters
            execute: Async callable(tool_call_id, params, signal, ctx) -> result
        """
        self._tools.append({
            "name": name,
            "description": description,
            "parameters": parameters,
            "execute": execute,
            "extension_id": self._extension_id,
        })
        logger.debug("Extension %s registered tool %s", self._extension_id, name)

    def on(self, event: str, handler: Callable[..., Any] | None = None) -> Callable[..., Any] | None:
        """
        Subscribe to an extension event.

        Supported events: agent_start, agent_end, turn_start, turn_end,
        before_agent_start, tool_call, tool_result, session_start, session_end.
        
        Can be used as decorator:
            @api.on("before_agent_start")
            async def handler(event, context):
                ...
        
        Or called directly:
            api.on("before_agent_start", handler)
        """
        if handler is None:
            # Decorator syntax: @api.on("event_name")
            def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
                self._handlers.setdefault(event, []).append(fn)
                logger.debug("Extension %s registered handler for %s", self._extension_id, event)
                return fn
            return decorator
        else:
            # Direct call: api.on("event_name", handler)
            self._handlers.setdefault(event, []).append(handler)
            logger.debug("Extension %s registered handler for %s", self._extension_id, event)
            return None

    def register_command(
        self,
        name: str,
        description: str,
        handler: Callable[..., Any],
    ) -> None:
        """Register a slash command (e.g. /mycommand)."""
        self._commands[name] = {
            "name": name,
            "description": description,
            "handler": handler,
            "extension_id": self._extension_id,
        }
        logger.debug("Extension %s registered command %s", self._extension_id, name)

    def get_tools(self) -> list[dict[str, Any]]:
        """Return all tools registered by this extension (for runner to collect)."""
        return self._tools.copy()

    def get_handlers(self) -> dict[str, list[Callable[..., Any]]]:
        """Return all event handlers (for runtime to dispatch)."""
        return self._handlers.copy()

    def get_commands(self) -> dict[str, dict[str, Any]]:
        """Return all registered commands."""
        return self._commands.copy()

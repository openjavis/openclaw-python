"""Plugin types and interfaces"""

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel


class PluginManifest(BaseModel):
    """Plugin manifest"""

    id: str
    name: str
    version: str
    description: str | None = None
    author: str | None = None
    main: str = "plugin.py"  # Main plugin file
    skills: list[str] = []  # Skill directories
    requires: list[str] = []  # Required dependencies


class PluginAPI:
    """API provided to plugins"""

    def __init__(self, plugin_id: str):
        self.plugin_id = plugin_id
        self._tools: list[Any] = []
        self._channels: list[Any] = []

    def register_tool(self, tool: Any) -> None:
        """Register a tool"""
        self._tools.append(tool)

    def register_channel(self, channel: Any) -> None:
        """Register a channel"""
        self._channels.append(channel)

    def register_hook(self, event: str, handler: Callable) -> None:
        """Register an event hook"""
        # TODO: Implement hook system
        pass

    def get_config(self) -> dict[str, Any]:
        """Get plugin configuration"""
        # TODO: Load from config
        return {}


class Plugin:
    """Base plugin class"""

    def __init__(self, manifest: PluginManifest, path: str):
        self.manifest = manifest
        self.path = path
        self.api: PluginAPI | None = None

    async def activate(self, api: PluginAPI) -> None:
        """Activate the plugin"""
        self.api = api

    async def deactivate(self) -> None:
        """Deactivate the plugin"""
        pass

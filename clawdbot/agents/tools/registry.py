"""Tool registry"""

from typing import Optional, Any
from .base import AgentTool
from .bash import BashTool
from .file_ops import ReadFileTool, WriteFileTool, EditFileTool
from .web import WebFetchTool, WebSearchTool
from .image import ImageTool
from .sessions import SessionsListTool, SessionsHistoryTool, SessionsSendTool, SessionsSpawnTool
from .browser import BrowserTool
from .cron import CronTool
from .tts import TTSTool
from .process import ProcessTool
from .channel_actions import MessageTool, TelegramActionsTool, DiscordActionsTool, SlackActionsTool, WhatsAppActionsTool
from .nodes import NodesTool
from .patch import ApplyPatchTool
from .canvas import CanvasTool
from .voice_call import VoiceCallTool
from ..session import SessionManager


class ToolRegistry:
    """Registry of available tools"""

    def __init__(self, session_manager: Optional['SessionManager'] = None, channel_registry: Optional[Any] = None):
        self._tools: dict[str, AgentTool] = {}
        self._session_manager = session_manager  # Must be provided when needed
        self._channel_registry = channel_registry
        if session_manager:  # Only register tools that need session manager if provided
            self._register_default_tools()

    def _register_default_tools(self) -> None:
        """Register default tools"""
        # File operations
        self.register(ReadFileTool())
        self.register(WriteFileTool())
        self.register(EditFileTool())

        # Process execution
        self.register(BashTool())

        # Web tools
        self.register(WebFetchTool())
        self.register(WebSearchTool())
        
        # Image analysis
        self.register(ImageTool())
        
        # Session management
        self.register(SessionsListTool(self._session_manager))
        self.register(SessionsHistoryTool(self._session_manager))
        self.register(SessionsSendTool(self._session_manager))
        self.register(SessionsSpawnTool(self._session_manager))
        
        # Advanced tools
        self.register(BrowserTool())
        self.register(CronTool())
        self.register(TTSTool())
        self.register(ProcessTool())
        
        # Channel actions (if channel registry available)
        if self._channel_registry:
            self.register(MessageTool(self._channel_registry))
            self.register(TelegramActionsTool(self._channel_registry))
            self.register(DiscordActionsTool(self._channel_registry))
            self.register(SlackActionsTool(self._channel_registry))
            self.register(WhatsAppActionsTool(self._channel_registry))
        
        # Special features
        self.register(NodesTool())
        self.register(CanvasTool())
        self.register(VoiceCallTool())
        
        # Patch tool
        self.register(ApplyPatchTool())

    def register(self, tool: AgentTool) -> None:
        """Register a tool"""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[AgentTool]:
        """Get tool by name"""
        return self._tools.get(name)

    def list_tools(self) -> list[AgentTool]:
        """List all tools"""
        return list(self._tools.values())

    def get_tools_by_profile(self, profile: str = "full") -> list[AgentTool]:
        """Get tools filtered by profile"""
        # TODO: Implement profile-based filtering
        if profile == "minimal":
            return [self.get("read_file"), self.get("web_fetch")]
        elif profile == "coding":
            return [
                self.get("read_file"),
                self.get("write_file"),
                self.get("edit_file"),
                self.get("bash"),
                self.get("web_fetch")
            ]
        elif profile == "messaging":
            return [self.get("web_fetch"), self.get("web_search")]
        else:  # full
            return self.list_tools()


# Global tool registry
_global_registry = ToolRegistry()


def get_tool_registry(session_manager: Optional[Any] = None) -> ToolRegistry:
    """Get global tool registry"""
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry(session_manager=session_manager)
    return _global_registry

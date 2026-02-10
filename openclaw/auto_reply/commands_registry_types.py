"""Command registry type definitions"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable


class CommandScope(str, Enum):
    """Command scope"""
    GLOBAL = "global"  # Available everywhere
    DM = "dm"  # Only in DMs
    GROUP = "group"  # Only in groups
    CHANNEL = "channel"  # Specific channel only


class CommandDispatchMode(str, Enum):
    """Command dispatch mode"""
    TOOL = "tool"  # Execute as tool
    PROMPT = "prompt"  # Rewrite as prompt
    HANDLER = "handler"  # Custom handler function


@dataclass
class Command:
    """Command definition"""
    
    # Identification
    name: str
    aliases: list[str] = field(default_factory=list)
    
    # Documentation
    description: str = ""
    usage: str = ""
    examples: list[str] = field(default_factory=list)
    
    # Behavior
    dispatch_mode: CommandDispatchMode = CommandDispatchMode.HANDLER
    handler: Callable[[Any], Awaitable[Any]] | None = None
    
    # Scope
    scope: CommandScope = CommandScope.GLOBAL
    channel_ids: list[str] = field(default_factory=list)  # For channel scope
    
    # Permissions
    admin_only: bool = False
    allowed_users: list[str] = field(default_factory=list)
    
    # Options
    requires_args: bool = False
    hidden: bool = False  # Hide from help
    
    def matches(self, command_name: str) -> bool:
        """Check if command matches name or alias"""
        return command_name == self.name or command_name in self.aliases

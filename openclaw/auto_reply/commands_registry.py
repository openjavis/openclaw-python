"""Command registry for managing commands"""
from __future__ import annotations

import logging
from typing import Optional

from .commands_registry_types import Command, CommandScope
from .commands_registry_data import get_builtin_commands
from .types import CommandInvocation, CommandResult, InboundMessage

logger = logging.getLogger(__name__)


class CommandRegistry:
    """
    Registry for managing commands
    
    Handles:
    - Built-in commands
    - Custom commands
    - Skill commands
    - Command resolution and execution
    """
    
    def __init__(self):
        """Initialize command registry"""
        self._commands: dict[str, Command] = {}
        self._aliases: dict[str, str] = {}  # alias -> command_name
        
        # Register built-in commands
        self._register_builtin_commands()
    
    def _register_builtin_commands(self) -> None:
        """Register built-in commands"""
        for command in get_builtin_commands():
            self.register(command)
        
        logger.info(f"Registered {len(self._commands)} built-in commands")
    
    def register(self, command: Command) -> None:
        """
        Register a command
        
        Args:
            command: Command to register
        """
        # Register command
        self._commands[command.name] = command
        
        # Register aliases
        for alias in command.aliases:
            self._aliases[alias] = command.name
        
        logger.debug(f"Registered command: {command.name}")
    
    def unregister(self, command_name: str) -> bool:
        """
        Unregister a command
        
        Args:
            command_name: Command name
            
        Returns:
            True if unregistered
        """
        if command_name not in self._commands:
            return False
        
        command = self._commands[command_name]
        
        # Remove aliases
        for alias in command.aliases:
            if alias in self._aliases:
                del self._aliases[alias]
        
        # Remove command
        del self._commands[command_name]
        
        logger.debug(f"Unregistered command: {command_name}")
        
        return True
    
    def resolve(self, command_name: str) -> Optional[Command]:
        """
        Resolve command by name or alias
        
        Args:
            command_name: Command name or alias
            
        Returns:
            Command if found
        """
        # Check direct name
        if command_name in self._commands:
            return self._commands[command_name]
        
        # Check aliases
        if command_name in self._aliases:
            actual_name = self._aliases[command_name]
            return self._commands[actual_name]
        
        return None
    
    def get_all(self, include_hidden: bool = False) -> list[Command]:
        """
        Get all commands
        
        Args:
            include_hidden: Include hidden commands
            
        Returns:
            List of commands
        """
        commands = list(self._commands.values())
        
        if not include_hidden:
            commands = [c for c in commands if not c.hidden]
        
        return commands
    
    def get_for_scope(
        self,
        scope: CommandScope,
        channel_id: str | None = None,
        include_hidden: bool = False
    ) -> list[Command]:
        """
        Get commands for specific scope
        
        Args:
            scope: Command scope
            channel_id: Optional channel ID
            include_hidden: Include hidden commands
            
        Returns:
            List of commands
        """
        commands = []
        
        for command in self._commands.values():
            if command.hidden and not include_hidden:
                continue
            
            # Check scope
            if command.scope == CommandScope.GLOBAL:
                commands.append(command)
            elif command.scope == scope:
                # Check channel-specific
                if command.scope == CommandScope.CHANNEL:
                    if channel_id and channel_id in command.channel_ids:
                        commands.append(command)
                else:
                    commands.append(command)
        
        return commands
    
    async def execute(
        self,
        invocation: CommandInvocation,
        context: dict | None = None
    ) -> CommandResult:
        """
        Execute command
        
        Args:
            invocation: Command invocation
            context: Optional context
            
        Returns:
            Command result
        """
        context = context or {}
        
        # Handle skill commands
        if invocation.command_name.startswith("skill:"):
            return await self._execute_skill_command(invocation, context)
        
        # Resolve command
        command = self.resolve(invocation.command_name)
        
        if not command:
            return CommandResult(
                success=False,
                error=f"Unknown command: {invocation.command_name}",
            )
        
        # Check if args required
        if command.requires_args and not invocation.args:
            return CommandResult(
                success=False,
                error=f"Command '{command.name}' requires arguments. Usage: {command.usage}",
            )
        
        # Execute handler
        if command.handler:
            try:
                result = await command.handler(invocation, context)
                return result
            except Exception as e:
                logger.error(f"Command execution error: {e}", exc_info=True)
                return CommandResult(
                    success=False,
                    error=str(e),
                )
        else:
            return CommandResult(
                success=False,
                error=f"Command '{command.name}' has no handler",
            )
    
    async def _execute_skill_command(
        self,
        invocation: CommandInvocation,
        context: dict
    ) -> CommandResult:
        """
        Execute skill command
        
        Args:
            invocation: Command invocation
            context: Context
            
        Returns:
            Command result
        """
        # Extract skill name
        skill_name = invocation.command_name[6:]  # Remove 'skill:' prefix
        
        # TODO: Load and execute skill
        # This requires skill loading system
        
        logger.warning(f"Skill command not yet implemented: {skill_name}")
        
        return CommandResult(
            success=False,
            error=f"Skill '{skill_name}' not found or not implemented",
        )


# Global registry
_global_registry: Optional[CommandRegistry] = None


def get_global_command_registry() -> CommandRegistry:
    """Get or create global command registry"""
    global _global_registry
    
    if _global_registry is None:
        _global_registry = CommandRegistry()
    
    return _global_registry

"""Chat command parsing and execution."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class ChatCommand:
    """Represents a parsed chat command."""
    name: str
    args: list[str]
    raw_text: str


class ChatCommandParser:
    """Parses chat commands from messages."""
    
    COMMANDS = {
        '/status',
        '/reset',
        '/new',
        '/compact',
        '/think',
        '/verbose',
        '/usage',
        '/restart',
        '/activation',
    }
    
    def parse(self, text: str) -> Optional[ChatCommand]:
        """
        Parse a message text into a ChatCommand if it's a command.
        
        Args:
            text: The message text to parse
            
        Returns:
            ChatCommand if text is a valid command, None otherwise
        """
        text = text.strip()
        
        if not text.startswith('/'):
            return None
        
        parts = text.split(maxsplit=1)
        cmd_name = parts[0].lower()
        
        if cmd_name not in self.COMMANDS:
            return None
        
        # Parse arguments
        args = parts[1].split() if len(parts) > 1 else []
        
        return ChatCommand(
            name=cmd_name[1:],  # Remove leading /
            args=args,
            raw_text=text
        )


class ChatCommandExecutor:
    """Executes chat commands."""
    
    def __init__(self, session_manager, agent_runtime):
        self.session_manager = session_manager
        self.agent_runtime = agent_runtime
    
    async def execute(
        self,
        command: ChatCommand,
        session_id: str,
        user_id: str,
        is_owner: bool = False
    ) -> str:
        """
        Execute a chat command.
        
        Args:
            command: The parsed command
            session_id: Current session ID
            user_id: User who issued the command
            is_owner: Whether user is the bot owner
            
        Returns:
            Response message to send back
        """
        # Check permissions
        if not self._check_permission(command.name, is_owner):
            return "❌ You don't have permission to use this command"
        
        try:
            if command.name == 'status':
                return await self._cmd_status(session_id)
            
            elif command.name in ('reset', 'new'):
                return await self._cmd_reset(session_id)
            
            elif command.name == 'compact':
                return await self._cmd_compact(session_id)
            
            elif command.name == 'think':
                level = command.args[0] if command.args else 'medium'
                return await self._cmd_think(session_id, level)
            
            elif command.name == 'verbose':
                enabled = command.args[0] == 'on' if command.args else True
                return await self._cmd_verbose(session_id, enabled)
            
            elif command.name == 'usage':
                mode = command.args[0] if command.args else 'full'
                return await self._cmd_usage(session_id, mode)
            
            elif command.name == 'activation':
                mode = command.args[0] if command.args else 'mention'
                return await self._cmd_activation(session_id, mode)
            
            elif command.name == 'restart':
                return await self._cmd_restart()
            
            return f"❌ Unknown command: {command.name}"
            
        except Exception as e:
            return f"❌ Error executing command: {str(e)}"
    
    def _check_permission(self, command: str, is_owner: bool) -> bool:
        """Check if user has permission for command."""
        owner_only = {'restart'}
        
        if command in owner_only:
            return is_owner
        
        return True
    
    async def _cmd_status(self, session_id: str) -> str:
        """Show session status."""
        session = await self.session_manager.get(session_id)
        
        if not session:
            return "❌ Session not found"
        
        message_count = len(getattr(session, 'messages', []))
        model = getattr(session, 'model', 'unknown')
        thinking = getattr(session, 'thinking_level', 'off')
        verbose = getattr(session, 'verbose', False)
        
        return f"""📊 **Session Status**

**Session ID**: {session_id}
**Model**: {model}
**Messages**: {message_count}
**Thinking**: {thinking}
**Verbose**: {'on' if verbose else 'off'}
"""
    
    async def _cmd_reset(self, session_id: str) -> str:
        """Reset/clear session."""
        success = await self.session_manager.reset(session_id)
        
        if success:
            return "✅ Session reset successfully"
        else:
            return "❌ Failed to reset session"
    
    async def _cmd_compact(self, session_id: str) -> str:
        """Compact session history."""
        session = await self.session_manager.get(session_id)
        
        if not session:
            return "❌ Session not found"
        
        # TODO: Implement compaction logic
        return "✅ Session compacted (feature coming soon)"
    
    async def _cmd_think(self, session_id: str, level: str) -> str:
        """Set thinking level."""
        valid_levels = {'off', 'low', 'medium', 'high'}
        
        if level not in valid_levels:
            return f"❌ Invalid thinking level. Use: {', '.join(valid_levels)}"
        
        session = await self.session_manager.get(session_id)
        if session:
            session.thinking_level = level
            await self.session_manager.save(session)
            return f"✅ Thinking level set to: **{level}**"
        
        return "❌ Session not found"
    
    async def _cmd_verbose(self, session_id: str, enabled: bool) -> str:
        """Toggle verbose mode."""
        session = await self.session_manager.get(session_id)
        
        if session:
            session.verbose = enabled
            await self.session_manager.save(session)
            status = "enabled" if enabled else "disabled"
            return f"✅ Verbose mode {status}"
        
        return "❌ Session not found"
    
    async def _cmd_usage(self, session_id: str, mode: str) -> str:
        """Show usage statistics."""
        valid_modes = {'off', 'tokens', 'full'}
        
        if mode not in valid_modes:
            return f"❌ Invalid usage mode. Use: {', '.join(valid_modes)}"
        
        session = await self.session_manager.get(session_id)
        if session:
            session.usage_mode = mode
            await self.session_manager.save(session)
            return f"✅ Usage display set to: **{mode}**"
        
        return "❌ Session not found"
    
    async def _cmd_activation(self, session_id: str, mode: str) -> str:
        """Set activation mode for groups."""
        valid_modes = {'mention', 'always', 'never'}
        
        if mode not in valid_modes:
            return f"❌ Invalid activation mode. Use: {', '.join(valid_modes)}"
        
        session = await self.session_manager.get(session_id)
        if session:
            session.activation_mode = mode
            await self.session_manager.save(session)
            return f"✅ Activation mode set to: **{mode}**"
        
        return "❌ Session not found"
    
    async def _cmd_restart(self) -> str:
        """Restart the gateway (owner only)."""
        # TODO: Implement gateway restart
        return "✅ Restart initiated (feature coming soon)"

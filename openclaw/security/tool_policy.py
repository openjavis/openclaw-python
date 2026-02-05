"""Tool execution permission policies."""
from enum import Enum
from typing import Optional


class SandboxMode(Enum):
    """Sandbox modes for tool execution."""
    OFF = "off"
    NON_MAIN = "non-main"
    ALL = "all"


class ToolPolicy:
    """Represents a tool allow/deny policy."""
    
    def __init__(
        self,
        allow: Optional[list[str]] = None,
        deny: Optional[list[str]] = None
    ):
        self.allow = allow or []
        self.deny = deny or []
    
    def is_allowed(self, tool_name: str) -> bool:
        """
        Check if a tool is allowed by this policy.
        
        Args:
            tool_name: Name of the tool to check
            
        Returns:
            True if tool is allowed
        """
        # Deny list takes precedence
        if tool_name in self.deny:
            return False
        
        # If allow list exists, tool must be in it
        if self.allow:
            return tool_name in self.allow or '*' in self.allow
        
        # No restrictions
        return True
    
    def __repr__(self) -> str:
        return f"ToolPolicy(allow={self.allow}, deny={self.deny})"


class ToolPolicyResolver:
    """Resolves and enforces tool policies."""
    
    def __init__(self, config: dict):
        self.config = config
    
    def is_tool_allowed(
        self,
        tool_name: str,
        agent_id: str,
        session_type: str = "main",
        is_main_session: bool = True
    ) -> tuple[bool, Optional[str]]:
        """
        Check if a tool can be executed.
        
        Args:
            tool_name: Tool to check
            agent_id: Current agent ID
            session_type: Type of session
            is_main_session: Whether this is the main session
            
        Returns:
            (allowed, reason_if_denied)
        """
        policies = self._get_policies(agent_id, is_main_session)
        
        for policy in policies:
            if not policy.is_allowed(tool_name):
                return False, f"Tool '{tool_name}' denied by policy"
        
        return True, None
    
    def _get_policies(
        self,
        agent_id: str,
        is_main_session: bool
    ) -> list[ToolPolicy]:
        """Get all applicable policies in order."""
        policies = []
        
        # 1. Global tools policy
        global_tools = self.config.get('tools', {})
        if global_tools.get('allow') or global_tools.get('deny'):
            policies.append(ToolPolicy(
                allow=global_tools.get('allow'),
                deny=global_tools.get('deny')
            ))
        
        # 2. Agent-specific policy
        agent_config = self._get_agent_config(agent_id)
        agent_tools = agent_config.get('tools', {})
        if agent_tools.get('allow') or agent_tools.get('deny'):
            policies.append(ToolPolicy(
                allow=agent_tools.get('allow'),
                deny=agent_tools.get('deny')
            ))
        
        # 3. Sandbox policy (for non-main sessions)
        sandbox_mode = self._get_sandbox_mode()
        if self._should_apply_sandbox(sandbox_mode, is_main_session):
            sandbox_policy = self._get_sandbox_policy(agent_config)
            if sandbox_policy:
                policies.append(sandbox_policy)
        
        return policies
    
    def _get_agent_config(self, agent_id: str) -> dict:
        """Get config for specific agent."""
        agents = self.config.get('agents', {})
        
        # Try specific agent config
        if agent_id in agents:
            return agents[agent_id]
        
        # Fall back to defaults
        return agents.get('defaults', {})
    
    def _get_sandbox_mode(self) -> SandboxMode:
        """Get configured sandbox mode."""
        mode_str = (
            self.config
            .get('agents', {})
            .get('defaults', {})
            .get('sandbox', {})
            .get('mode', 'off')
        )
        
        try:
            return SandboxMode(mode_str)
        except ValueError:
            return SandboxMode.OFF
    
    def _should_apply_sandbox(
        self,
        mode: SandboxMode,
        is_main_session: bool
    ) -> bool:
        """Determine if sandbox should be applied."""
        if mode == SandboxMode.OFF:
            return False
        
        if mode == SandboxMode.ALL:
            return True
        
        if mode == SandboxMode.NON_MAIN:
            return not is_main_session
        
        return False
    
    def _get_sandbox_policy(self, agent_config: dict) -> Optional[ToolPolicy]:
        """Get sandbox tool policy."""
        sandbox_tools = agent_config.get('sandbox', {}).get('tools', {})
        
        if sandbox_tools.get('allow') or sandbox_tools.get('deny'):
            return ToolPolicy(
                allow=sandbox_tools.get('allow'),
                deny=sandbox_tools.get('deny')
            )
        
        return None


# Predefined tool profiles
TOOL_PROFILES = {
    'safe': ToolPolicy(
        allow=['bash', 'read', 'write', 'edit', 'list_dir'],
        deny=['browser', 'system_run', 'nodes']
    ),
    'restricted': ToolPolicy(
        allow=['bash', 'read'],
        deny=['write', 'edit', 'browser', 'system_run', 'nodes']
    ),
    'full': ToolPolicy(
        allow=['*'],
        deny=[]
    ),
}


def get_profile_policy(profile_name: str) -> Optional[ToolPolicy]:
    """Get a predefined tool profile."""
    return TOOL_PROFILES.get(profile_name)

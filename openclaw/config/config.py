"""
Agent configuration - aligned with pi-mono

Provides configurable limits and strategies for agent behavior.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class AgentConfig:
    """
    Agent configuration - aligned with pi-mono
    
    Provides configurable limits for:
    - History message count
    - Token limits
    - Context compaction strategy
    """
    # Message history limits
    max_history_messages: int = 20  # Default: 20 messages (aligned with current implementation)
    max_history_tokens: int | None = None  # Token-based limit (optional)
    
    # Context compaction strategy
    compaction_strategy: Literal["truncate", "summarize", "keep_important"] = "truncate"
    
    # Keep first N messages (system prompt, etc.)
    keep_first_messages: int = 1  # Always keep system prompt
    
    # Compaction threshold (trigger compaction when history exceeds this)
    compaction_threshold: float = 0.9  # Trigger at 90% of max
    
    
    @classmethod
    def default(cls) -> "AgentConfig":
        """Create default configuration"""
        return cls()
    
    @classmethod
    def strict(cls) -> "AgentConfig":
        """Create strict configuration (minimal history)"""
        return cls(
            max_history_messages=10,
            compaction_strategy="truncate",
            keep_first_messages=1
        )
    
    @classmethod
    def permissive(cls) -> "AgentConfig":
        """Create permissive configuration (large history)"""
        return cls(
            max_history_messages=50,
            compaction_strategy="keep_important",
            keep_first_messages=2
        )
    
    @classmethod
    def summarize(cls) -> "AgentConfig":
        """Create summarization configuration"""
        return cls(
            max_history_messages=20,
            compaction_strategy="summarize",
            keep_first_messages=1
        )


@dataclass
class GatewayConfig:
    """
    Gateway configuration
    
    Configuration for Gateway server behavior.
    """
    # Port configuration
    websocket_port: int = 18789
    http_port: int = 8080
    
    # Timeouts
    websocket_timeout: int = 300  # 5 minutes
    http_timeout: int = 120  # 2 minutes
    
    # Queue limits
    max_concurrent_sessions: int = 100
    max_queue_size: int = 1000
    
    # Cache settings
    session_cache_ttl_ms: int = 45_000  # 45 seconds
    dedupe_ttl_ms: int = 60_000  # 60 seconds
    dedupe_max_entries: int = 1000
    
    # Delta streaming
    delta_debounce_ms: int = 150  # 150ms debounce


@dataclass
class ToolConfig:
    """
    Tool configuration
    
    Configuration for tool execution and policy.
    """
    # Execution limits
    max_tool_execution_time: int = 300  # 5 minutes
    max_parallel_tools: int = 1  # Sequential by default
    
    # Tool policy
    default_profile: Literal["default", "strict", "permissive", "coding"] = "default"
    
    # Owner-only enforcement
    enforce_owner_only: bool = True


@dataclass
class LLMConfig:
    """
    LLM provider configuration
    
    Configuration for LLM behavior and limits.
    """
    # Model defaults
    default_model: str = "google/gemini-3-pro-preview"
    
    # Retry configuration
    max_retries: int = 3
    retry_delay: float = 1.0  # seconds
    
    # Token limits
    max_tokens: int = 4096
    
    # Tool control
    tool_choice: Literal["auto", "none", "required"] | None = "auto"
    
    # Streaming
    enable_streaming: bool = True


@dataclass
class OpenClawConfig:
    """
    Complete OpenClaw configuration
    
    Top-level configuration combining all subsystems.
    """
    agent: AgentConfig = None
    gateway: GatewayConfig = None
    tool: ToolConfig = None
    llm: LLMConfig = None
    
    def __post_init__(self):
        """Initialize default configs if not provided"""
        if self.agent is None:
            self.agent = AgentConfig.default()
        if self.gateway is None:
            self.gateway = GatewayConfig()
        if self.tool is None:
            self.tool = ToolConfig()
        if self.llm is None:
            self.llm = LLMConfig()
    
    @classmethod
    def default(cls) -> "OpenClawConfig":
        """Create default configuration"""
        return cls()
    
    @classmethod
    def strict(cls) -> "OpenClawConfig":
        """Create strict configuration (minimal resources)"""
        return cls(
            agent=AgentConfig.strict(),
            tool=ToolConfig(default_profile="strict")
        )
    
    @classmethod
    def permissive(cls) -> "OpenClawConfig":
        """Create permissive configuration (maximum resources)"""
        return cls(
            agent=AgentConfig.permissive(),
            tool=ToolConfig(default_profile="permissive", enforce_owner_only=False)
        )

"""
Channel onboarding adapter types (aligned with TypeScript onboarding-types.ts)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Literal

DmPolicy = Literal["off", "allowlist", "open"]


@dataclass
class ChannelOnboardingStatus:
    """Status of channel configuration"""
    
    configured: bool
    """Whether the channel is configured"""
    
    enabled: bool = False
    """Whether the channel is enabled"""
    
    has_token: bool = False
    """Whether authentication token exists"""
    
    dm_policy: DmPolicy | None = None
    """DM policy setting"""
    
    accounts: list[str] | None = None
    """List of configured account IDs"""
    
    issues: list[str] | None = None
    """Configuration issues"""


@dataclass
class ChannelOnboardingDmPolicy:
    """DM policy configuration"""
    
    policy: DmPolicy
    """Policy type"""
    
    allow_from: list[str] | None = None
    """Allowlist of user IDs"""


class ChannelOnboardingAdapter(ABC):
    """
    Base class for channel onboarding adapters
    
    Each channel (Telegram, Discord, Slack, etc.) implements this interface
    to provide guided onboarding experience.
    """
    
    def __init__(self, channel_id: str):
        self.channel_id = channel_id
    
    @abstractmethod
    async def get_status(self, config: dict[str, Any]) -> ChannelOnboardingStatus:
        """
        Check current configuration status
        
        Args:
            config: Current OpenClaw configuration
            
        Returns:
            Status indicating what's configured
        """
        pass
    
    @abstractmethod
    async def configure(
        self,
        config: dict[str, Any],
        prompter: Any,
    ) -> dict[str, Any]:
        """
        Interactive configuration wizard
        
        Args:
            config: Current configuration
            prompter: Wizard prompter for user interaction
            
        Returns:
            Updated configuration
        """
        pass
    
    @abstractmethod
    async def configure_dm_policy(
        self,
        config: dict[str, Any],
        prompter: Any,
        account_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Configure DM access policy
        
        Args:
            config: Current configuration
            prompter: Wizard prompter
            account_id: Specific account ID (for multi-account channels)
            
        Returns:
            Updated configuration
        """
        pass
    
    async def validate_token(self, token: str) -> bool:
        """
        Validate authentication token
        
        Args:
            token: Token to validate
            
        Returns:
            True if valid
        """
        # Default implementation - override in subclass
        return bool(token and len(token) > 10)
    
    def get_help_text(self) -> str:
        """Get help text for configuring this channel"""
        return f"See documentation for {self.channel_id} setup"

"""Session send policy configuration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SendPolicyType(str, Enum):
    """Send policy types."""
    
    ALWAYS = "always"  # Always send messages
    NEVER = "never"  # Never send messages  
    ASK = "ask"  # Ask before sending


@dataclass
class SendPolicy:
    """Send policy for a session."""
    
    policy_type: SendPolicyType = SendPolicyType.ALWAYS
    allow_a2a: bool = True  # Allow agent-to-agent messages
    allow_broadcast: bool = True  # Allow broadcast messages


def resolve_send_policy(config: dict, session_key: str) -> SendPolicy:
    """Resolve send policy for session.
    
    Args:
        config: Configuration dict
        session_key: Session key
    
    Returns:
        SendPolicy for this session
    """
    # Get session-specific policy
    session_policies = config.get("session_policies", {})
    policy_data = session_policies.get(session_key, {})
    
    return SendPolicy(
        policy_type=SendPolicyType(policy_data.get("type", "always")),
        allow_a2a=policy_data.get("allow_a2a", True),
        allow_broadcast=policy_data.get("allow_broadcast", True)
    )

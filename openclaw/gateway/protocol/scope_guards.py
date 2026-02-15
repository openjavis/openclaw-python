"""
Event scope guards for filtering events based on client permissions.

This module implements event filtering to ensure clients only receive events
they're authorized to see based on their role and scopes.

Matches openclaw/src/gateway/server-broadcast.ts EVENT_SCOPE_GUARDS
"""

# Event scope guards mapping
# Maps event names to required scopes (client must have at least one of these scopes)
EVENT_SCOPE_GUARDS: dict[str, set[str]] = {
    # Agent and chat events require read access
    "agent": {"operator.read"},
    "chat": {"operator.read"},
    
    # Cron events require read access
    "cron": {"operator.read"},
    
    # Node pairing events require admin access
    "node.pair.requested": {"operator.admin"},
    "node.pair.resolved": {"operator.admin"},
    
    # Device pairing events require admin access
    "device.pair.requested": {"operator.admin"},
    "device.pair.resolved": {"operator.admin"},
    
    # Execution approval events require approvals scope
    "exec.approval.requested": {"operator.approvals"},
    "exec.approval.resolved": {"operator.approvals"},
    
    # Node invoke events require admin access
    "node.invoke.request": {"operator.admin"},
    "node.invoke.response": {"operator.admin"},
    
    # Voice wake events require admin access
    "voicewake.changed": {"operator.admin"},
    
    # System events typically require read access
    "presence": {"operator.read"},
    "health": {"operator.read"},
    "heartbeat": {"operator.read"},
    
    # Connect, tick, and shutdown events have no guards (always allowed)
    # "connect.challenge": no guard
    # "tick": no guard
    # "shutdown": no guard
}


def event_passes_scope_guard(event: str, client_scopes: set[str]) -> bool:
    """
    Check if client has required scopes to receive an event.
    
    Args:
        event: Event name
        client_scopes: Set of scopes the client has
        
    Returns:
        True if client should receive the event, False otherwise
        
    Notes:
        - Events without guards are allowed for all clients
        - Client needs at least one of the required scopes
        - Empty client scopes only pass events with no guards
    """
    required_scopes = EVENT_SCOPE_GUARDS.get(event)
    
    # No guard = allowed for all
    if not required_scopes:
        return True
    
    # Check if client has any of the required scopes
    return bool(required_scopes & client_scopes)


def get_required_scopes(event: str) -> set[str] | None:
    """
    Get required scopes for an event.
    
    Args:
        event: Event name
        
    Returns:
        Set of required scopes, or None if no guards
    """
    return EVENT_SCOPE_GUARDS.get(event)


__all__ = [
    "EVENT_SCOPE_GUARDS",
    "event_passes_scope_guard",
    "get_required_scopes",
]

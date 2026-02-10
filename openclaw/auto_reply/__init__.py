"""Auto-Reply system for openclaw

Handles automated message processing and response generation.
Matches TypeScript openclaw/src/auto-reply/ architecture.
"""

from .dispatch import dispatch_inbound_message
from .inbound_context import finalize_inbound_context, InboundContext
from .envelope import InboundEnvelope
from .command_detection import detect_command
from .commands_registry import CommandRegistry, get_global_command_registry

__all__ = [
    "dispatch_inbound_message",
    "finalize_inbound_context",
    "InboundContext",
    "InboundEnvelope",
    "detect_command",
    "CommandRegistry",
    "get_global_command_registry",
]

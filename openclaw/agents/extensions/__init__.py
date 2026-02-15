"""
Agent Extensions

Extensions for enhancing agent behavior with additional features.
"""

from .context_pruning import (
    ContextPruningSettings,
    prune_context_messages,
)

__all__ = [
    "ContextPruningSettings",
    "prune_context_messages",
]

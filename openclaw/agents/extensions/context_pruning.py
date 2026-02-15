"""
Context Pruning Extension

Intelligent context pruning with TTL and soft-trim modes.
Matches TypeScript openclaw/src/agents/pi-extensions/context-pruning/

This extension helps manage context window size by intelligently pruning
old or less relevant messages while preserving essential context.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Literal

logger = logging.getLogger(__name__)


@dataclass
class ContextPruningSettings:
    """
    Context pruning settings.
    
    Modes:
    - disabled: No pruning
    - cache-ttl: Only prune if cache TTL expired
    - soft-trim: Prune to keep within soft_trim_ratio of window
    
    Attributes:
        mode: Pruning mode
        ttl_ms: Time-to-live in milliseconds for cache-ttl mode
        soft_trim_ratio: Target ratio of context window (e.g., 0.75 = 75%)
        keep_bootstrap_safe: Protect messages before first user message
        prunable_tools: Set of tool names whose results can be pruned
    """
    mode: Literal["disabled", "cache-ttl", "soft-trim"] = "disabled"
    ttl_ms: int = 300000  # 5 minutes default
    soft_trim_ratio: float = 0.75
    keep_bootstrap_safe: bool = True
    prunable_tools: set[str] = field(default_factory=lambda: {
        "bash", "shell", "read", "write", "edit", "glob", "grep"
    })


def prune_context_messages(
    messages: list[dict[str, Any]],
    settings: ContextPruningSettings,
    context_window_tokens: int,
    is_tool_prunable: Callable[[str], bool] | None = None,
    current_time_ms: int | None = None,
) -> list[dict[str, Any]]:
    """
    Prune context messages based on settings.
    
    Modes:
    - disabled: Return messages unchanged
    - cache-ttl: Only prune if cache TTL expired
    - soft-trim: Prune to keep within soft_trim_ratio of window
    
    Always protects:
    - System messages
    - Messages before first user message (bootstrap safety)
    - User messages
    - Assistant text messages
    
    Can prune:
    - Tool results (if tool is prunable)
    - Old bash/shell execution results
    - File read results
    
    Args:
        messages: List of message dictionaries
        settings: Pruning settings
        context_window_tokens: Total context window size in tokens
        is_tool_prunable: Optional custom function to check if tool is prunable
        current_time_ms: Current time in milliseconds (for TTL checks)
        
    Returns:
        Pruned message list
    """
    if settings.mode == "disabled":
        return messages
    
    if not messages:
        return messages
    
    # Use provided prunable check or default to settings
    if is_tool_prunable is None:
        is_tool_prunable = lambda tool_name: tool_name in settings.prunable_tools
    
    # Find first user message (bootstrap safety boundary)
    first_user_idx = -1
    if settings.keep_bootstrap_safe:
        for i, msg in enumerate(messages):
            if msg.get("role") == "user":
                first_user_idx = i
                break
    
    # Calculate token budget for soft-trim mode
    token_budget = None
    if settings.mode == "soft-trim":
        token_budget = int(context_window_tokens * settings.soft_trim_ratio)
    
    # Prune messages
    pruned = []
    current_tokens = 0
    
    for i, msg in enumerate(messages):
        role = msg.get("role")
        
        # Always keep messages before first user (bootstrap safety)
        if first_user_idx >= 0 and i < first_user_idx:
            pruned.append(msg)
            current_tokens += _estimate_message_tokens(msg)
            continue
        
        # Always keep system messages
        if role == "system":
            pruned.append(msg)
            current_tokens += _estimate_message_tokens(msg)
            continue
        
        # Always keep user messages
        if role == "user":
            pruned.append(msg)
            current_tokens += _estimate_message_tokens(msg)
            continue
        
        # Always keep assistant text messages
        if role == "assistant":
            pruned.append(msg)
            current_tokens += _estimate_message_tokens(msg)
            continue
        
        # Check if we can prune tool results
        if role in ["toolResult", "tool"]:
            tool_name = msg.get("toolName", "")
            tool_call_id = msg.get("toolCallId", "")
            
            # Check if tool is prunable
            if not is_tool_prunable(tool_name):
                # Not prunable, keep it
                pruned.append(msg)
                current_tokens += _estimate_message_tokens(msg)
                continue
            
            # For cache-ttl mode, check TTL
            if settings.mode == "cache-ttl":
                timestamp = msg.get("timestamp", 0)
                if current_time_ms and timestamp:
                    age_ms = current_time_ms - timestamp
                    if age_ms < settings.ttl_ms:
                        # Still within TTL, keep it
                        pruned.append(msg)
                        current_tokens += _estimate_message_tokens(msg)
                        continue
                    else:
                        # TTL expired, prune it
                        logger.debug(f"Pruning tool result (TTL expired): {tool_name} ({tool_call_id})")
                        continue
                else:
                    # No timestamp, keep it to be safe
                    pruned.append(msg)
                    current_tokens += _estimate_message_tokens(msg)
                    continue
            
            # For soft-trim mode, check if we're over budget
            if settings.mode == "soft-trim" and token_budget:
                msg_tokens = _estimate_message_tokens(msg)
                if current_tokens + msg_tokens > token_budget:
                    # Would exceed budget, prune it
                    logger.debug(f"Pruning tool result (soft-trim): {tool_name} ({tool_call_id})")
                    continue
                else:
                    # Still within budget, keep it
                    pruned.append(msg)
                    current_tokens += msg_tokens
                    continue
            
            # Default: keep the message
            pruned.append(msg)
            current_tokens += _estimate_message_tokens(msg)
        else:
            # Unknown role, keep it to be safe
            pruned.append(msg)
            current_tokens += _estimate_message_tokens(msg)
    
    logger.info(
        f"Context pruning ({settings.mode}): {len(messages)} -> {len(pruned)} messages "
        f"(estimated {current_tokens} tokens)"
    )
    
    return pruned


def _estimate_message_tokens(msg: dict[str, Any]) -> int:
    """
    Estimate tokens for a single message.
    
    Uses improved estimation from context.py.
    
    Args:
        msg: Message dictionary
        
    Returns:
        Estimated token count
    """
    # Import here to avoid circular dependency
    from ..context import estimate_tokens_from_text
    
    # Estimate tokens from string representation
    msg_str = str(msg)
    return estimate_tokens_from_text(msg_str)


def should_prune_tool_result(
    tool_name: str,
    tool_call_id: str,
    timestamp: int | None,
    settings: ContextPruningSettings,
    current_time_ms: int | None = None,
) -> bool:
    """
    Determine if a tool result should be pruned.
    
    Args:
        tool_name: Name of the tool
        tool_call_id: Tool call ID
        timestamp: Message timestamp in milliseconds
        settings: Pruning settings
        current_time_ms: Current time in milliseconds
        
    Returns:
        True if should prune, False otherwise
    """
    # Check if tool is prunable
    if tool_name not in settings.prunable_tools:
        return False
    
    # For cache-ttl mode, check TTL
    if settings.mode == "cache-ttl":
        if not timestamp or not current_time_ms:
            return False
        
        age_ms = current_time_ms - timestamp
        return age_ms >= settings.ttl_ms
    
    # For soft-trim mode, caller handles budget checking
    # This function just checks if it's eligible for pruning
    return settings.mode == "soft-trim"


def get_pruning_settings_from_config(config: dict | None) -> ContextPruningSettings:
    """
    Get pruning settings from configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        ContextPruningSettings instance
    """
    if not config:
        return ContextPruningSettings()
    
    pruning_config = config.get("agents", {}).get("defaults", {}).get("contextPruning", {})
    
    if not pruning_config:
        return ContextPruningSettings()
    
    # Parse mode
    mode = pruning_config.get("mode", "disabled")
    if mode not in ["disabled", "cache-ttl", "soft-trim"]:
        logger.warning(f"Invalid pruning mode '{mode}', defaulting to 'disabled'")
        mode = "disabled"
    
    # Parse TTL (supports "5m", "300s", etc.)
    ttl_str = pruning_config.get("ttl", "5m")
    ttl_ms = _parse_time_string(ttl_str)
    
    # Parse soft trim ratio
    soft_trim_ratio = float(pruning_config.get("softTrimRatio", 0.75))
    
    # Parse prunable tools
    prunable_tools = set(pruning_config.get("prunableTools", [
        "bash", "shell", "read", "write", "edit", "glob", "grep"
    ]))
    
    return ContextPruningSettings(
        mode=mode,
        ttl_ms=ttl_ms,
        soft_trim_ratio=soft_trim_ratio,
        prunable_tools=prunable_tools,
    )


def _parse_time_string(time_str: str) -> int:
    """
    Parse time string to milliseconds.
    
    Supports: "5m", "300s", "5000ms"
    
    Args:
        time_str: Time string
        
    Returns:
        Time in milliseconds
    """
    time_str = time_str.strip().lower()
    
    if time_str.endswith("ms"):
        return int(time_str[:-2])
    elif time_str.endswith("s"):
        return int(time_str[:-1]) * 1000
    elif time_str.endswith("m"):
        return int(time_str[:-1]) * 60 * 1000
    elif time_str.endswith("h"):
        return int(time_str[:-1]) * 60 * 60 * 1000
    else:
        # Assume milliseconds
        return int(time_str)

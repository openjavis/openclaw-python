"""
Group message gating with mention patterns.

Determines whether group messages should trigger auto-reply
based on mention patterns and configuration.

Matches openclaw/src/web/auto-reply/group-gating.ts
"""
from __future__ import annotations

import re


def build_mention_patterns(config: dict, bot_name: str | None = None) -> list[str]:
    """
    Build mention patterns from config.
    
    Args:
        config: Account config with mentionPatterns
        bot_name: Bot display name for default pattern
        
    Returns:
        List of mention patterns (regex strings)
    """
    patterns = []
    
    # Get configured patterns
    if isinstance(config, dict):
        mention_patterns = config.get('mentionPatterns', [])
        if isinstance(mention_patterns, list):
            patterns.extend(mention_patterns)
    
    # Add default bot name pattern
    if bot_name:
        # Escape special regex characters
        escaped_name = re.escape(bot_name)
        patterns.append(f"@{escaped_name}")
        patterns.append(escaped_name)
    
    return patterns


def check_mentions(text: str, mention_patterns: list[str]) -> bool:
    """
    Check if text contains any mention patterns.
    
    Args:
        text: Message text to check
        mention_patterns: List of regex patterns
        
    Returns:
        True if text contains a mention, False otherwise
    """
    if not text or not mention_patterns:
        return False
    
    text_lower = text.lower()
    
    for pattern in mention_patterns:
        if not pattern:
            continue
        
        try:
            # Try regex match
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        except re.error:
            # Fallback to simple substring match
            if pattern.lower() in text_lower:
                return True
    
    return False


def check_allow_from(sender_id: str, sender_name: str | None, allow_from: list[str] | None) -> bool:
    """
    Check if sender is in allowFrom list.
    
    Args:
        sender_id: Sender identifier
        sender_name: Sender display name
        allow_from: List of allowed sender patterns
        
    Returns:
        True if sender is allowed, False otherwise
    """
    if not allow_from:
        return True  # No restrictions
    
    if not sender_id:
        return False
    
    # Check sender ID
    if sender_id in allow_from:
        return True
    
    # Check sender name
    if sender_name and sender_name in allow_from:
        return True
    
    # Check patterns
    sender_id_lower = sender_id.lower()
    sender_name_lower = (sender_name or "").lower()
    
    for pattern in allow_from:
        if not pattern:
            continue
        
        pattern_lower = pattern.lower()
        
        # Exact match
        if pattern_lower == sender_id_lower or pattern_lower == sender_name_lower:
            return True
        
        # Wildcard patterns
        if "*" in pattern:
            regex_pattern = pattern.replace("*", ".*")
            try:
                if re.match(regex_pattern, sender_id, re.IGNORECASE):
                    return True
                if sender_name and re.match(regex_pattern, sender_name, re.IGNORECASE):
                    return True
            except re.error:
                pass
    
    return False


def apply_group_gating(
    message: dict,
    config: dict,
    mention_patterns: list[str] | None = None
) -> bool:
    """
    Check if group message should trigger reply.
    
    Rules:
    - Always reply to DMs (peer_kind == "dm")
    - Group messages require mention unless alwaysGroupActivation
    - Check allowFrom patterns if configured
    
    Args:
        message: Message dict with {text, peer_kind, sender_id, sender_name}
        config: Account config with auto-reply settings
        mention_patterns: Mention patterns (built from config if not provided)
        
    Returns:
        True if message should trigger reply, False otherwise
    """
    # Always reply to DMs
    peer_kind = message.get("peer_kind", "dm")
    if peer_kind == "dm":
        return True
    
    # Check allowFrom filter
    allow_from = config.get("allowFrom")
    if allow_from:
        sender_id = message.get("sender_id", "")
        sender_name = message.get("sender_name")
        if not check_allow_from(sender_id, sender_name, allow_from):
            return False
    
    # Check if always active in groups
    always_group_activation = config.get("alwaysGroupActivation", False)
    if always_group_activation:
        return True
    
    # Check mentions
    text = message.get("text", "")
    if not mention_patterns:
        mention_patterns = build_mention_patterns(config, message.get("bot_name"))
    
    return check_mentions(text, mention_patterns)


__all__ = [
    "build_mention_patterns",
    "check_mentions",
    "check_allow_from",
    "apply_group_gating",
]

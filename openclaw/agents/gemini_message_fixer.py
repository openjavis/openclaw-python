"""
Gemini Message Sequence Fixer

Fixes message sequences to comply with Gemini API requirements:
- No consecutive assistant messages
- function call must follow user or tool message
- Proper turn structure
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def fix_gemini_message_sequence(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Fix message sequence to comply with Gemini API requirements.
    
    Rules:
    1. No consecutive assistant messages (merge them)
    2. function call must follow user or tool message
    3. Remove empty messages
    
    Args:
        messages: List of message dicts with 'role' and 'content'
    
    Returns:
        Fixed list of messages
    """
    if not messages:
        return messages
    
    fixed: list[dict[str, Any]] = []
    
    for i, msg in enumerate(messages):
        role = msg.get("role")
        
        # Skip system messages in validation (Gemini handles them separately)
        if role == "system":
            fixed.append(msg)
            continue
        
        # Check if we can add this message
        if not fixed:
            # First message (after system)
            if role == "user":
                fixed.append(msg)
            else:
                # Skip non-user first message
                logger.warning(f"Skipping non-user first message: {role}")
            continue
        
        last_msg = fixed[-1]
        last_role = last_msg.get("role")
        
        # Rule 1: No consecutive assistant messages
        if role == "assistant" and last_role == "assistant":
            # Merge with previous assistant message
            logger.debug("Merging consecutive assistant messages")
            last_content = last_msg.get("content", "")
            new_content = msg.get("content", "")
            
            # Combine content
            if last_content and new_content:
                last_msg["content"] = f"{last_content}\n\n{new_content}"
            elif new_content:
                last_msg["content"] = new_content
            
            # Combine tool_calls if any
            if msg.get("tool_calls"):
                if not last_msg.get("tool_calls"):
                    last_msg["tool_calls"] = []
                last_msg["tool_calls"].extend(msg["tool_calls"])
            
            continue
        
        # Rule 2: tool message must follow assistant with tool_calls
        if role == "tool":
            if last_role != "assistant":
                # CRITICAL: Skip invalid tool messages that can't be fixed
                # If last message is also assistant, we can't insert another assistant
                logger.warning(f"Tool message not after assistant, skipping to avoid sequence error")
                continue
            elif not last_msg.get("tool_calls"):
                # Assistant exists but has no tool_calls, add them retroactively
                tool_name = msg.get("name") or "unknown_function"
                if not tool_name or not str(tool_name).strip():
                    tool_name = "unknown_function"
                last_msg["tool_calls"] = [{
                    "id": msg.get("tool_call_id", "unknown"),
                    "type": "function",
                    "name": tool_name,
                    "arguments": {}
                }]
                logger.debug(f"Added tool_calls to previous assistant message")
        
        # Rule 3: assistant with tool_calls must be followed by tool
        if role == "user" and last_role == "assistant" and last_msg.get("tool_calls"):
            logger.warning("Assistant with tool_calls not followed by tool, removing tool_calls")
            last_msg.pop("tool_calls", None)
        
        # Add the message
        fixed.append(msg)
    
    # Final cleanup: remove empty content messages (except those with tool_calls)
    cleaned = []
    for msg in fixed:
        if msg.get("role") == "system":
            cleaned.append(msg)
        elif msg.get("tool_calls"):
            # Keep messages with tool_calls even if content is empty
            cleaned.append(msg)
        elif msg.get("content") and str(msg["content"]).strip():
            # Keep messages with non-empty content
            cleaned.append(msg)
        elif msg.get("role") == "tool":
            # Keep tool messages even if content is empty
            cleaned.append(msg)
        else:
            logger.debug(f"Removing empty message: {msg.get('role')}")
    
    return cleaned


def validate_gemini_sequence(messages: list[dict[str, Any]]) -> tuple[bool, str]:
    """
    Validate if message sequence is valid for Gemini API.
    
    Returns:
        (is_valid, error_message)
    """
    if not messages:
        return True, ""
    
    prev_role = None
    prev_had_tool_calls = False
    
    for i, msg in enumerate(messages):
        role = msg.get("role")
        
        # Skip system messages
        if role == "system":
            continue
        
        # First non-system message must be user
        if prev_role is None:
            if role != "user":
                return False, f"First message must be 'user', got '{role}'"
            prev_role = role
            continue
        
        # Check for consecutive assistant messages
        if role == "assistant" and prev_role == "assistant":
            return False, f"Consecutive assistant messages at index {i}"
        
        # Check tool message follows assistant with tool_calls
        if role == "tool" and not prev_had_tool_calls:
            return False, f"Tool message at {i} not after assistant with tool_calls"
        
        # Check assistant with tool_calls is followed by tool
        if prev_had_tool_calls and role not in ["tool", "assistant"]:
            return False, f"Assistant with tool_calls not followed by tool at {i}"
        
        prev_role = role
        prev_had_tool_calls = (role == "assistant" and msg.get("tool_calls"))
    
    return True, ""

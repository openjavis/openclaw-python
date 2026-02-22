"""
History Utils - session history cleaning and limiting

Aligned with openclaw/src/agents/pi-embedded-runner/run/attempt.ts
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def sanitize_session_history(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Sanitize session history by removing metadata and empty messages.
    
    Matches TypeScript sanitizeSessionHistory() behavior from pi-mono/packages/coding-agent/src/core/google.ts:
    - Remove thinking, details, usage, cost fields
    - Remove empty tool results
    - Remove messages without role or content
    - Keep only essential fields (id, timestamp, role, content)
    
    Args:
        messages: Raw session messages
        
    Returns:
        Cleaned messages
    """
    sanitized = []
    
    for msg in messages:
        # Skip messages without role
        if not msg.get("role"):
            logger.debug(f"Skipping message without role: {msg}")
            continue
        
        # Create clean copy without metadata
        clean_msg = {
            "role": msg["role"],
            "content": msg.get("content"),
        }
        
        # Preserve essential fields only
        if "id" in msg:
            clean_msg["id"] = msg["id"]
        if "timestamp" in msg:
            clean_msg["timestamp"] = msg["timestamp"]
        
        # Support both camelCase (TypeScript) and snake_case (Python)
        if "toolCallId" in msg:
            clean_msg["toolCallId"] = msg["toolCallId"]
        if "tool_call_id" in msg:
            clean_msg["tool_call_id"] = msg["tool_call_id"]
        
        if "toolName" in msg:
            clean_msg["toolName"] = msg["toolName"]
        if "name" in msg:
            clean_msg["name"] = msg["name"]
        
        if "tool_calls" in msg:
            clean_msg["tool_calls"] = msg["tool_calls"]
        
        # Skip empty content
        content = clean_msg["content"]
        if content is None or content == "":
            logger.debug(f"Skipping message without content: role={msg.get('role')}")
            continue
        
        # Skip empty tool results
        if msg["role"] in ["toolResult", "tool"]:
            if isinstance(content, list) and len(content) == 0:
                logger.debug(f"Skipping empty tool result: toolCallId={msg.get('toolCallId')}")
                continue
            if isinstance(content, str) and not content.strip():
                logger.debug(f"Skipping empty tool result: toolCallId={msg.get('toolCallId')}")
                continue
        
        # Skip messages with empty content array (system messages)
        if isinstance(content, list) and len(content) == 0:
            logger.debug(f"Skipping message with empty content array: role={msg.get('role')}")
            continue
        
        sanitized.append(clean_msg)
    
    logger.debug(f"Sanitized history: {len(messages)} -> {len(sanitized)} messages")
    return sanitized


def limit_history_turns(
    messages: list[dict[str, Any]],
    max_turns: int | None = None,
    provider: str | None = None
) -> list[dict[str, Any]]:
    """
    Limit history to most recent N user messages and their responses.
    
    Aligned with TypeScript openclaw/src/agents/pi-embedded-runner/history.ts:
    - Count only user messages (not user-assistant pairs)
    - Scan from end backwards
    - Keep last N user messages + all messages after the Nth user message
    
    Args:
        messages: Session messages
        max_turns: Maximum number of user messages to keep (None = no limit)
        provider: Provider name for default limits
        
    Returns:
        Limited messages
    """
    # Apply provider-specific defaults
    if max_turns is None and provider:
        if provider.lower() in ["gemini", "google"]:
            max_turns = 20  # Keep last 20 user messages
        elif provider.lower() in ["anthropic", "claude"]:
            max_turns = 30
        else:
            max_turns = 50  # Default
    
    if max_turns is None or max_turns <= 0:
        return messages
    
    if len(messages) == 0:
        return messages
    
    # Scan backwards to find the Nth user message from the end
    user_count = 0
    last_user_index = len(messages)  # Track position of Nth user message
    
    for i in range(len(messages) - 1, -1, -1):
        if messages[i].get("role") == "user":
            user_count += 1
            if user_count > max_turns:
                # Found the (N+1)th user message, cut at last_user_index
                break
            last_user_index = i  # Update to current user position
    
    # Return slice from last_user_index
    if last_user_index > 0 and last_user_index < len(messages):
        limited = messages[last_user_index:]
        kept_users = min(user_count, max_turns)
        logger.info(f"✂️ History limited: {len(messages)} -> {len(limited)} messages (kept last {kept_users} user messages)")
        return limited
    
    return messages


def count_history_turns(messages: list[dict[str, Any]]) -> int:
    """
    Count number of user-assistant turns in history
    
    Args:
        messages: Session messages
        
    Returns:
        Number of complete turns
    """
    turn_count = 0
    last_role = None
    
    for msg in messages:
        role = msg.get("role")
        if role == "assistant" and last_role == "user":
            turn_count += 1
        last_role = role
    
    return turn_count


def find_last_message_by_role(
    messages: list[dict[str, Any]],
    role: str
) -> dict[str, Any] | None:
    """
    Find last message with given role
    
    Args:
        messages: Session messages
        role: Role to search for
        
    Returns:
        Last message with role, or None
    """
    for msg in reversed(messages):
        if msg.get("role") == role:
            return msg
    return None


def extract_text_from_content(content: Any) -> str:
    """
    Extract text from message content (supports both string and array formats)
    
    Args:
        content: Message content (string or array of content blocks)
        
    Returns:
        Extracted text
    """
    if isinstance(content, str):
        return content
    
    if isinstance(content, list):
        texts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                texts.append(block.get("text", ""))
            elif isinstance(block, str):
                texts.append(block)
        return "".join(texts)
    
    return str(content)


def inject_history_images_into_messages(
    messages: list[dict[str, Any]],
    images: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Inject image references into message history for multi-turn conversations.

    Matches TypeScript injectHistoryImagesIntoMessages() in attempt.ts:
    - Takes message history, finds image references by index
    - Converts string content to array format where necessary
    - Prevents duplicates (only injects if not already present)

    Args:
        messages: Message history dicts.
        images: List of image URLs / base64 data to inject into the last
                user message if they are not already embedded.

    Returns:
        Updated messages list (shallow copy of the list, dicts may be mutated).
    """
    if not images:
        return messages

    messages = list(messages)  # shallow copy

    # Find the last user message
    last_user_idx = -1
    for i in range(len(messages) - 1, -1, -1):
        if messages[i].get("role") == "user":
            last_user_idx = i
            break

    if last_user_idx == -1:
        return messages

    msg = dict(messages[last_user_idx])
    content = msg.get("content", [])

    # Normalize content to list format
    if isinstance(content, str):
        content = [{"type": "text", "text": content}]
    else:
        content = list(content)

    # Collect already-present image URLs/data to deduplicate
    existing_images: set[str] = set()
    for block in content:
        if isinstance(block, dict) and block.get("type") == "image":
            src = block.get("source", {})
            if isinstance(src, dict):
                existing_images.add(src.get("url", "") or src.get("data", ""))
            elif isinstance(src, str):
                existing_images.add(src)

    # Inject new images
    for img in images:
        if img in existing_images:
            continue
        if img.startswith("data:"):
            # base64 data URI
            try:
                header, data = img.split(",", 1)
                media_type = header.split(":")[1].split(";")[0]
            except Exception:
                media_type = "image/jpeg"
                data = img
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": data,
                },
            })
        else:
            # URL reference
            content.append({
                "type": "image",
                "source": {
                    "type": "url",
                    "url": img,
                },
            })
        existing_images.add(img)

    msg["content"] = content
    messages[last_user_idx] = msg
    return messages


def validate_message_sequence(messages: list[dict[str, Any]]) -> tuple[bool, str | None]:
    """
    Validate message sequence for correct role ordering
    
    Checks for:
    - User messages followed by assistant responses
    - No consecutive messages of same role
    - Tool messages between assistant and next assistant
    
    Args:
        messages: Session messages
        
    Returns:
        (is_valid, error_message)
    """
    if not messages:
        return True, None
    
    last_role = None
    
    for i, msg in enumerate(messages):
        role = msg.get("role")
        
        # Check for consecutive same roles (except tool)
        if role != "tool" and role == last_role:
            return False, f"Consecutive {role} messages at index {i}"
        
        last_role = role
    
    return True, None

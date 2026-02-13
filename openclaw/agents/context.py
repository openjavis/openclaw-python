"""
Context management and message conversion for agent system

This module provides:
- convert_to_llm: Convert AgentMessage to LLM format
- transform_context: Hook for context transformation
- Support for custom message types
- Context window management
- Message validation for different providers (Anthropic, Gemini)
- History limiting and sanitization

Matches pi-mono's message conversion logic.
"""
from __future__ import annotations

import asyncio
import re
from typing import Any

from .types import AgentMessage, Content, TextContent


# Custom message type support (extensible)
class CustomMessageTypes:
    """
    Registry for custom message types.
    
    Allows extensions to register custom message types and their converters.
    
    Example:
        ```python
        def convert_bash_execution(msg: dict) -> dict:
            return {
                "role": "user",
                "content": f"Executed: {msg['command']}\nOutput: {msg['output']}"
            }
        
        CustomMessageTypes.register("bashExecution", convert_bash_execution)
        ```
    """
    
    _converters: dict[str, Any] = {}
    
    @classmethod
    def register(cls, message_type: str, converter: Any) -> None:
        """Register custom message type converter"""
        cls._converters[message_type] = converter
    
    @classmethod
    def convert(cls, message_type: str, message: dict) -> dict | None:
        """Convert custom message type"""
        converter = cls._converters.get(message_type)
        if converter:
            return converter(message)
        return None


def convert_to_llm(messages: list[AgentMessage]) -> list[dict[str, Any]]:
    """
    Convert AgentMessage list to LLM-compatible format.
    
    Handles:
    - Standard message types (user, assistant, tool result)
    - Custom message types (bashExecution, custom, etc.)
    - Branch/compaction summaries with special wrapping
    - Filtering of excluded messages
    
    Matches pi-mono's convertToLlm behavior.
    
    Args:
        messages: List of AgentMessage objects
        
    Returns:
        List of LLM-compatible message dictionaries
        
    Example:
        ```python
        agent_messages = [
            UserMessage(content="Hello"),
            AssistantMessage(content=[TextContent(text="Hi!")]),
        ]
        
        llm_messages = convert_to_llm(agent_messages)
        # Returns: [
        #     {"role": "user", "content": "Hello"},
        #     {"role": "assistant", "content": "Hi!"}
        # ]
        ```
    """
    llm_messages: list[dict[str, Any]] = []
    
    for msg in messages:
        # Get message role
        role = getattr(msg, "role", None)
        if not role:
            continue
        
        # Handle different message types
        if role == "user":
            # User message
            content = _format_content(msg.content)
            llm_messages.append({
                "role": "user",
                "content": content
            })
        
        elif role == "assistant":
            # Assistant message
            content_list = getattr(msg, "content", [])
            
            # Convert content list to string or keep as list
            if isinstance(content_list, str):
                content = content_list
            elif isinstance(content_list, list):
                # Combine text content blocks
                text_parts = []
                for item in content_list:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                    elif hasattr(item, "type") and item.type == "text":
                        text_parts.append(item.text)
                content = "".join(text_parts)
            else:
                content = str(content_list)
            
            msg_dict = {
                "role": "assistant",
                "content": content
            }
            
            # Add tool calls if present
            tool_calls = getattr(msg, "tool_calls", None)
            if tool_calls:
                msg_dict["tool_calls"] = tool_calls
            
            # Add thinking if present (some providers support this)
            thinking = getattr(msg, "thinking", None)
            if thinking:
                msg_dict["thinking"] = thinking
            
            llm_messages.append(msg_dict)
        
        elif role == "toolResult":
            # Tool result message
            content = _format_content(getattr(msg, "content", []))
            
            llm_messages.append({
                "role": "tool",
                "tool_call_id": getattr(msg, "tool_call_id", ""),
                "content": content
            })
        
        elif role == "system":
            # System message
            content = _format_content(getattr(msg, "content", ""))
            llm_messages.append({
                "role": "system",
                "content": content
            })
        
        # Handle custom message types (if any)
        elif hasattr(msg, "custom_type"):
            custom_type = getattr(msg, "custom_type")
            custom_msg = CustomMessageTypes.convert(custom_type, msg.__dict__)
            if custom_msg:
                llm_messages.append(custom_msg)
    
    return llm_messages


def _format_content(content: Any) -> str:
    """
    Format content to string.
    
    Handles:
    - String content (pass through)
    - List of Content objects
    - Dict content
    
    Args:
        content: Content to format
        
    Returns:
        Formatted string
    """
    if isinstance(content, str):
        return content
    
    if isinstance(content, list):
        # List of content blocks
        parts = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    parts.append(item.get("text", ""))
                elif item.get("type") == "image":
                    # For images, include a placeholder
                    parts.append("[Image]")
            elif hasattr(item, "type"):
                if item.type == "text":
                    parts.append(item.text)
                elif item.type == "image":
                    parts.append("[Image]")
        return "".join(parts)
    
    return str(content)


async def transform_context(
    messages: list[AgentMessage],
    signal: asyncio.Event | None = None,
    max_messages: int | None = None,
    max_tokens: int | None = None,
) -> list[AgentMessage]:
    """
    Transform context before sending to LLM.
    
    This is a hook for implementing:
    - Context pruning (remove old messages)
    - Message summarization
    - External context injection
    - Token limit enforcement
    
    Default implementation does basic message limiting.
    Override in AgentLoopConfig for custom behavior.
    
    Args:
        messages: Current message list
        signal: Cancellation signal
        max_messages: Maximum number of messages to keep
        max_tokens: Maximum token count (approximate)
        
    Returns:
        Transformed message list
        
    Example:
        ```python
        # Keep only last 20 messages
        transformed = await transform_context(
            messages,
            max_messages=20
        )
        
        # Custom transformation
        async def my_transform(messages, signal):
            # Summarize old messages
            # Inject external context
            # Apply token limits
            return transformed_messages
        ```
    """
    # Check cancellation
    if signal and signal.is_set():
        return messages
    
    # If no limits specified, return as-is
    if max_messages is None and max_tokens is None:
        return messages
    
    # Separate system messages (always keep)
    system_messages = [m for m in messages if getattr(m, "role", None) == "system"]
    conversation_messages = [m for m in messages if getattr(m, "role", None) != "system"]
    
    # Apply message limit
    if max_messages is not None and len(conversation_messages) > max_messages:
        # Keep most recent messages
        conversation_messages = conversation_messages[-max_messages:]
    
    # Token limit would require actual token counting
    # For now, approximate with message limit
    # TODO: Implement proper token counting
    
    return system_messages + conversation_messages


def build_context_summary(messages: list[AgentMessage]) -> str:
    """
    Build summary of context for compaction.
    
    This creates a text summary of conversation history.
    Used when context window is exceeded.
    
    Args:
        messages: Messages to summarize
        
    Returns:
        Summary text
    """
    summary_parts = []
    summary_parts.append("<summary>")
    summary_parts.append("Previous conversation summary:")
    summary_parts.append("")
    
    for i, msg in enumerate(messages, 1):
        role = getattr(msg, "role", "unknown")
        content = _format_content(getattr(msg, "content", ""))
        
        # Truncate long content
        if len(content) > 200:
            content = content[:200] + "..."
        
        summary_parts.append(f"{i}. {role}: {content}")
    
    summary_parts.append("</summary>")
    
    return "\n".join(summary_parts)


def inject_summary_message(
    messages: list[AgentMessage],
    summary: str,
    at_index: int = 0
) -> list[AgentMessage]:
    """
    Inject summary message into conversation.
    
    Used after compaction to preserve context.
    
    Args:
        messages: Current messages
        summary: Summary text
        at_index: Where to insert (default: beginning)
        
    Returns:
        Messages with summary injected
    """
    from .types import UserMessage
    
    summary_msg = UserMessage(content=summary)
    
    # Insert at specified index
    new_messages = list(messages)
    new_messages.insert(at_index, summary_msg)
    
    return new_messages


def validate_gemini_turns(messages: list[AgentMessage]) -> list[AgentMessage]:
    """
    Validates and fixes conversation turn sequences for Gemini API.
    
    Gemini requires strict alternating user→assistant→tool→user pattern.
    Merges consecutive assistant messages together.
    
    Args:
        messages: List of agent messages
        
    Returns:
        Validated message list with consecutive assistant messages merged
        
    Example:
        ```python
        messages = [
            UserMessage(content="Hello"),
            AssistantMessage(content="Hi"),
            AssistantMessage(content="How are you?"),  # Will be merged with previous
        ]
        validated = validate_gemini_turns(messages)
        # Result has 2 messages: user, assistant (merged)
        ```
    """
    if not messages:
        return messages
    
    result: list[AgentMessage] = []
    last_role: str | None = None
    
    for msg in messages:
        if not msg or not hasattr(msg, "role"):
            result.append(msg)
            continue
        
        msg_role = msg.role
        
        # Merge consecutive assistant messages
        if msg_role == last_role and last_role == "assistant":
            if result:
                last_msg = result[-1]
                
                # Merge content
                last_content = getattr(last_msg, "content", [])
                current_content = getattr(msg, "content", [])
                
                merged_content = []
                if isinstance(last_content, list):
                    merged_content.extend(last_content)
                elif last_content:
                    merged_content.append(last_content)
                    
                if isinstance(current_content, list):
                    merged_content.extend(current_content)
                elif current_content:
                    merged_content.append(current_content)
                
                # Update last message
                last_msg.content = merged_content
                
                # Preserve usage and stop reason from current message
                if hasattr(msg, "usage"):
                    last_msg.usage = msg.usage
                if hasattr(msg, "stop_reason"):
                    last_msg.stop_reason = msg.stop_reason
                
                continue
        
        result.append(msg)
        last_role = msg_role
    
    return result


def validate_anthropic_turns(messages: list[AgentMessage]) -> list[AgentMessage]:
    """
    Validates and fixes conversation turn sequences for Anthropic API.
    
    Anthropic requires strict alternating user→assistant pattern.
    Merges consecutive user messages together.
    
    Args:
        messages: List of agent messages
        
    Returns:
        Validated message list with consecutive user messages merged
        
    Example:
        ```python
        messages = [
            UserMessage(content="Hello"),
            UserMessage(content="Are you there?"),  # Will be merged with previous
            AssistantMessage(content="Yes!"),
        ]
        validated = validate_anthropic_turns(messages)
        # Result has 2 messages: user (merged), assistant
        ```
    """
    if not messages:
        return messages
    
    result: list[AgentMessage] = []
    last_role: str | None = None
    
    for msg in messages:
        if not msg or not hasattr(msg, "role"):
            result.append(msg)
            continue
        
        msg_role = msg.role
        
        # Merge consecutive user messages
        if msg_role == last_role and last_role == "user":
            if result:
                last_msg = result[-1]
                
                # Merge content
                last_content = getattr(last_msg, "content", [])
                current_content = getattr(msg, "content", [])
                
                merged_content = []
                if isinstance(last_content, list):
                    merged_content.extend(last_content)
                elif last_content:
                    merged_content.append(last_content)
                    
                if isinstance(current_content, list):
                    merged_content.extend(current_content)
                elif current_content:
                    merged_content.append(current_content)
                
                # Update last message
                last_msg.content = merged_content
                
                # Preserve timestamp from current message
                if hasattr(msg, "timestamp"):
                    last_msg.timestamp = msg.timestamp
                
                continue
        
        result.append(msg)
        last_role = msg_role
    
    return result


def limit_history_turns(
    messages: list[AgentMessage],
    limit: int | None
) -> list[AgentMessage]:
    """
    Limits conversation history to the last N user turns.
    
    This reduces token usage for long-running sessions by keeping only
    recent conversation. Counts backward from the end and keeps the last
    N user messages and their associated assistant responses.
    
    Args:
        messages: List of messages to limit
        limit: Maximum number of user turns to keep (None = no limit)
        
    Returns:
        Limited message list
        
    Example:
        ```python
        # Keep only last 5 user turns
        limited = limit_history_turns(messages, limit=5)
        ```
    """
    if not limit or limit <= 0 or not messages:
        return messages
    
    user_count = 0
    last_user_index = len(messages)
    
    # Count backward to find the Nth user message
    for i in range(len(messages) - 1, -1, -1):
        if messages[i].role == "user":
            user_count += 1
            if user_count > limit:
                # Found more than limit, slice from next user message
                return messages[last_user_index:]
            last_user_index = i
    
    return messages


# Thread suffix regex pattern
THREAD_SUFFIX_REGEX = re.compile(r"^(.*)(?::(?:thread|topic):\d+)$", re.IGNORECASE)


def _strip_thread_suffix(value: str) -> str:
    """Strip thread/topic suffix from session key part."""
    match = THREAD_SUFFIX_REGEX.match(value)
    return match.group(1) if match else value


def get_dm_history_limit_from_session_key(
    session_key: str | None,
    config: dict | None
) -> int | None:
    """
    Extract DM history limit from session key and config.
    
    Supports per-DM overrides and provider defaults.
    Session key format: "agent:agentId:provider:dm:userId" or "provider:dm:userId"
    
    Args:
        session_key: Session key string
        config: OpenClaw configuration dict
        
    Returns:
        History limit for this DM, or None if not configured
        
    Example:
        ```python
        # Config with DM limits
        config = {
            "channels": {
                "telegram": {
                    "dmHistoryLimit": 20,
                    "dms": {
                        "123456": {"historyLimit": 50}
                    }
                }
            }
        }
        
        limit = get_dm_history_limit_from_session_key(
            "agent:main:telegram:dm:123456",
            config
        )
        # Returns: 50 (per-DM override)
        ```
    """
    if not session_key or not config:
        return None
    
    # Parse session key
    parts = [p for p in session_key.split(":") if p]
    
    # Remove "agent:agentId" prefix if present
    provider_parts = parts[2:] if len(parts) >= 3 and parts[0] == "agent" else parts
    
    if not provider_parts:
        return None
    
    provider = provider_parts[0].lower()
    
    if len(provider_parts) < 2:
        return None
    
    kind = provider_parts[1].lower()
    
    # Only apply to DM sessions
    if kind != "dm":
        return None
    
    # Extract user ID (may have thread suffix)
    user_id_raw = ":".join(provider_parts[2:]) if len(provider_parts) > 2 else ""
    user_id = _strip_thread_suffix(user_id_raw)
    
    # Get provider config
    channels = config.get("channels", {})
    if not isinstance(channels, dict):
        return None
    
    provider_config = channels.get(provider, {})
    if not isinstance(provider_config, dict):
        return None
    
    # Check per-DM override first
    if user_id:
        dms = provider_config.get("dms", {})
        if isinstance(dms, dict) and user_id in dms:
            dm_config = dms[user_id]
            if isinstance(dm_config, dict) and "historyLimit" in dm_config:
                return dm_config["historyLimit"]
    
    # Fall back to provider default
    return provider_config.get("dmHistoryLimit")


def sanitize_session_history(
    messages: list[AgentMessage],
    remove_empty: bool = True,
    remove_invalid_roles: bool = True
) -> list[AgentMessage]:
    """
    Sanitize session history by removing invalid messages.
    
    This removes:
    - Messages with no role
    - Messages with empty content (if remove_empty=True)
    - Messages with invalid roles (if remove_invalid_roles=True)
    
    Args:
        messages: List of messages to sanitize
        remove_empty: Remove messages with empty content
        remove_invalid_roles: Remove messages with invalid roles
        
    Returns:
        Sanitized message list
        
    Example:
        ```python
        sanitized = sanitize_session_history(messages)
        ```
    """
    if not messages:
        return messages
    
    valid_roles = {"user", "assistant", "system", "tool", "toolResult"}
    result: list[AgentMessage] = []
    
    for msg in messages:
        # Check for role
        if not hasattr(msg, "role"):
            continue
        
        role = msg.role
        
        # Check for invalid role
        if remove_invalid_roles and role not in valid_roles:
            continue
        
        # Check for empty content
        if remove_empty:
            content = getattr(msg, "content", None)
            if content is None:
                continue
            if isinstance(content, str) and not content.strip():
                continue
            if isinstance(content, list) and not content:
                continue
        
        result.append(msg)
    
    return result


def inject_history_images_into_messages(
    messages: list[AgentMessage],
    history_images_by_index: dict[int, list]
) -> bool:
    """
    Inject history images into messages at specified indices.
    
    This adds image content to messages that were referenced in markdown
    (e.g., ![description](path/to/image.png)) but didn't have the actual
    image data loaded.
    
    Args:
        messages: List of messages to modify
        history_images_by_index: Map of message index to list of image content
        
    Returns:
        True if any messages were modified, False otherwise
        
    Example:
        ```python
        history_images = {
            0: [ImageContent(...)],  # Add images to message 0
            3: [ImageContent(...)],  # Add images to message 3
        }
        
        modified = inject_history_images_into_messages(messages, history_images)
        ```
    """
    if not history_images_by_index:
        return False
    
    did_mutate = False
    
    for msg_index, images in history_images_by_index.items():
        if msg_index < 0 or msg_index >= len(messages):
            continue
        
        if not images:
            continue
        
        msg = messages[msg_index]
        
        # Get current content
        content = getattr(msg, "content", None)
        
        # Initialize content list if needed
        if content is None:
            content = []
        elif isinstance(content, str):
            # Convert string to list with text content
            content = [{"type": "text", "text": content}]
        elif not isinstance(content, list):
            content = [content]
        
        # Add images to content
        for image in images:
            if isinstance(image, dict):
                content.append(image)
            else:
                # Convert image object to dict
                content.append({
                    "type": "image",
                    "source": getattr(image, "source", None)
                })
        
        # Update message content
        msg.content = content
        did_mutate = True
    
    return did_mutate


__all__ = [
    "CustomMessageTypes",
    "convert_to_llm",
    "transform_context",
    "build_context_summary",
    "inject_summary_message",
    "validate_gemini_turns",
    "validate_anthropic_turns",
    "limit_history_turns",
    "get_dm_history_limit_from_session_key",
    "sanitize_session_history",
    "inject_history_images_into_messages",
]

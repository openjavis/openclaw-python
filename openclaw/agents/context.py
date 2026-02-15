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

# ---------------------------------------------------------------------------
# Token Estimation Constants (matching TypeScript)
# ---------------------------------------------------------------------------

# More accurate than simple chars // 4
# Based on empirical testing with various LLMs
CHARS_PER_TOKEN_ESTIMATE = 3.5

# Safety margin to avoid underestimating
TOKEN_BUFFER_RATIO = 1.1


def estimate_tokens_from_text(text: str) -> int:
    """
    Estimate tokens from text using character count.
    
    Uses improved estimation: chars / 3.5 * 1.1 (buffer)
    More accurate than the old chars // 4 method.
    
    Args:
        text: Input text
        
    Returns:
        Estimated token count
    """
    if not text:
        return 0
    
    char_count = len(text)
    estimated = char_count / CHARS_PER_TOKEN_ESTIMATE
    return int(estimated * TOKEN_BUFFER_RATIO)


def estimate_tokens_from_messages(messages: list[dict | AgentMessage]) -> int:
    """
    Estimate tokens from a list of messages.
    
    Args:
        messages: List of message dictionaries or AgentMessage objects
        
    Returns:
        Total estimated token count
    """
    if not messages:
        return 0
    
    total_chars = sum(len(str(msg)) for msg in messages)
    return estimate_tokens_from_text(str(messages))


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
        
        elif role == "branchSummary":
            # Branch summary message (converted to user message with prefix)
            summary = getattr(msg, "summary", "")
            prefix = "# Branch Summary (Auto-generated)\n\nThe following is a summary of a parallel branch that was merged:\n\n"
            
            msg_dict = {
                "role": "user",
                "content": prefix + summary
            }
            
            # Preserve timestamp if present
            if hasattr(msg, "timestamp"):
                msg_dict["timestamp"] = msg.timestamp
            
            llm_messages.append(msg_dict)
        
        elif role == "compactionSummary":
            # Compaction summary message (converted to user message with prefix)
            summary = getattr(msg, "summary", "")
            prefix = "# Compaction Summary (Auto-generated)\n\nThe following is a summary of earlier conversation history:\n\n"
            
            msg_dict = {
                "role": "user",
                "content": prefix + summary
            }
            
            # Preserve timestamp if present
            if hasattr(msg, "timestamp"):
                msg_dict["timestamp"] = msg.timestamp
            
            llm_messages.append(msg_dict)
        
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


# Context management classes for backward compatibility
class ContextWindow:
    """
    Context window management for agent sessions.
    
    Tracks token usage and manages context window limits.
    """
    
    def __init__(self, max_tokens: int = 32000, current_tokens: int = 0):
        # Handle various input types gracefully
        try:
            self.max_tokens = int(max_tokens) if max_tokens else 32000
        except (ValueError, TypeError):
            self.max_tokens = 32000  # Fallback to default
            
        try:
            self.current_tokens = int(current_tokens) if current_tokens else 0
        except (ValueError, TypeError):
            self.current_tokens = 0  # Fallback to default
            
        self.total_tokens = self.max_tokens
        self.should_compress = self.current_tokens > int(self.max_tokens * 0.8)  # Compress at 80%
    
    def add_tokens(self, count: int) -> None:
        """Add tokens to current count"""
        self.current_tokens += int(count)
        self.should_compress = self.current_tokens > int(self.max_tokens * 0.8)
    
    def reset(self) -> None:
        """Reset token count"""
        self.current_tokens = 0
        self.should_compress = False
    
    def available(self) -> int:
        """Get available tokens"""
        return max(0, self.max_tokens - self.current_tokens)
    
    def is_full(self) -> bool:
        """Check if context window is full"""
        return self.current_tokens >= self.max_tokens


class ContextManager:
    """
    Context manager for agent runtime.
    
    Manages message history and context windows across sessions.
    """
    
    def __init__(self, default_window_size: int = 32000):
        self.default_window_size = default_window_size
        self.windows: dict[str, ContextWindow] = {}
    
    def get_window(self, session_id: str) -> ContextWindow:
        """Get or create context window for session"""
        if session_id not in self.windows:
            self.windows[session_id] = ContextWindow(self.default_window_size)
        return self.windows[session_id]
    
    def reset_window(self, session_id: str) -> None:
        """Reset context window for session"""
        if session_id in self.windows:
            self.windows[session_id].reset()
    
    def clear_session(self, session_id: str) -> None:
        """Clear session context"""
        if session_id in self.windows:
            del self.windows[session_id]
    
    def check_context(self, token_count: int, max_tokens: int | None = None) -> ContextWindow:
        """
        Check context window status.
        
        Args:
            token_count: Current token count (can be int or list of messages)
            max_tokens: Optional max tokens override
            
        Returns:
            ContextWindow object with status
        """
        # Handle both int and list inputs
        if isinstance(token_count, list):
            # Use improved token estimation
            total_chars = sum(len(str(msg)) for msg in token_count)
            estimated_tokens = estimate_tokens_from_text(str(token_count))
        else:
            estimated_tokens = token_count
        
        max_tok = max_tokens or self.default_window_size
        
        return ContextWindow(max_tokens=max_tok, current_tokens=estimated_tokens)
    
    async def check_context_async(self, token_count: int, max_tokens: int | None = None) -> ContextWindow:
        """Async version of check_context"""
        return self.check_context(token_count, max_tokens)


# ---------------------------------------------------------------------------
# Context window guard (matches TypeScript context-window-guard.ts)
# ---------------------------------------------------------------------------

CONTEXT_WINDOW_HARD_MIN_TOKENS = 16_000
CONTEXT_WINDOW_WARN_BELOW_TOKENS = 32_000


class ContextWindowInfo:
    """Resolved context window info with source tracking."""

    __slots__ = ("tokens", "source")

    def __init__(self, tokens: int, source: str):
        self.tokens = tokens
        self.source = source  # "model" | "modelsConfig" | "agentContextTokens" | "default"

    def __repr__(self) -> str:
        return f"ContextWindowInfo(tokens={self.tokens}, source={self.source!r})"


class ContextWindowGuardResult(ContextWindowInfo):
    """Guard result with warning / blocking flags."""

    __slots__ = ("should_warn", "should_block")

    def __init__(
        self, tokens: int, source: str, should_warn: bool, should_block: bool
    ):
        super().__init__(tokens, source)
        self.should_warn = should_warn
        self.should_block = should_block


def _normalize_positive_int(value: Any) -> int | None:
    """Normalize to positive int, or None."""
    if value is None:
        return None
    try:
        v = int(value)
        return v if v > 0 else None
    except (ValueError, TypeError):
        return None


def resolve_context_window_info(
    cfg: dict | None,
    provider: str,
    model_id: str,
    model_context_window: int | None = None,
    default_tokens: int = 32_000,
) -> ContextWindowInfo:
    """
    Resolve the effective context window for a model.

    Priority: modelsConfig > model metadata > agentContextTokens cap > default.

    Matches TypeScript resolveContextWindowInfo().
    """
    # Check modelsConfig
    from_models_config: int | None = None
    if cfg:
        providers = (cfg.get("models") or {}).get("providers") or {}
        provider_entry = providers.get(provider) or {}
        models = provider_entry.get("models") or []
        if isinstance(models, list):
            for m in models:
                if isinstance(m, dict) and m.get("id") == model_id:
                    from_models_config = _normalize_positive_int(m.get("contextWindow"))
                    break

    from_model = _normalize_positive_int(model_context_window)

    if from_models_config:
        base = ContextWindowInfo(tokens=from_models_config, source="modelsConfig")
    elif from_model:
        base = ContextWindowInfo(tokens=from_model, source="model")
    else:
        base = ContextWindowInfo(tokens=int(default_tokens), source="default")

    # Apply agentContextTokens cap
    cap = None
    if cfg:
        cap = _normalize_positive_int(
            (cfg.get("agents") or {}).get("defaults", {}).get("contextTokens")
        )
    if cap and cap < base.tokens:
        return ContextWindowInfo(tokens=cap, source="agentContextTokens")

    return base


def evaluate_context_window_guard(
    info: ContextWindowInfo,
    warn_below_tokens: int | None = None,
    hard_min_tokens: int | None = None,
) -> ContextWindowGuardResult:
    """
    Evaluate context window against thresholds.

    Matches TypeScript evaluateContextWindowGuard().
    """
    warn_below = max(1, int(warn_below_tokens or CONTEXT_WINDOW_WARN_BELOW_TOKENS))
    hard_min = max(1, int(hard_min_tokens or CONTEXT_WINDOW_HARD_MIN_TOKENS))
    tokens = max(0, int(info.tokens))

    return ContextWindowGuardResult(
        tokens=tokens,
        source=info.source,
        should_warn=tokens > 0 and tokens < warn_below,
        should_block=tokens > 0 and tokens < hard_min,
    )


def check_context_window_status(
    context_tokens: int,
    context_window: int,
) -> dict:
    """
    Evaluate context window state with detailed status.
    
    Returns remaining tokens, usage percentage, and warning/blocking flags.
    
    Args:
        context_tokens: Current token count in context
        context_window: Total context window size
        
    Returns:
        Dictionary with:
        - shouldWarn: bool - < 32k tokens remaining
        - shouldBlock: bool - < 16k tokens remaining
        - remaining: int - tokens remaining
        - usage_percent: float - percentage of window used
        - context_tokens: int - current token count
        - context_window: int - total window size
    """
    remaining = context_window - context_tokens
    usage_percent = (context_tokens / context_window * 100) if context_window > 0 else 0
    
    return {
        "shouldWarn": remaining < CONTEXT_WINDOW_WARN_BELOW_TOKENS,
        "shouldBlock": remaining < CONTEXT_WINDOW_HARD_MIN_TOKENS,
        "remaining": remaining,
        "usage_percent": usage_percent,
        "context_tokens": context_tokens,
        "context_window": context_window,
    }


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
    "ContextManager",
    "ContextWindow",
    "ContextWindowInfo",
    "ContextWindowGuardResult",
    "resolve_context_window_info",
    "evaluate_context_window_guard",
    "check_context_window_status",
    "estimate_tokens_from_text",
    "estimate_tokens_from_messages",
    "CONTEXT_WINDOW_HARD_MIN_TOKENS",
    "CONTEXT_WINDOW_WARN_BELOW_TOKENS",
    "CHARS_PER_TOKEN_ESTIMATE",
    "TOKEN_BUFFER_RATIO",
]

"""
Context management for agent conversations
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ContextWindow:
    """Context window information"""

    total_tokens: int
    used_tokens: int
    remaining_tokens: int
    is_near_limit: bool
    should_compress: bool


class ContextManager:
    """Manages conversation context and token limits"""

    # Default limits for common models
    MODEL_LIMITS = {
        "claude-opus-4": 200000,
        "claude-sonnet-4": 200000,
        "claude-3-5-sonnet": 200000,
        "gpt-4o": 128000,
        "gpt-4-turbo": 128000,
        "gpt-4": 8192,
        "gpt-3.5-turbo": 16385,
        "gemini-3": 128000,
        "gemini-2.5": 128000,
        "gemini-1.5": 128000,  # sign up for gemini models
    }

    def __init__(self, model: str, max_tokens: int | None = None):
        """
        Initialize context manager

        Args:
            model: Model identifier
            max_tokens: Maximum context tokens (default: auto-detect from model)
        """
        self.model = model
        self.max_tokens = max_tokens or self._get_model_limit(model)
        self.buffer_tokens = max(4000, int(self.max_tokens * 0.1))  # 10% buffer

    def _get_model_limit(self, model: str) -> int:
        """Get context window limit for model"""
        model_lower = model.lower()

        for key, limit in self.MODEL_LIMITS.items():
            if key in model_lower:
                return limit

        # Default fallback
        logger.warning(f"Unknown model {model}, using default 128k context")
        return 128000

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text

        Simple estimation: ~4 chars per token for English
        This is a rough approximation
        """
        return len(text) // 4

    def estimate_messages_tokens(self, messages: list[dict]) -> int:
        """Estimate total tokens for message list"""
        total = 0
        for msg in messages:
            # Count content tokens
            if isinstance(msg.get("content"), str):
                total += self.estimate_tokens(msg["content"])
            elif isinstance(msg.get("content"), list):
                for item in msg["content"]:
                    if isinstance(item, dict) and "text" in item:
                        total += self.estimate_tokens(item["text"])

            # Add overhead for message structure (~50 tokens per message)
            total += 50

        return total

    def check_context(self, current_tokens: int) -> ContextWindow:
        """
        Check context window status

        Args:
            current_tokens: Current token usage

        Returns:
            ContextWindow with status information
        """
        remaining = self.max_tokens - current_tokens
        used_percent = current_tokens / self.max_tokens

        # Near limit if using > 80% of available tokens
        is_near_limit = used_percent > 0.8

        # Should compress if using > 70% of available tokens
        should_compress = used_percent > 0.7

        return ContextWindow(
            total_tokens=self.max_tokens,
            used_tokens=current_tokens,
            remaining_tokens=remaining,
            is_near_limit=is_near_limit,
            should_compress=should_compress,
        )

    def can_fit_message(self, current_tokens: int, new_message_tokens: int) -> bool:
        """Check if new message can fit in context window"""
        total = current_tokens + new_message_tokens + self.buffer_tokens
        return total <= self.max_tokens

    def prune_messages(self, messages: list[dict], keep_recent: int = 10) -> list[dict]:
        """
        Prune old messages to reduce context size

        Strategy:
        1. Always keep system prompt (first message)
        2. Keep last N messages (recent conversation)
        3. Remove middle messages

        Args:
            messages: List of messages
            keep_recent: Number of recent messages to keep

        Returns:
            Pruned message list
        """
        if len(messages) <= keep_recent + 1:  # +1 for system prompt
            return messages

        # Keep system prompt if exists
        result = []
        if messages and messages[0].get("role") == "system":
            result.append(messages[0])
            messages = messages[1:]

        # Keep recent messages
        result.extend(messages[-keep_recent:])

        pruned_count = len(messages) - keep_recent
        logger.info(f"Pruned {pruned_count} messages from context")

        return result

    def create_summary_message(self, messages: list[dict], start_idx: int, end_idx: int) -> dict:
        """
        Create a summary message for a range of messages

        This is a simple implementation that concatenates messages.
        In a production system, you might use an LLM to create an actual summary.
        """
        summary_parts = []
        for msg in messages[start_idx:end_idx]:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if isinstance(content, str):
                summary_parts.append(f"[{role}]: {content[:100]}...")

        summary_text = "\n".join(summary_parts)

        return {
            "role": "system",
            "content": f"[Previous conversation summary covering {end_idx - start_idx} messages]:\n{summary_text}",
        }

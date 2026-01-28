"""
Context compaction strategies
"""

import logging
from enum import Enum
from typing import Any

from .analyzer import TokenAnalyzer

logger = logging.getLogger(__name__)


class CompactionStrategy(str, Enum):
    """Strategy for context compaction"""

    KEEP_RECENT = "recent"  # Keep last N messages
    KEEP_IMPORTANT = "important"  # Keep system + high importance
    SLIDING_WINDOW = "sliding"  # Keep first + last messages
    SUMMARIZE = "summarize"  # Summarize old messages (future)


class CompactionManager:
    """
    Manage context window compaction

    Features:
    - Multiple compaction strategies
    - Preserve important messages
    - Token-aware pruning
    """

    def __init__(
        self,
        analyzer: TokenAnalyzer,
        strategy: CompactionStrategy = CompactionStrategy.KEEP_IMPORTANT,
    ):
        """
        Initialize compaction manager

        Args:
            analyzer: Token analyzer
            strategy: Compaction strategy
        """
        self.analyzer = analyzer
        self.strategy = strategy

    def compact(
        self, messages: list[dict[str, Any]], target_tokens: int, preserve_system: bool = True
    ) -> list[dict[str, Any]]:
        """
        Compact messages to fit token budget

        Args:
            messages: List of messages
            target_tokens: Target token count
            preserve_system: Always keep system messages

        Returns:
            Compacted message list
        """
        current_tokens = self.analyzer.estimate_messages_tokens(messages)

        if current_tokens <= target_tokens:
            logger.debug(f"No compaction needed: {current_tokens}/{target_tokens} tokens")
            return messages

        logger.info(
            f"Compacting from {current_tokens} to {target_tokens} tokens using {self.strategy.value}"
        )

        if self.strategy == CompactionStrategy.KEEP_RECENT:
            return self._compact_keep_recent(messages, target_tokens, preserve_system)

        elif self.strategy == CompactionStrategy.KEEP_IMPORTANT:
            return self._compact_keep_important(messages, target_tokens, preserve_system)

        elif self.strategy == CompactionStrategy.SLIDING_WINDOW:
            return self._compact_sliding_window(messages, target_tokens, preserve_system)

        else:
            # Default to keep recent
            return self._compact_keep_recent(messages, target_tokens, preserve_system)

    def _compact_keep_recent(
        self, messages: list[dict[str, Any]], target_tokens: int, preserve_system: bool
    ) -> list[dict[str, Any]]:
        """Keep most recent messages that fit"""
        # Separate system messages
        system_msgs = [m for m in messages if m.get("role") == "system"]
        other_msgs = [m for m in messages if m.get("role") != "system"]

        # Start with system messages if preserving
        result = system_msgs.copy() if preserve_system else []
        current_tokens = self.analyzer.estimate_messages_tokens(result)

        # Add messages from end until we hit token limit
        for msg in reversed(other_msgs):
            msg_tokens = self.analyzer.estimate_messages_tokens([msg])
            if current_tokens + msg_tokens <= target_tokens:
                result.insert(len(system_msgs) if preserve_system else 0, msg)
                current_tokens += msg_tokens
            else:
                break

        logger.debug(f"Kept {len(result)}/{len(messages)} messages ({current_tokens} tokens)")
        return result

    def _compact_keep_important(
        self, messages: list[dict[str, Any]], target_tokens: int, preserve_system: bool
    ) -> list[dict[str, Any]]:
        """Keep important messages based on score"""
        # Calculate importance for each message
        scored = [
            (
                msg,
                self.analyzer.get_message_importance(msg),
                self.analyzer.estimate_messages_tokens([msg]),
            )
            for msg in messages
        ]

        # Always include system messages if preserving
        result = []
        current_tokens = 0

        if preserve_system:
            system_msgs = [(m, s, t) for m, s, t in scored if m.get("role") == "system"]
            result.extend([m for m, _, _ in system_msgs])
            current_tokens = sum(t for _, _, t in system_msgs)

        # Sort remaining by importance (descending)
        non_system = [(m, s, t) for m, s, t in scored if m.get("role") != "system"]
        non_system.sort(key=lambda x: x[1], reverse=True)

        # Add messages by importance until token limit
        for msg, importance, tokens in non_system:
            if current_tokens + tokens <= target_tokens:
                result.append(msg)
                current_tokens += tokens

        # Restore original order
        result_set = set(id(m) for m in result)
        result = [m for m in messages if id(m) in result_set]

        logger.debug(
            f"Kept {len(result)}/{len(messages)} important messages ({current_tokens} tokens)"
        )
        return result

    def _compact_sliding_window(
        self, messages: list[dict[str, Any]], target_tokens: int, preserve_system: bool
    ) -> list[dict[str, Any]]:
        """Keep first N and last M messages"""
        # Separate system messages
        system_msgs = [m for m in messages if m.get("role") == "system"]
        other_msgs = [m for m in messages if m.get("role") != "system"]

        if not other_msgs:
            return system_msgs

        result = system_msgs.copy() if preserve_system else []
        current_tokens = self.analyzer.estimate_messages_tokens(result)
        target_tokens - current_tokens

        # Calculate how many messages we can fit
        # Try to balance between first and last
        first_count = 0
        last_count = 0

        # Add messages from start
        for msg in other_msgs:
            msg_tokens = self.analyzer.estimate_messages_tokens([msg])
            if current_tokens + msg_tokens <= target_tokens:
                result.append(msg)
                current_tokens += msg_tokens
                first_count += 1
            else:
                break

        # Add messages from end
        for msg in reversed(other_msgs[first_count:]):
            msg_tokens = self.analyzer.estimate_messages_tokens([msg])
            if current_tokens + msg_tokens <= target_tokens:
                result.append(msg)
                current_tokens += msg_tokens
                last_count += 1
            else:
                break

        logger.debug(
            f"Kept {len(result)}/{len(messages)} messages "
            f"(first {first_count}, last {last_count}, {current_tokens} tokens)"
        )
        return result

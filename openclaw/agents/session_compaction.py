"""
Session compaction - automatic conversation history summarization

Inspired by pi-mono's compaction mechanism to manage long conversations
and keep context within model limits.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from openclaw.agents.types import AgentMessage

logger = logging.getLogger(__name__)


class CompactionSummary(BaseModel):
    """
    Summary of compacted conversation history.
    
    Matches pi-mono's CompactionSummaryMessage
    """
    role: str = "custom"
    custom_type: str = Field(default="compactionSummary", alias="customType")
    summary: str  # LLM-generated summary of compacted messages
    compacted_count: int = Field(alias="compactedCount")  # Number of messages compacted
    compacted_range: tuple[int, int] = Field(alias="compactedRange")  # (start_idx, end_idx)
    timestamp: int


class SessionCompactor:
    """
    Automatically compacts long conversation histories using LLM summarization.
    
    Features:
    - Token-based compaction threshold
    - Smart message selection (preserve recent context)
    - LLM-powered summarization
    - Configurable compaction strategies
    """
    
    def __init__(
        self,
        max_tokens: int = 4000,
        compaction_threshold: float = 0.8,
        min_messages_to_compact: int = 10,
        preserve_recent_count: int = 5,
    ):
        """
        Initialize SessionCompactor.
        
        Args:
            max_tokens: Maximum tokens before triggering compaction
            compaction_threshold: Compact when usage exceeds this fraction (0.8 = 80%)
            min_messages_to_compact: Minimum messages needed before compaction
            preserve_recent_count: Number of recent messages to always preserve
        """
        self.max_tokens = max_tokens
        self.compaction_threshold = compaction_threshold
        self.min_messages_to_compact = min_messages_to_compact
        self.preserve_recent_count = preserve_recent_count
    
    async def should_compact(self, messages: list[AgentMessage]) -> bool:
        """
        Determine if conversation should be compacted.
        
        Rules:
        1. Must have minimum number of messages
        2. Estimated token count must exceed threshold
        3. Must have enough old messages to compact (preserve recent)
        
        Args:
            messages: Current message list
        
        Returns:
            True if compaction is recommended
        """
        if len(messages) < self.min_messages_to_compact:
            return False
        
        # Estimate token count (rough: 4 chars per token)
        estimated_tokens = sum(
            len(str(msg.content)) // 4
            for msg in messages
        )
        
        threshold_tokens = self.max_tokens * self.compaction_threshold
        
        if estimated_tokens > threshold_tokens:
            logger.info(
                f"Compaction recommended: {estimated_tokens} tokens (threshold: {threshold_tokens})"
            )
            return True
        
        return False
    
    async def compact(
        self,
        messages: list[AgentMessage],
        use_llm: bool = True,
    ) -> list[AgentMessage]:
        """
        Compact conversation history by summarizing old messages.
        
        Strategy:
        1. Separate system messages, old messages, and recent messages
        2. Summarize old messages (using LLM if enabled)
        3. Replace old messages with summary
        4. Reconstruct: system + summary + recent
        
        Args:
            messages: Current message list
            use_llm: Whether to use LLM for summarization (default: True)
        
        Returns:
            Compacted message list
        """
        if len(messages) <= self.preserve_recent_count + 1:
            logger.warning("Not enough messages to compact")
            return messages
        
        # Separate system messages
        system_messages = [msg for msg in messages if msg.role == "system"]
        conversation_messages = [msg for msg in messages if msg.role != "system"]
        
        # Calculate split point
        preserve_count = min(self.preserve_recent_count, len(conversation_messages) - 1)
        compact_count = len(conversation_messages) - preserve_count
        
        if compact_count < 3:  # Need at least 3 messages to make compaction worthwhile
            logger.info("Too few messages to compact")
            return messages
        
        # Split messages
        messages_to_compact = conversation_messages[:compact_count]
        recent_messages = conversation_messages[compact_count:]
        
        logger.info(
            f"Compacting {compact_count} messages, preserving {preserve_count} recent"
        )
        
        # Generate summary
        if use_llm:
            summary_text = await self._llm_summarize(messages_to_compact)
        else:
            summary_text = self._simple_summarize(messages_to_compact)
        
        # Create compaction summary message
        from datetime import datetime
        summary_msg = CompactionSummary(
            summary=summary_text,
            compacted_count=compact_count,
            compacted_range=(0, compact_count - 1),
            timestamp=int(datetime.now().timestamp() * 1000),
        )
        
        # Reconstruct message list
        # Note: summary_msg is a Pydantic model, need to convert to proper message type
        from openclaw.agents.types import CustomMessage
        
        summary_as_message = CustomMessage(
            customType="compactionSummary",
            content=f"[Conversation Summary: {compact_count} messages]\n\n{summary_text}",
            display=False,  # Don't show in UI
            details=summary_msg.model_dump(),
        )
        
        compacted_messages = system_messages + [summary_as_message] + recent_messages
        
        logger.info(
            f"Compaction complete: {len(messages)} → {len(compacted_messages)} messages"
        )
        
        return compacted_messages
    
    async def _llm_summarize(self, messages: list[AgentMessage]) -> str:
        """
        Use LLM to generate a natural language summary.
        
        TODO: Implement actual LLM call
        For now, falls back to simple summarization.
        """
        # Placeholder for LLM summarization
        # In production, this would call the LLM provider with a summarization prompt
        logger.warning("LLM summarization not yet implemented, using simple summary")
        return self._simple_summarize(messages)
    
    def _simple_summarize(self, messages: list[AgentMessage]) -> str:
        """
        Generate a simple summary without LLM.
        
        Lists key events and topics discussed.
        """
        summary_parts = []
        
        # Count message types
        user_count = sum(1 for msg in messages if msg.role == "user")
        assistant_count = sum(1 for msg in messages if msg.role == "assistant")
        tool_count = sum(
            1 for msg in messages
            if msg.role in ["tool", "toolResult"]
        )
        
        summary_parts.append(
            f"Summary of {len(messages)} messages: "
            f"{user_count} user, {assistant_count} assistant, {tool_count} tool calls."
        )
        
        # Extract user topics (first 50 chars of user messages)
        user_topics = []
        for msg in messages:
            if msg.role == "user":
                content_str = str(msg.content)[:50]
                user_topics.append(content_str)
        
        if user_topics:
            topics_preview = " | ".join(user_topics[:3])
            summary_parts.append(f"\nTopics: {topics_preview}")
            if len(user_topics) > 3:
                summary_parts.append(f" (+ {len(user_topics) - 3} more)")
        
        return "".join(summary_parts)
    
    def get_compaction_stats(self, messages: list[AgentMessage]) -> dict:
        """
        Get statistics about current conversation state.
        
        Useful for monitoring and debugging.
        """
        estimated_tokens = sum(
            len(str(msg.content)) // 4
            for msg in messages
        )
        
        usage_ratio = estimated_tokens / self.max_tokens if self.max_tokens > 0 else 0
        
        return {
            "message_count": len(messages),
            "estimated_tokens": estimated_tokens,
            "max_tokens": self.max_tokens,
            "usage_ratio": usage_ratio,
            "should_compact": usage_ratio > self.compaction_threshold,
            "compaction_threshold": self.compaction_threshold,
        }


# Singleton compactor instance
_default_compactor: SessionCompactor | None = None


def get_default_compactor() -> SessionCompactor:
    """Get the default session compactor instance."""
    global _default_compactor
    if _default_compactor is None:
        _default_compactor = SessionCompactor()
    return _default_compactor

"""
LLM-driven message summarization for context compaction
"""

import logging
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class SummarizationStrategy(str, Enum):
    """Strategy for message summarization"""

    NONE = "none"  # No summarization
    COMPRESS = "compress"  # Compress to key points
    ABSTRACT = "abstract"  # High-level abstract
    DIALOGUE = "dialogue"  # Preserve dialogue flow


class MessageSummarizer:
    """
    Summarize conversation messages using LLM

    Features:
    - Multiple summarization strategies
    - Preserve important context
    - Token-aware summarization
    - Batch and incremental summarization

    Example:
        summarizer = MessageSummarizer(llm_provider)
        summary = await summarizer.summarize(messages, strategy="compress")
    """

    SYSTEM_PROMPTS = {
        SummarizationStrategy.COMPRESS: """You are a conversation summarizer. Compress the following conversation into key points while preserving all important information, decisions, and context. Be concise but complete.

Format your summary as:
- Key Point 1
- Key Point 2
- ...

Keep the summary under 500 tokens.""",
        SummarizationStrategy.ABSTRACT: """You are a conversation summarizer. Create a high-level abstract of the following conversation, focusing on the main topic, goals, and outcomes.

Format your summary as a brief paragraph (2-3 sentences) capturing the essence of the conversation.

Keep the summary under 200 tokens.""",
        SummarizationStrategy.DIALOGUE: """You are a conversation summarizer. Preserve the dialogue flow while condensing the conversation. Keep speaker attributions and maintain the conversational structure.

Format your summary as:
User: [condensed message]
Assistant: [condensed response]
...

Keep the summary under 800 tokens.""",
    }

    def __init__(self, llm_provider: Any = None):
        """
        Initialize summarizer

        Args:
            llm_provider: LLM provider instance (optional, uses default if not provided)
        """
        self.llm_provider = llm_provider

    async def summarize(
        self,
        messages: list[dict[str, Any]],
        strategy: SummarizationStrategy = SummarizationStrategy.COMPRESS,
        max_tokens: int = 1000,
        preserve_system: bool = True,
    ) -> str:
        """
        Summarize a list of messages

        Args:
            messages: List of message dicts with role/content
            strategy: Summarization strategy
            max_tokens: Maximum tokens for summary
            preserve_system: Keep system messages separate

        Returns:
            Summary string
        """
        if not messages:
            return ""

        if strategy == SummarizationStrategy.NONE:
            return self._format_messages(messages)

        # Separate system messages if preserving
        system_messages = []
        other_messages = messages

        if preserve_system:
            system_messages = [m for m in messages if m.get("role") == "system"]
            other_messages = [m for m in messages if m.get("role") != "system"]

        if not other_messages:
            return self._format_messages(system_messages)

        # Format conversation for summarization
        conversation = self._format_messages(other_messages)

        # Generate summary
        summary = await self._generate_summary(conversation, strategy, max_tokens)

        # Combine system messages with summary
        if system_messages:
            system_text = self._format_messages(system_messages)
            return f"{system_text}\n\n[SUMMARY OF CONVERSATION]\n{summary}"

        return f"[SUMMARY]\n{summary}"

    async def summarize_batch(
        self,
        message_batches: list[list[dict[str, Any]]],
        strategy: SummarizationStrategy = SummarizationStrategy.COMPRESS,
        max_tokens: int = 1000,
    ) -> list[str]:
        """
        Summarize multiple batches of messages

        Args:
            message_batches: List of message lists
            strategy: Summarization strategy
            max_tokens: Maximum tokens per summary

        Returns:
            List of summary strings
        """
        summaries = []
        for batch in message_batches:
            summary = await self.summarize(batch, strategy, max_tokens)
            summaries.append(summary)
        return summaries

    async def incremental_summarize(
        self,
        previous_summary: str,
        new_messages: list[dict[str, Any]],
        strategy: SummarizationStrategy = SummarizationStrategy.COMPRESS,
        max_tokens: int = 1000,
    ) -> str:
        """
        Incrementally update summary with new messages

        Args:
            previous_summary: Previous conversation summary
            new_messages: New messages to incorporate
            strategy: Summarization strategy
            max_tokens: Maximum tokens for updated summary

        Returns:
            Updated summary string
        """
        if not new_messages:
            return previous_summary

        if not previous_summary:
            return await self.summarize(new_messages, strategy, max_tokens)

        # Combine previous summary with new messages
        combined = f"Previous Summary:\n{previous_summary}\n\nNew Messages:\n{self._format_messages(new_messages)}"

        # Generate updated summary
        system_prompt = f"""{self.SYSTEM_PROMPTS.get(strategy, self.SYSTEM_PROMPTS[SummarizationStrategy.COMPRESS])}

Update the previous summary by incorporating the new messages. Maintain continuity while adding new information."""

        return await self._generate_summary(
            combined, strategy, max_tokens, custom_prompt=system_prompt
        )

    def _format_messages(self, messages: list[dict[str, Any]]) -> str:
        """Format messages as text"""
        formatted = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            # Handle structured content
            if isinstance(content, list):
                content = "\n".join(
                    item.get("text", str(item)) for item in content if isinstance(item, dict)
                )

            formatted.append(f"{role.title()}: {content}")

        return "\n\n".join(formatted)

    async def _generate_summary(
        self,
        text: str,
        strategy: SummarizationStrategy,
        max_tokens: int,
        custom_prompt: str | None = None,
    ) -> str:
        """
        Generate summary using LLM

        Args:
            text: Text to summarize
            strategy: Summarization strategy
            max_tokens: Maximum tokens
            custom_prompt: Custom system prompt (optional)

        Returns:
            Summary string
        """
        if not self.llm_provider:
            # Fallback to simple truncation if no LLM
            logger.warning("No LLM provider configured, using simple truncation")
            return self._simple_truncate(text, max_tokens)

        try:
            # Get system prompt
            system_prompt = custom_prompt or self.SYSTEM_PROMPTS.get(
                strategy, self.SYSTEM_PROMPTS[SummarizationStrategy.COMPRESS]
            )

            # Prepare messages for LLM
            from ..providers.base import LLMMessage

            messages = [
                LLMMessage(role="system", content=system_prompt),
                LLMMessage(role="user", content=text),
            ]

            # Generate summary
            summary_parts = []
            async for response in self.llm_provider.stream(
                messages=messages, max_tokens=max_tokens
            ):
                if response.type == "text_delta":
                    summary_parts.append(response.content)
                elif response.type == "done":
                    break
                elif response.type == "error":
                    logger.error(f"Summarization error: {response.content}")
                    return self._simple_truncate(text, max_tokens)

            return "".join(summary_parts).strip()

        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return self._simple_truncate(text, max_tokens)

    def _simple_truncate(self, text: str, max_tokens: int) -> str:
        """Simple truncation fallback"""
        # Rough estimate: 4 chars per token
        max_chars = max_tokens * 4
        if len(text) <= max_chars:
            return text

        truncated = text[:max_chars]
        # Try to end at a sentence
        last_period = truncated.rfind(".")
        if last_period > max_chars * 0.8:
            truncated = truncated[: last_period + 1]

        return truncated + "\n[...truncated]"

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text"""
        # Rough estimate: 4 characters per token
        return len(text) // 4

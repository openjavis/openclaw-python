"""
Tests for message summarization
"""

import pytest

from openclaw.agents.summarization import MessageSummarizer, SummarizationStrategy


class TestSummarizationStrategy:
    """Test SummarizationStrategy enum"""

    def test_strategy_values(self):
        """Test strategy enum values"""
        assert SummarizationStrategy.NONE == "none"
        assert SummarizationStrategy.COMPRESS == "compress"
        assert SummarizationStrategy.ABSTRACT == "abstract"
        assert SummarizationStrategy.DIALOGUE == "dialogue"


class TestMessageSummarizer:
    """Test MessageSummarizer class"""

    def test_init(self):
        """Test initializing summarizer"""
        summarizer = MessageSummarizer()
        assert summarizer.llm_provider is None

    def test_init_with_provider(self):
        """Test initializing with LLM provider"""
        mock_provider = object()
        summarizer = MessageSummarizer(mock_provider)
        assert summarizer.llm_provider == mock_provider

    def test_format_messages(self):
        """Test message formatting"""
        summarizer = MessageSummarizer()

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        formatted = summarizer._format_messages(messages)

        assert "User: Hello" in formatted
        assert "Assistant: Hi there!" in formatted

    def test_format_messages_structured_content(self):
        """Test formatting messages with structured content"""
        summarizer = MessageSummarizer()

        messages = [{"role": "user", "content": [{"text": "Part 1"}, {"text": "Part 2"}]}]

        formatted = summarizer._format_messages(messages)

        assert "Part 1" in formatted
        assert "Part 2" in formatted

    @pytest.mark.asyncio
    async def test_summarize_empty(self):
        """Test summarizing empty messages"""
        summarizer = MessageSummarizer()

        summary = await summarizer.summarize([])

        assert summary == ""

    @pytest.mark.asyncio
    async def test_summarize_none_strategy(self):
        """Test summarize with NONE strategy"""
        summarizer = MessageSummarizer()

        messages = [{"role": "user", "content": "Test message"}]

        summary = await summarizer.summarize(messages, strategy=SummarizationStrategy.NONE)

        assert "Test message" in summary

    @pytest.mark.asyncio
    async def test_summarize_preserve_system(self):
        """Test preserving system messages"""
        summarizer = MessageSummarizer()

        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
        ]

        summary = await summarizer.summarize(
            messages, strategy=SummarizationStrategy.NONE, preserve_system=True
        )

        assert "System: You are helpful" in summary
        assert "User: Hello" in summary

    def test_simple_truncate(self):
        """Test simple truncation fallback"""
        summarizer = MessageSummarizer()

        long_text = "A" * 10000
        truncated = summarizer._simple_truncate(long_text, max_tokens=100)

        assert len(truncated) < len(long_text)
        assert "[...truncated]" in truncated

    def test_simple_truncate_short_text(self):
        """Test truncation on short text"""
        summarizer = MessageSummarizer()

        short_text = "Short text"
        result = summarizer._simple_truncate(short_text, max_tokens=100)

        assert result == short_text

    def test_estimate_tokens(self):
        """Test token estimation"""
        summarizer = MessageSummarizer()

        text = "This is a test message"
        tokens = summarizer.estimate_tokens(text)

        assert tokens > 0
        assert tokens < len(text)

    @pytest.mark.asyncio
    async def test_summarize_batch(self):
        """Test batch summarization"""
        summarizer = MessageSummarizer()

        batches = [
            [{"role": "user", "content": "Batch 1"}],
            [{"role": "user", "content": "Batch 2"}],
        ]

        summaries = await summarizer.summarize_batch(batches, strategy=SummarizationStrategy.NONE)

        assert len(summaries) == 2
        assert "Batch 1" in summaries[0]
        assert "Batch 2" in summaries[1]

    @pytest.mark.asyncio
    async def test_incremental_summarize_no_previous(self):
        """Test incremental summarization with no previous summary"""
        summarizer = MessageSummarizer()

        messages = [{"role": "user", "content": "New message"}]

        summary = await summarizer.incremental_summarize(
            "", messages, strategy=SummarizationStrategy.NONE
        )

        assert "New message" in summary

    @pytest.mark.asyncio
    async def test_incremental_summarize_no_new_messages(self):
        """Test incremental summarization with no new messages"""
        summarizer = MessageSummarizer()

        previous = "Previous summary"

        summary = await summarizer.incremental_summarize(
            previous, [], strategy=SummarizationStrategy.NONE
        )

        assert summary == previous


class TestSummarizationIntegration:
    """Integration tests for summarization"""

    @pytest.mark.asyncio
    async def test_compress_strategy_format(self):
        """Test compress strategy output format"""
        summarizer = MessageSummarizer()

        messages = [
            {"role": "user", "content": "What is Python?"},
            {"role": "assistant", "content": "Python is a programming language"},
        ]

        # Without LLM, should fall back to truncation
        summary = await summarizer.summarize(messages, strategy=SummarizationStrategy.COMPRESS)

        # Should contain formatted messages or summary marker
        assert len(summary) > 0

    @pytest.mark.asyncio
    async def test_dialogue_preservation(self):
        """Test dialogue strategy preserves structure"""
        summarizer = MessageSummarizer()

        messages = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
        ]

        summary = await summarizer.summarize(messages, strategy=SummarizationStrategy.DIALOGUE)

        # Should preserve order (with fallback)
        assert len(summary) > 0

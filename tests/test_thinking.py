"""
Tests for thinking mode and extraction
"""

import pytest

from openclaw.agents.thinking import ThinkingExtractor, ThinkingMode


class TestThinkingMode:
    """Test ThinkingMode enum"""

    def test_mode_values(self):
        """Test mode enum values"""
        assert ThinkingMode.OFF == "off"
        assert ThinkingMode.ON == "on"
        assert ThinkingMode.STREAM == "stream"


class TestThinkingExtractor:
    """Test ThinkingExtractor class"""

    def test_extract_no_thinking(self):
        """Test extraction with no thinking tags"""
        extractor = ThinkingExtractor()
        text = "This is regular text without thinking"

        result = extractor.extract(text)

        assert result.thinking == ""
        assert result.content == text
        assert not result.has_thinking

    def test_extract_thinking_tags(self):
        """Test extraction with thinking tags"""
        extractor = ThinkingExtractor()
        text = "Let me think. <thinking>This is my thought process</thinking> The answer is 42."

        result = extractor.extract(text)

        assert "thought process" in result.thinking
        assert result.content == "Let me think.  The answer is 42."
        assert result.has_thinking

    def test_extract_multiple_thinking_blocks(self):
        """Test extraction with multiple thinking blocks"""
        extractor = ThinkingExtractor()
        text = "<thinking>First thought</thinking> Some text <thinking>Second thought</thinking> More text"

        result = extractor.extract(text)

        assert "First thought" in result.thinking
        assert "Second thought" in result.thinking
        assert result.content == "Some text  More text"
        assert result.has_thinking

    def test_extract_thought_tags(self):
        """Test extraction with <thought> tags"""
        extractor = ThinkingExtractor()
        text = "Text <thought>My reasoning</thought> More text"

        result = extractor.extract(text)

        assert "reasoning" in result.thinking
        assert result.has_thinking

    def test_extract_antthinking_tags(self):
        """Test extraction with <antthinking> tags"""
        extractor = ThinkingExtractor()
        text = "<antthinking>Analysis here</antthinking>Result"

        result = extractor.extract(text)

        assert "Analysis" in result.thinking
        assert "Result" in result.content
        assert result.has_thinking

    def test_extract_streaming(self):
        """Test streaming extraction"""
        extractor = ThinkingExtractor()
        state = {}

        # First delta: opening tag
        think_delta1, content_delta1 = extractor.extract_streaming("Hello <thinking>Let me", state)
        assert content_delta1 == "Hello "

        # Second delta: thinking content
        think_delta2, content_delta2 = extractor.extract_streaming(" analyze this", state)

        # Third delta: closing tag and more content
        think_delta3, content_delta3 = extractor.extract_streaming("</thinking> Answer", state)
        assert "Answer" in content_delta3

    def test_has_thinking_tags(self):
        """Test thinking tag detection"""
        extractor = ThinkingExtractor()

        assert extractor._has_thinking_tags("<thinking>test</thinking>")
        assert extractor._has_thinking_tags("<thought>test</thought>")
        assert extractor._has_thinking_tags("<antthinking>test</antthinking>")
        assert not extractor._has_thinking_tags("regular text")

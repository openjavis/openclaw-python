"""
Tests for context compaction
"""

import pytest

from openclaw.agents.compaction import CompactionManager, CompactionStrategy, TokenAnalyzer


class TestTokenAnalyzer:
    """Test TokenAnalyzer class"""

    def test_analyzer_creation(self):
        """Test creating analyzer"""
        analyzer = TokenAnalyzer("claude-opus")
        assert analyzer.model_name == "claude-opus"

    def test_estimate_tokens_empty(self):
        """Test empty text estimation"""
        analyzer = TokenAnalyzer()
        assert analyzer.estimate_tokens("") == 0
        assert analyzer.estimate_tokens(None) == 0

    def test_estimate_tokens_text(self):
        """Test text estimation"""
        analyzer = TokenAnalyzer()
        text = "Hello world! This is a test message."

        tokens = analyzer.estimate_tokens(text)

        # Should be roughly len(text) * 0.25
        assert tokens > 0
        assert tokens < len(text)

    def test_estimate_messages_tokens(self):
        """Test estimating tokens for messages"""
        analyzer = TokenAnalyzer()
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        tokens = analyzer.estimate_messages_tokens(messages)

        # Should include message overhead + content
        assert tokens > 10

    def test_get_message_importance(self):
        """Test message importance scoring"""
        analyzer = TokenAnalyzer()

        # System message should be most important
        system_score = analyzer.get_message_importance({"role": "system", "content": "test"})
        assert system_score == 1.0

        # Assistant with tool calls should be high
        assistant_score = analyzer.get_message_importance(
            {"role": "assistant", "content": "test", "tool_calls": [{"name": "bash"}]}
        )
        assert assistant_score > 0.8

        # User messages moderate
        user_score = analyzer.get_message_importance({"role": "user", "content": "test"})
        assert 0.5 < user_score < 0.8

        # Tool results less important
        tool_score = analyzer.get_message_importance({"role": "tool", "content": "result"})
        assert tool_score < 0.5


class TestCompactionStrategy:
    """Test CompactionStrategy enum"""

    def test_strategy_values(self):
        """Test strategy enum values"""
        assert CompactionStrategy.KEEP_RECENT == "recent"
        assert CompactionStrategy.KEEP_IMPORTANT == "important"
        assert CompactionStrategy.SLIDING_WINDOW == "sliding"


class TestCompactionManager:
    """Test CompactionManager class"""

    @pytest.fixture
    def messages(self):
        """Sample messages for testing"""
        return [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "Hello" * 100},
            {"role": "assistant", "content": "Hi!" * 100},
            {"role": "user", "content": "How are you?" * 100},
            {"role": "assistant", "content": "I'm good" * 100, "tool_calls": [{"name": "test"}]},
            {"role": "tool", "content": "Tool result" * 100},
            {"role": "user", "content": "Thanks" * 100},
        ]

    def test_no_compaction_needed(self, messages):
        """Test when compaction is not needed"""
        analyzer = TokenAnalyzer()
        manager = CompactionManager(analyzer, CompactionStrategy.KEEP_RECENT)

        # High target tokens
        result = manager.compact(messages[:2], target_tokens=10000)

        assert len(result) == 2  # No change

    def test_compact_keep_recent(self, messages):
        """Test keep recent strategy"""
        analyzer = TokenAnalyzer()
        manager = CompactionManager(analyzer, CompactionStrategy.KEEP_RECENT)

        result = manager.compact(messages, target_tokens=100)

        # Should keep system + some recent messages
        assert len(result) < len(messages)
        assert result[0]["role"] == "system"  # System preserved

    def test_compact_keep_important(self, messages):
        """Test keep important strategy"""
        analyzer = TokenAnalyzer()
        manager = CompactionManager(analyzer, CompactionStrategy.KEEP_IMPORTANT)

        result = manager.compact(messages, target_tokens=150)

        # Should keep system and important messages
        assert len(result) < len(messages)
        # System message should be first
        system_msgs = [m for m in result if m["role"] == "system"]
        assert len(system_msgs) > 0

    def test_compact_sliding_window(self, messages):
        """Test sliding window strategy"""
        analyzer = TokenAnalyzer()
        manager = CompactionManager(analyzer, CompactionStrategy.SLIDING_WINDOW)

        result = manager.compact(messages, target_tokens=200)

        # Should keep some from start and end
        assert len(result) < len(messages)
        assert result[0]["role"] == "system"

    def test_preserve_system_messages(self, messages):
        """Test system message preservation"""
        analyzer = TokenAnalyzer()
        manager = CompactionManager(analyzer, CompactionStrategy.KEEP_RECENT)

        result = manager.compact(messages, target_tokens=50, preserve_system=True)

        # System message should always be present
        assert any(m["role"] == "system" for m in result)

"""
Unit tests for enhanced context functionality

Tests the new context features including message validation, history limiting,
and image injection.
"""

import pytest
from unittest.mock import MagicMock
from openclaw.agents.context import (
    validate_gemini_turns,
    validate_anthropic_turns,
    limit_history_turns,
    get_dm_history_limit_from_session_key,
    sanitize_session_history,
    inject_history_images_into_messages,
)


@pytest.fixture
def mock_message():
    """Create a mock message object."""
    def _create(role, content, **kwargs):
        msg = MagicMock()
        msg.role = role
        msg.content = content
        for key, value in kwargs.items():
            setattr(msg, key, value)
        return msg
    return _create


class TestValidateGeminiTurns:
    """Test Gemini message validation."""
    
    def test_merge_consecutive_assistant_messages(self, mock_message):
        """Test that consecutive assistant messages are merged."""
        messages = [
            mock_message("user", "Hello"),
            mock_message("assistant", "Hi"),
            mock_message("assistant", "How are you?"),
        ]
        
        result = validate_gemini_turns(messages)
        
        assert len(result) == 2  # user + merged assistant
        assert result[0].role == "user"
        assert result[1].role == "assistant"
    
    def test_preserve_user_assistant_alternation(self, mock_message):
        """Test that proper user/assistant alternation is preserved."""
        messages = [
            mock_message("user", "Hello"),
            mock_message("assistant", "Hi"),
            mock_message("user", "How are you?"),
            mock_message("assistant", "I'm good"),
        ]
        
        result = validate_gemini_turns(messages)
        
        assert len(result) == 4  # All messages preserved
    
    def test_empty_messages_list(self):
        """Test handling empty messages list."""
        result = validate_gemini_turns([])
        assert result == []
    
    def test_system_messages_preserved(self, mock_message):
        """Test that system messages are preserved."""
        messages = [
            mock_message("system", "System prompt"),
            mock_message("user", "Hello"),
            mock_message("assistant", "Hi"),
        ]
        
        result = validate_gemini_turns(messages)
        
        assert len(result) == 3
        assert result[0].role == "system"


class TestValidateAnthropicTurns:
    """Test Anthropic message validation."""
    
    def test_merge_consecutive_user_messages(self, mock_message):
        """Test that consecutive user messages are merged."""
        messages = [
            mock_message("user", "Hello"),
            mock_message("user", "Are you there?"),
            mock_message("assistant", "Yes!"),
        ]
        
        result = validate_anthropic_turns(messages)
        
        assert len(result) == 2  # merged user + assistant
        assert result[0].role == "user"
        assert result[1].role == "assistant"
    
    def test_preserve_user_assistant_alternation(self, mock_message):
        """Test that proper alternation is preserved."""
        messages = [
            mock_message("user", "Hello"),
            mock_message("assistant", "Hi"),
            mock_message("user", "How are you?"),
            mock_message("assistant", "Good"),
        ]
        
        result = validate_anthropic_turns(messages)
        
        assert len(result) == 4
    
    def test_empty_messages_list(self):
        """Test handling empty messages list."""
        result = validate_anthropic_turns([])
        assert result == []
    
    def test_assistant_messages_not_merged(self, mock_message):
        """Test that consecutive assistant messages are NOT merged."""
        messages = [
            mock_message("user", "Hello"),
            mock_message("assistant", "Hi"),
            mock_message("assistant", "How are you?"),
        ]
        
        result = validate_anthropic_turns(messages)
        
        # Both assistant messages should be kept
        assert len(result) == 3


class TestLimitHistoryTurns:
    """Test history turn limiting."""
    
    def test_limit_to_last_n_user_turns(self, mock_message):
        """Test limiting to last N user turns."""
        messages = [
            mock_message("user", "Message 1"),
            mock_message("assistant", "Response 1"),
            mock_message("user", "Message 2"),
            mock_message("assistant", "Response 2"),
            mock_message("user", "Message 3"),
            mock_message("assistant", "Response 3"),
        ]
        
        result = limit_history_turns(messages, limit=2)
        
        # Should keep last 2 user turns + their responses
        assert len(result) == 4
        assert result[0].content == "Message 2"
    
    def test_no_limit_returns_all(self, mock_message):
        """Test that None limit returns all messages."""
        messages = [
            mock_message("user", "Message 1"),
            mock_message("assistant", "Response 1"),
        ]
        
        result = limit_history_turns(messages, limit=None)
        
        assert len(result) == 2
    
    def test_zero_limit_returns_all(self, mock_message):
        """Test that zero limit returns all messages."""
        messages = [
            mock_message("user", "Message 1"),
        ]
        
        result = limit_history_turns(messages, limit=0)
        
        assert len(result) == 1
    
    def test_limit_exceeds_messages(self, mock_message):
        """Test limit greater than message count."""
        messages = [
            mock_message("user", "Message 1"),
            mock_message("assistant", "Response 1"),
        ]
        
        result = limit_history_turns(messages, limit=10)
        
        assert len(result) == 2
    
    def test_empty_messages(self):
        """Test with empty messages list."""
        result = limit_history_turns([], limit=5)
        assert result == []


class TestGetDmHistoryLimit:
    """Test DM history limit retrieval from config."""
    
    def test_get_limit_from_provider_default(self):
        """Test getting default limit from provider config."""
        config = {
            "channels": {
                "telegram": {
                    "dmHistoryLimit": 20
                }
            }
        }
        
        limit = get_dm_history_limit_from_session_key(
            "agent:main:telegram:dm:123456",
            config
        )
        
        assert limit == 20
    
    def test_get_limit_from_per_dm_override(self):
        """Test getting per-DM override limit."""
        config = {
            "channels": {
                "telegram": {
                    "dmHistoryLimit": 20,
                    "dms": {
                        "123456": {
                            "historyLimit": 50
                        }
                    }
                }
            }
        }
        
        limit = get_dm_history_limit_from_session_key(
            "agent:main:telegram:dm:123456",
            config
        )
        
        assert limit == 50  # Per-DM override takes precedence
    
    def test_non_dm_session_returns_none(self):
        """Test that non-DM sessions return None."""
        config = {
            "channels": {
                "telegram": {
                    "dmHistoryLimit": 20
                }
            }
        }
        
        limit = get_dm_history_limit_from_session_key(
            "agent:main:telegram:group:456",
            config
        )
        
        assert limit is None
    
    def test_missing_config_returns_none(self):
        """Test that missing config returns None."""
        limit = get_dm_history_limit_from_session_key(
            "agent:main:telegram:dm:123",
            None
        )
        
        assert limit is None
    
    def test_thread_suffix_stripped(self):
        """Test that thread suffix is stripped from user ID."""
        config = {
            "channels": {
                "telegram": {
                    "dms": {
                        "123456": {
                            "historyLimit": 30
                        }
                    }
                }
            }
        }
        
        limit = get_dm_history_limit_from_session_key(
            "agent:main:telegram:dm:123456:thread:789",
            config
        )
        
        assert limit == 30
    
    def test_short_session_key_format(self):
        """Test short session key format without agent prefix."""
        config = {
            "channels": {
                "discord": {
                    "dmHistoryLimit": 15
                }
            }
        }
        
        limit = get_dm_history_limit_from_session_key(
            "discord:dm:789",
            config
        )
        
        assert limit == 15


class TestSanitizeSessionHistory:
    """Test session history sanitization."""
    
    def test_remove_empty_content_messages(self, mock_message):
        """Test removing messages with empty content."""
        messages = [
            mock_message("user", "Hello"),
            mock_message("user", ""),
            mock_message("assistant", "Hi"),
        ]
        
        result = sanitize_session_history(messages, remove_empty=True)
        
        assert len(result) == 2
        assert result[0].content == "Hello"
        assert result[1].content == "Hi"
    
    def test_remove_invalid_roles(self, mock_message):
        """Test removing messages with invalid roles."""
        messages = [
            mock_message("user", "Hello"),
            mock_message("invalid_role", "Bad message"),
            mock_message("assistant", "Hi"),
        ]
        
        result = sanitize_session_history(messages, remove_invalid_roles=True)
        
        assert len(result) == 2
    
    def test_preserve_all_valid_roles(self, mock_message):
        """Test that all valid roles are preserved."""
        messages = [
            mock_message("system", "System"),
            mock_message("user", "User"),
            mock_message("assistant", "Assistant"),
            mock_message("tool", "Tool"),
        ]
        
        result = sanitize_session_history(messages)
        
        assert len(result) == 4
    
    def test_keep_empty_content_when_disabled(self, mock_message):
        """Test keeping empty content when remove_empty=False."""
        messages = [
            mock_message("user", ""),
        ]
        
        result = sanitize_session_history(messages, remove_empty=False)
        
        assert len(result) == 1
    
    def test_empty_messages_list(self):
        """Test with empty messages list."""
        result = sanitize_session_history([])
        assert result == []


class TestInjectHistoryImages:
    """Test history image injection."""
    
    def test_inject_images_to_messages(self, mock_message):
        """Test injecting images into specific messages."""
        messages = [
            mock_message("user", "Look at this"),
            mock_message("assistant", "I see"),
            mock_message("user", "And this"),
        ]
        
        history_images = {
            0: [{"type": "image", "source": "image1.png"}],
            2: [{"type": "image", "source": "image2.png"}],
        }
        
        modified = inject_history_images_into_messages(messages, history_images)
        
        assert modified is True
        # Check that images were added to content
        assert isinstance(messages[0].content, list)
        assert isinstance(messages[2].content, list)
    
    def test_no_images_returns_false(self, mock_message):
        """Test that no images returns False."""
        messages = [mock_message("user", "Hello")]
        
        modified = inject_history_images_into_messages(messages, {})
        
        assert modified is False
    
    def test_invalid_index_skipped(self, mock_message):
        """Test that invalid indices are skipped."""
        messages = [
            mock_message("user", "Hello"),
        ]
        
        history_images = {
            10: [{"type": "image", "source": "image.png"}],  # Invalid index
        }
        
        modified = inject_history_images_into_messages(messages, history_images)
        
        # Should not crash, but won't modify anything
        assert modified is False
    
    def test_string_content_converted_to_list(self, mock_message):
        """Test that string content is converted to list with images."""
        messages = [
            mock_message("user", "Text content"),
        ]
        
        history_images = {
            0: [{"type": "image", "source": "image.png"}],
        }
        
        inject_history_images_into_messages(messages, history_images)
        
        # Content should now be a list
        assert isinstance(messages[0].content, list)
        # Should have text and image
        assert any(item.get("type") == "text" for item in messages[0].content)
        assert any(item.get("type") == "image" for item in messages[0].content)


class TestIntegration:
    """Integration tests combining multiple functions."""
    
    def test_full_validation_pipeline(self, mock_message):
        """Test full message validation pipeline."""
        messages = [
            mock_message("user", "Hello"),
            mock_message("user", "Are you there?"),  # Will be merged
            mock_message("assistant", "Yes"),
            mock_message("assistant", "I'm here"),  # Will be merged for Gemini
            mock_message("user", "Good"),
        ]
        
        # Sanitize first
        sanitized = sanitize_session_history(messages)
        
        # Validate for Anthropic (merges user messages)
        anthropic_validated = validate_anthropic_turns(sanitized)
        assert len(anthropic_validated) == 4  # 1 merged user + 2 assistant + 1 user
        
        # Validate for Gemini (merges assistant messages)
        gemini_validated = validate_gemini_turns(sanitized)
        assert len(gemini_validated) == 4  # 2 user + 1 merged assistant + 1 user
    
    def test_limit_after_validation(self, mock_message):
        """Test limiting messages after validation."""
        messages = [
            mock_message("user", "Message 1"),
            mock_message("assistant", "Response 1"),
            mock_message("user", "Message 2"),
            mock_message("assistant", "Response 2"),
            mock_message("user", "Message 3"),
            mock_message("assistant", "Response 3"),
        ]
        
        # Validate then limit
        validated = validate_anthropic_turns(messages)
        limited = limit_history_turns(validated, limit=2)
        
        assert len(limited) <= len(messages)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

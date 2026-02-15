"""
Unit tests for history sanitization functionality.

Tests the enhanced sanitize_session_history() that removes metadata fields.
"""
import pytest
from openclaw.agents.history_utils import sanitize_session_history


def test_removes_thinking_metadata():
    """Test that thinking field is removed"""
    messages = [{
        "role": "assistant",
        "content": "Hello",
        "thinking": "Internal thoughts...",
    }]
    
    sanitized = sanitize_session_history(messages)
    
    assert len(sanitized) == 1
    assert "thinking" not in sanitized[0]
    assert sanitized[0]["content"] == "Hello"
    assert sanitized[0]["role"] == "assistant"


def test_removes_details_metadata():
    """Test that details field is removed"""
    messages = [{
        "role": "assistant",
        "content": "Response",
        "details": {"debug": "info", "trace": "data"},
    }]
    
    sanitized = sanitize_session_history(messages)
    
    assert len(sanitized) == 1
    assert "details" not in sanitized[0]
    assert sanitized[0]["content"] == "Response"


def test_removes_usage_metadata():
    """Test that usage field is removed"""
    messages = [{
        "role": "assistant",
        "content": "Response",
        "usage": {"tokens": 100, "cost": 0.001},
    }]
    
    sanitized = sanitize_session_history(messages)
    
    assert len(sanitized) == 1
    assert "usage" not in sanitized[0]


def test_removes_cost_metadata():
    """Test that cost field is removed"""
    messages = [{
        "role": "assistant",
        "content": "Response",
        "cost": 0.001,
    }]
    
    sanitized = sanitize_session_history(messages)
    
    assert len(sanitized) == 1
    assert "cost" not in sanitized[0]


def test_removes_all_metadata():
    """Test that all metadata fields are removed"""
    messages = [{
        "role": "assistant",
        "content": "Hello",
        "thinking": "Internal thoughts...",
        "details": {"debug": "info"},
        "usage": {"tokens": 100},
        "cost": 0.001,
        "extra_field": "should be removed",
    }]
    
    sanitized = sanitize_session_history(messages)
    
    assert len(sanitized) == 1
    assert "thinking" not in sanitized[0]
    assert "details" not in sanitized[0]
    assert "usage" not in sanitized[0]
    assert "cost" not in sanitized[0]
    assert "extra_field" not in sanitized[0]
    assert sanitized[0]["content"] == "Hello"


def test_preserves_essential_fields():
    """Test that essential fields are preserved"""
    messages = [{
        "role": "assistant",
        "content": "Response",
        "id": "msg-123",
        "timestamp": 1234567890,
        "thinking": "Remove this",
    }]
    
    sanitized = sanitize_session_history(messages)
    
    assert len(sanitized) == 1
    assert sanitized[0]["role"] == "assistant"
    assert sanitized[0]["content"] == "Response"
    assert sanitized[0]["id"] == "msg-123"
    assert sanitized[0]["timestamp"] == 1234567890
    assert "thinking" not in sanitized[0]


def test_preserves_tool_fields():
    """Test that tool-specific fields are preserved"""
    messages = [{
        "role": "toolResult",
        "content": "Tool output",
        "toolCallId": "call-123",
        "toolName": "read",
        "usage": {"tokens": 50},  # Should be removed
    }]
    
    sanitized = sanitize_session_history(messages)
    
    assert len(sanitized) == 1
    assert sanitized[0]["toolCallId"] == "call-123"
    assert sanitized[0]["toolName"] == "read"
    assert "usage" not in sanitized[0]


def test_removes_empty_tool_results_list():
    """Test that empty tool results (list) are removed"""
    messages = [{
        "role": "toolResult",
        "content": [],
        "toolCallId": "123",
    }]
    
    sanitized = sanitize_session_history(messages)
    assert len(sanitized) == 0


def test_removes_empty_tool_results_string():
    """Test that empty tool results (whitespace string) are removed"""
    messages = [{
        "role": "toolResult",
        "content": "   \n  ",
        "toolCallId": "123",
    }]
    
    sanitized = sanitize_session_history(messages)
    assert len(sanitized) == 0


def test_removes_messages_without_role():
    """Test that messages without role are removed"""
    messages = [
        {"content": "No role"},
        {"role": "user", "content": "Has role"},
    ]
    
    sanitized = sanitize_session_history(messages)
    
    assert len(sanitized) == 1
    assert sanitized[0]["role"] == "user"


def test_removes_messages_without_content():
    """Test that messages without content are removed"""
    messages = [
        {"role": "user"},  # No content
        {"role": "assistant", "content": None},  # None content
        {"role": "user", "content": ""},  # Empty string
        {"role": "assistant", "content": "Valid"},  # Valid
    ]
    
    sanitized = sanitize_session_history(messages)
    
    assert len(sanitized) == 1
    assert sanitized[0]["content"] == "Valid"


def test_removes_empty_content_arrays():
    """Test that messages with empty content arrays are removed"""
    messages = [
        {"role": "system", "content": []},
        {"role": "user", "content": "Valid"},
    ]
    
    sanitized = sanitize_session_history(messages)
    
    assert len(sanitized) == 1
    assert sanitized[0]["content"] == "Valid"


def test_handles_multiple_messages():
    """Test sanitization of multiple messages"""
    messages = [
        {"role": "user", "content": "Question"},
        {"role": "assistant", "content": "Answer", "thinking": "Remove"},
        {"role": "toolResult", "content": "", "toolCallId": "1"},  # Empty, remove
        {"role": "user", "content": "Follow-up"},
    ]
    
    sanitized = sanitize_session_history(messages)
    
    assert len(sanitized) == 3
    assert sanitized[0]["role"] == "user"
    assert sanitized[1]["role"] == "assistant"
    assert "thinking" not in sanitized[1]
    assert sanitized[2]["role"] == "user"


def test_handles_empty_input():
    """Test sanitization of empty message list"""
    messages = []
    sanitized = sanitize_session_history(messages)
    assert len(sanitized) == 0


def test_tool_result_with_valid_content():
    """Test that tool results with valid content are kept"""
    messages = [{
        "role": "toolResult",
        "content": "Valid tool output",
        "toolCallId": "call-123",
    }]
    
    sanitized = sanitize_session_history(messages)
    
    assert len(sanitized) == 1
    assert sanitized[0]["content"] == "Valid tool output"


def test_preserves_message_order():
    """Test that message order is preserved"""
    messages = [
        {"role": "user", "content": "First"},
        {"role": "assistant", "content": "Second", "thinking": "Remove"},
        {"role": "user", "content": "Third"},
        {"role": "assistant", "content": "Fourth"},
    ]
    
    sanitized = sanitize_session_history(messages)
    
    assert len(sanitized) == 4
    assert sanitized[0]["content"] == "First"
    assert sanitized[1]["content"] == "Second"
    assert sanitized[2]["content"] == "Third"
    assert sanitized[3]["content"] == "Fourth"


def test_handles_nested_content():
    """Test sanitization with nested content structures"""
    messages = [{
        "role": "assistant",
        "content": [
            {"type": "text", "text": "Response"},
            {"type": "toolUse", "name": "read"},
        ],
        "thinking": "Remove this",
        "usage": {"tokens": 100},
    }]
    
    sanitized = sanitize_session_history(messages)
    
    assert len(sanitized) == 1
    assert sanitized[0]["role"] == "assistant"
    assert isinstance(sanitized[0]["content"], list)
    assert len(sanitized[0]["content"]) == 2
    assert "thinking" not in sanitized[0]
    assert "usage" not in sanitized[0]


def test_handles_user_messages():
    """Test that user messages are cleaned properly"""
    messages = [{
        "role": "user",
        "content": "User question",
        "extra_metadata": "Should be removed",
        "id": "msg-user-1",
    }]
    
    sanitized = sanitize_session_history(messages)
    
    assert len(sanitized) == 1
    assert sanitized[0]["role"] == "user"
    assert sanitized[0]["content"] == "User question"
    assert sanitized[0]["id"] == "msg-user-1"
    assert "extra_metadata" not in sanitized[0]


def test_handles_system_messages():
    """Test that system messages are cleaned properly"""
    messages = [{
        "role": "system",
        "content": "System prompt",
        "metadata": {"source": "config"},
    }]
    
    sanitized = sanitize_session_history(messages)
    
    assert len(sanitized) == 1
    assert sanitized[0]["role"] == "system"
    assert sanitized[0]["content"] == "System prompt"
    assert "metadata" not in sanitized[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

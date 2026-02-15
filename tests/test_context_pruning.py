"""
Unit tests for context pruning functionality.

Tests the context pruning extension with TTL and soft-trim modes.
"""
import pytest
from openclaw.agents.extensions.context_pruning import (
    ContextPruningSettings,
    prune_context_messages,
    should_prune_tool_result,
    get_pruning_settings_from_config,
    _parse_time_string,
)


def test_disabled_mode_returns_unchanged():
    """Test that disabled mode returns messages unchanged"""
    settings = ContextPruningSettings(mode="disabled")
    
    messages = [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello"},
        {"role": "toolResult", "content": "Output", "toolName": "bash"},
    ]
    
    pruned = prune_context_messages(messages, settings, context_window_tokens=100000)
    
    assert len(pruned) == len(messages)
    assert pruned == messages


def test_prunes_old_tool_results_soft_trim():
    """Test that old tool results are pruned in soft-trim mode"""
    settings = ContextPruningSettings(
        mode="soft-trim",
        soft_trim_ratio=0.5,
        prunable_tools={"bash", "read"},
    )
    
    messages = [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello"},
        {"role": "user", "content": "Read file.txt"},
        {"role": "assistant", "content": "tool call"},
        {"role": "toolResult", "content": "A" * 50000, "toolCallId": "123", "toolName": "bash"},
        {"role": "assistant", "content": "The file says..."},
        {"role": "user", "content": "New question"},
    ]
    
    # Small context window to trigger pruning
    pruned = prune_context_messages(messages, settings, context_window_tokens=100)
    
    # Tool result should be pruned, but surrounding messages kept
    tool_result_present = any(m.get("role") == "toolResult" for m in pruned)
    assert not tool_result_present
    
    # User and assistant messages preserved
    user_messages = [m for m in pruned if m.get("role") == "user"]
    assert len(user_messages) >= 2


def test_bootstrap_safety():
    """Test that messages before first user message are protected"""
    settings = ContextPruningSettings(
        mode="soft-trim",
        keep_bootstrap_safe=True,
        soft_trim_ratio=0.1,  # Very aggressive
    )
    
    messages = [
        {"role": "system", "content": "System prompt"},
        {"role": "assistant", "content": "I read SOUL.md"},  # Before first user
        {"role": "user", "content": "Hi"},  # First user message
        {"role": "toolResult", "content": "Old result", "toolCallId": "456", "toolName": "bash"},
    ]
    
    pruned = prune_context_messages(messages, settings, context_window_tokens=1000)
    
    # System and assistant before first user should be kept
    assert pruned[0]["role"] == "system"
    assert pruned[1]["role"] == "assistant"
    assert pruned[1]["content"] == "I read SOUL.md"


def test_preserves_non_prunable_tools():
    """Test that non-prunable tool results are kept"""
    settings = ContextPruningSettings(
        mode="soft-trim",
        soft_trim_ratio=0.1,  # Very aggressive
        prunable_tools={"bash"},  # Only bash is prunable
    )
    
    messages = [
        {"role": "user", "content": "Question"},
        {"role": "toolResult", "content": "Bash output", "toolName": "bash", "toolCallId": "1"},
        {"role": "toolResult", "content": "Important data", "toolName": "database_query", "toolCallId": "2"},
    ]
    
    pruned = prune_context_messages(messages, settings, context_window_tokens=100)
    
    # Bash result may be pruned, but database_query should be kept
    tool_results = [m for m in pruned if m.get("role") == "toolResult"]
    tool_names = [m.get("toolName") for m in tool_results]
    
    # database_query should definitely be present
    assert "database_query" in tool_names


def test_preserves_user_messages():
    """Test that user messages are never pruned"""
    settings = ContextPruningSettings(
        mode="soft-trim",
        soft_trim_ratio=0.1,
    )
    
    messages = [
        {"role": "user", "content": "First question"},
        {"role": "user", "content": "Second question"},
        {"role": "user", "content": "Third question"},
    ]
    
    pruned = prune_context_messages(messages, settings, context_window_tokens=100)
    
    # All user messages should be preserved
    assert len(pruned) == 3
    assert all(m["role"] == "user" for m in pruned)


def test_preserves_assistant_messages():
    """Test that assistant messages are never pruned"""
    settings = ContextPruningSettings(
        mode="soft-trim",
        soft_trim_ratio=0.1,
    )
    
    messages = [
        {"role": "user", "content": "Question"},
        {"role": "assistant", "content": "Answer 1"},
        {"role": "assistant", "content": "Answer 2"},
    ]
    
    pruned = prune_context_messages(messages, settings, context_window_tokens=100)
    
    # All messages should be preserved
    assert len(pruned) == 3


def test_preserves_system_messages():
    """Test that system messages are never pruned"""
    settings = ContextPruningSettings(
        mode="soft-trim",
        soft_trim_ratio=0.1,
    )
    
    messages = [
        {"role": "system", "content": "System prompt"},
        {"role": "user", "content": "Question"},
    ]
    
    pruned = prune_context_messages(messages, settings, context_window_tokens=10)
    
    # System message should be preserved
    assert pruned[0]["role"] == "system"


def test_cache_ttl_mode_with_fresh_results():
    """Test cache-ttl mode keeps fresh tool results"""
    settings = ContextPruningSettings(
        mode="cache-ttl",
        ttl_ms=300000,  # 5 minutes
        prunable_tools={"bash"},
    )
    
    current_time = 1000000
    
    messages = [
        {"role": "user", "content": "Question"},
        {
            "role": "toolResult",
            "content": "Fresh output",
            "toolName": "bash",
            "toolCallId": "1",
            "timestamp": current_time - 60000,  # 1 minute ago
        },
    ]
    
    pruned = prune_context_messages(
        messages, settings, context_window_tokens=100000, current_time_ms=current_time
    )
    
    # Fresh tool result should be kept
    tool_results = [m for m in pruned if m.get("role") == "toolResult"]
    assert len(tool_results) == 1


def test_cache_ttl_mode_prunes_expired():
    """Test cache-ttl mode prunes expired tool results"""
    settings = ContextPruningSettings(
        mode="cache-ttl",
        ttl_ms=300000,  # 5 minutes
        prunable_tools={"bash"},
    )
    
    current_time = 1000000
    
    messages = [
        {"role": "user", "content": "Question"},
        {
            "role": "toolResult",
            "content": "Old output",
            "toolName": "bash",
            "toolCallId": "1",
            "timestamp": current_time - 400000,  # 6.67 minutes ago (expired)
        },
    ]
    
    pruned = prune_context_messages(
        messages, settings, context_window_tokens=100000, current_time_ms=current_time
    )
    
    # Expired tool result should be pruned
    tool_results = [m for m in pruned if m.get("role") == "toolResult"]
    assert len(tool_results) == 0


def test_empty_message_list():
    """Test pruning empty message list"""
    settings = ContextPruningSettings(mode="soft-trim")
    
    messages = []
    pruned = prune_context_messages(messages, settings, context_window_tokens=100000)
    
    assert len(pruned) == 0


def test_should_prune_tool_result_cache_ttl():
    """Test should_prune_tool_result with cache-ttl mode"""
    settings = ContextPruningSettings(
        mode="cache-ttl",
        ttl_ms=300000,
        prunable_tools={"bash"},
    )
    
    current_time = 1000000
    
    # Fresh result
    assert not should_prune_tool_result(
        "bash", "call-1", current_time - 100000, settings, current_time
    )
    
    # Expired result
    assert should_prune_tool_result(
        "bash", "call-2", current_time - 400000, settings, current_time
    )
    
    # Non-prunable tool
    assert not should_prune_tool_result(
        "database", "call-3", current_time - 400000, settings, current_time
    )


def test_get_pruning_settings_from_config():
    """Test getting pruning settings from configuration"""
    config = {
        "agents": {
            "defaults": {
                "contextPruning": {
                    "mode": "soft-trim",
                    "ttl": "10m",
                    "softTrimRatio": 0.8,
                    "prunableTools": ["bash", "read", "write"],
                }
            }
        }
    }
    
    settings = get_pruning_settings_from_config(config)
    
    assert settings.mode == "soft-trim"
    assert settings.ttl_ms == 600000  # 10 minutes in ms
    assert settings.soft_trim_ratio == 0.8
    assert "bash" in settings.prunable_tools
    assert "read" in settings.prunable_tools


def test_get_pruning_settings_defaults():
    """Test getting default pruning settings"""
    config = None
    settings = get_pruning_settings_from_config(config)
    
    assert settings.mode == "disabled"
    assert settings.ttl_ms == 300000  # 5 minutes default
    assert settings.soft_trim_ratio == 0.75


def test_parse_time_string():
    """Test parsing time strings"""
    assert _parse_time_string("5000ms") == 5000
    assert _parse_time_string("30s") == 30000
    assert _parse_time_string("5m") == 300000
    assert _parse_time_string("1h") == 3600000
    assert _parse_time_string("1000") == 1000  # No unit, assume ms


def test_custom_prunable_check():
    """Test custom prunable tool check function"""
    settings = ContextPruningSettings(mode="soft-trim")
    
    # Custom function that only prunes "read" tool
    def custom_prunable(tool_name: str) -> bool:
        return tool_name == "read"
    
    messages = [
        {"role": "user", "content": "Question"},
        {"role": "toolResult", "content": "Output 1", "toolName": "read", "toolCallId": "1"},
        {"role": "toolResult", "content": "Output 2", "toolName": "bash", "toolCallId": "2"},
    ]
    
    pruned = prune_context_messages(
        messages, settings, context_window_tokens=50, is_tool_prunable=custom_prunable
    )
    
    # Only "read" tool result should be prunable
    tool_results = [m for m in pruned if m.get("role") == "toolResult"]
    tool_names = [m.get("toolName") for m in tool_results]
    
    # bash should be kept (not prunable), read might be pruned
    assert "bash" in tool_names


def test_pruning_respects_soft_trim_ratio():
    """Test that pruning respects soft_trim_ratio"""
    settings = ContextPruningSettings(
        mode="soft-trim",
        soft_trim_ratio=0.5,  # 50% of window
        prunable_tools={"bash"},
    )
    
    # Create messages that exceed 50% of 1000 token window
    messages = [
        {"role": "user", "content": "Q"},
        {"role": "toolResult", "content": "A" * 2000, "toolName": "bash", "toolCallId": "1"},
        {"role": "toolResult", "content": "B" * 2000, "toolName": "bash", "toolCallId": "2"},
    ]
    
    pruned = prune_context_messages(messages, settings, context_window_tokens=1000)
    
    # Should prune some tool results to stay under budget
    tool_results = [m for m in pruned if m.get("role") == "toolResult"]
    assert len(tool_results) < 2


def test_mixed_tool_types():
    """Test pruning with mix of prunable and non-prunable tools"""
    settings = ContextPruningSettings(
        mode="soft-trim",
        soft_trim_ratio=0.5,
        prunable_tools={"bash", "read"},
    )
    
    messages = [
        {"role": "user", "content": "Q"},
        {"role": "toolResult", "content": "A" * 1000, "toolName": "bash", "toolCallId": "1"},
        {"role": "toolResult", "content": "B" * 1000, "toolName": "database", "toolCallId": "2"},
        {"role": "toolResult", "content": "C" * 1000, "toolName": "read", "toolCallId": "3"},
    ]
    
    pruned = prune_context_messages(messages, settings, context_window_tokens=500)
    
    # database tool result should always be kept
    tool_results = [m for m in pruned if m.get("role") == "toolResult"]
    tool_names = [m.get("toolName") for m in tool_results]
    
    assert "database" in tool_names


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

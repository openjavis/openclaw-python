"""
End-to-end integration tests for context flow.

Tests the complete flow: history → sanitization → pruning → conversion → LLM
"""
import pytest
from openclaw.agents.context import convert_to_llm, estimate_tokens_from_messages
from openclaw.agents.history_utils import sanitize_session_history
from openclaw.agents.extensions.context_pruning import (
    ContextPruningSettings,
    prune_context_messages,
)


def test_complete_context_flow_basic():
    """Test complete context flow with basic messages"""
    # 1. Create session history with metadata
    history = [
        {"role": "user", "content": "Hello"},
        {
            "role": "assistant",
            "content": "Hi there!",
            "thinking": "User greeted me",  # Should be removed
            "usage": {"tokens": 10},  # Should be removed
        },
        {"role": "user", "content": "How are you?"},
        {
            "role": "assistant",
            "content": "I'm doing well!",
            "cost": 0.001,  # Should be removed
        },
    ]
    
    # 2. Sanitize history
    sanitized = sanitize_session_history(history)
    
    # Verify sanitization
    assert len(sanitized) == 4
    assert "thinking" not in sanitized[1]
    assert "usage" not in sanitized[1]
    assert "cost" not in sanitized[3]
    
    # 3. Apply pruning (disabled in this case)
    pruning_settings = ContextPruningSettings(mode="disabled")
    pruned = prune_context_messages(sanitized, pruning_settings, context_window_tokens=100000)
    
    assert len(pruned) == 4
    
    # 4. Convert to LLM format
    class Message:
        def __init__(self, role, content):
            self.role = role
            self.content = content
    
    llm_messages = [Message(m["role"], m["content"]) for m in pruned]
    converted = convert_to_llm(llm_messages)
    
    # 5. Verify final output
    assert len(converted) == 4
    assert all(m.get("role") in ["user", "assistant"] for m in converted)
    assert converted[0]["content"] == "Hello"
    assert converted[1]["content"] == "Hi there!"


def test_complete_context_flow_with_tools():
    """Test complete context flow with tool usage"""
    # 1. Create history with tool calls
    history = [
        {"role": "user", "content": "Read file.txt"},
        {"role": "assistant", "content": "Let me read that", "thinking": "Remove this"},
        {
            "role": "toolResult",
            "content": "File content here",
            "toolCallId": "call-123",
            "toolName": "read",
            "usage": {"tokens": 50},  # Should be removed
        },
        {"role": "assistant", "content": "The file contains..."},
    ]
    
    # 2. Sanitize
    sanitized = sanitize_session_history(history)
    assert "thinking" not in sanitized[1]
    assert "usage" not in sanitized[2]
    
    # 3. Prune (keep all in this case)
    pruning_settings = ContextPruningSettings(mode="disabled")
    pruned = prune_context_messages(sanitized, pruning_settings, context_window_tokens=100000)
    
    assert len(pruned) == 4
    
    # 4. Convert
    class Message:
        def __init__(self, d):
            for k, v in d.items():
                setattr(self, k, v)
    
    llm_messages = [Message(m) for m in pruned]
    converted = convert_to_llm(llm_messages)
    
    # 5. Verify
    assert len(converted) == 4
    assert converted[2]["role"] == "tool"
    assert converted[2]["tool_call_id"] == "call-123"


def test_complete_context_flow_with_pruning():
    """Test complete context flow with active pruning"""
    # 1. Create history with prunable tool results
    history = [
        {"role": "user", "content": "Question"},
        {"role": "assistant", "content": "Answer"},
        {
            "role": "toolResult",
            "content": "X" * 10000,  # Large result
            "toolCallId": "call-1",
            "toolName": "bash",
        },
        {"role": "assistant", "content": "Got the result"},
        {"role": "user", "content": "New question"},
    ]
    
    # 2. Sanitize
    sanitized = sanitize_session_history(history)
    
    # 3. Prune with aggressive soft-trim
    pruning_settings = ContextPruningSettings(
        mode="soft-trim",
        soft_trim_ratio=0.3,
        prunable_tools={"bash"},
    )
    pruned = prune_context_messages(sanitized, pruning_settings, context_window_tokens=1000)
    
    # Tool result should be pruned
    tool_results = [m for m in pruned if m.get("role") == "toolResult"]
    assert len(tool_results) == 0
    
    # User and assistant messages should be kept
    assert len(pruned) >= 4
    
    # 4. Convert
    class Message:
        def __init__(self, d):
            for k, v in d.items():
                setattr(self, k, v)
    
    llm_messages = [Message(m) for m in pruned]
    converted = convert_to_llm(llm_messages)
    
    # 5. Verify no tool results in output
    tool_msgs = [m for m in converted if m.get("role") == "tool"]
    assert len(tool_msgs) == 0


def test_complete_context_flow_with_summaries():
    """Test complete context flow with branch and compaction summaries"""
    # 1. Create history with summaries
    history = [
        {"role": "compactionSummary", "summary": "Earlier work on files"},
        {"role": "user", "content": "Continue"},
        {"role": "assistant", "content": "Sure"},
        {"role": "branchSummary", "summary": "Parallel branch completed"},
    ]
    
    # 2. Sanitize (summaries pass through)
    sanitized = sanitize_session_history(history)
    assert len(sanitized) == 4
    
    # 3. Prune (disabled)
    pruning_settings = ContextPruningSettings(mode="disabled")
    pruned = prune_context_messages(sanitized, pruning_settings, context_window_tokens=100000)
    
    # 4. Convert
    class Message:
        def __init__(self, d):
            for k, v in d.items():
                setattr(self, k, v)
    
    llm_messages = [Message(m) for m in pruned]
    converted = convert_to_llm(llm_messages)
    
    # 5. Verify summaries converted to user messages
    assert len(converted) == 4
    assert converted[0]["role"] == "user"
    assert "Compaction Summary" in converted[0]["content"]
    assert converted[3]["role"] == "user"
    assert "Branch Summary" in converted[3]["content"]


def test_complete_context_flow_removes_empty():
    """Test that empty messages are removed in sanitization"""
    history = [
        {"role": "user", "content": "Question"},
        {"role": "assistant", "content": ""},  # Empty, should be removed
        {"role": "toolResult", "content": [], "toolCallId": "1"},  # Empty, remove
        {"role": "user", "content": "Follow-up"},
        {"role": "assistant", "content": "Response"},
    ]
    
    # Sanitize
    sanitized = sanitize_session_history(history)
    
    # Empty messages should be removed
    assert len(sanitized) == 3
    assert sanitized[0]["content"] == "Question"
    assert sanitized[1]["content"] == "Follow-up"
    assert sanitized[2]["content"] == "Response"


def test_complete_context_flow_token_estimation():
    """Test token estimation throughout the flow"""
    history = [
        {"role": "user", "content": "Short message"},
        {"role": "assistant", "content": "X" * 1000},  # Long message
    ]
    
    # Estimate tokens before processing
    tokens_before = estimate_tokens_from_messages(history)
    assert tokens_before > 0
    
    # Process
    sanitized = sanitize_session_history(history)
    pruning_settings = ContextPruningSettings(mode="disabled")
    pruned = prune_context_messages(sanitized, pruning_settings, context_window_tokens=100000)
    
    # Estimate after processing
    tokens_after = estimate_tokens_from_messages(pruned)
    
    # Should be similar (no major changes in this case)
    assert abs(tokens_before - tokens_after) < tokens_before * 0.2


def test_complete_context_flow_bootstrap_safety():
    """Test bootstrap safety in pruning"""
    history = [
        {"role": "system", "content": "System prompt"},
        {"role": "assistant", "content": "Bootstrap message"},  # Before first user
        {"role": "user", "content": "First user message"},
        {
            "role": "toolResult",
            "content": "X" * 10000,
            "toolCallId": "1",
            "toolName": "bash",
        },
    ]
    
    # Sanitize
    sanitized = sanitize_session_history(history)
    
    # Prune with aggressive settings
    pruning_settings = ContextPruningSettings(
        mode="soft-trim",
        soft_trim_ratio=0.1,
        keep_bootstrap_safe=True,
    )
    pruned = prune_context_messages(sanitized, pruning_settings, context_window_tokens=1000)
    
    # Bootstrap messages should be kept
    assert pruned[0]["role"] == "system"
    assert pruned[1]["role"] == "assistant"
    assert pruned[1]["content"] == "Bootstrap message"


def test_complete_context_flow_mixed_metadata():
    """Test handling of various metadata fields"""
    history = [
        {
            "role": "user",
            "content": "Question",
            "id": "msg-1",
            "timestamp": 1000,
            "extra_field": "remove",
        },
        {
            "role": "assistant",
            "content": "Answer",
            "thinking": "remove",
            "details": {"debug": "remove"},
            "usage": {"tokens": 100},
            "cost": 0.001,
            "id": "msg-2",
        },
    ]
    
    # Sanitize
    sanitized = sanitize_session_history(history)
    
    # Verify metadata removed but essentials kept
    assert "extra_field" not in sanitized[0]
    assert sanitized[0]["id"] == "msg-1"
    assert sanitized[0]["timestamp"] == 1000
    
    assert "thinking" not in sanitized[1]
    assert "details" not in sanitized[1]
    assert "usage" not in sanitized[1]
    assert "cost" not in sanitized[1]
    assert sanitized[1]["id"] == "msg-2"


def test_complete_context_flow_cache_ttl():
    """Test complete flow with cache-ttl pruning"""
    current_time = 1000000
    
    history = [
        {"role": "user", "content": "Question"},
        {
            "role": "toolResult",
            "content": "Fresh data",
            "toolCallId": "1",
            "toolName": "bash",
            "timestamp": current_time - 60000,  # 1 min ago
        },
        {
            "role": "toolResult",
            "content": "Old data",
            "toolCallId": "2",
            "toolName": "bash",
            "timestamp": current_time - 400000,  # 6+ min ago
        },
    ]
    
    # Sanitize
    sanitized = sanitize_session_history(history)
    
    # Prune with TTL
    pruning_settings = ContextPruningSettings(
        mode="cache-ttl",
        ttl_ms=300000,  # 5 minutes
        prunable_tools={"bash"},
    )
    pruned = prune_context_messages(
        sanitized, pruning_settings, context_window_tokens=100000, current_time_ms=current_time
    )
    
    # Fresh result kept, old result pruned
    tool_results = [m for m in pruned if m.get("role") == "toolResult"]
    assert len(tool_results) == 1
    assert tool_results[0]["content"] == "Fresh data"


def test_complete_context_flow_complex():
    """Test complex scenario with all features"""
    current_time = 1000000
    
    history = [
        {"role": "system", "content": "System"},
        {"role": "compactionSummary", "summary": "Previous work"},
        {"role": "user", "content": "Start"},
        {
            "role": "assistant",
            "content": "Response",
            "thinking": "remove",
            "usage": {"tokens": 50},
        },
        {
            "role": "toolResult",
            "content": "Data",
            "toolCallId": "1",
            "toolName": "bash",
            "timestamp": current_time - 100000,
            "cost": 0.001,
        },
        {"role": "user", "content": "Continue"},
        {"role": "branchSummary", "summary": "Branch work"},
        {"role": "toolResult", "content": "", "toolCallId": "2"},  # Empty
        {"role": "user", "content": "Final"},
    ]
    
    # Full flow
    sanitized = sanitize_session_history(history)
    
    # Should remove empty tool result and metadata
    assert len(sanitized) == 8  # One empty removed
    
    pruning_settings = ContextPruningSettings(mode="disabled")
    pruned = prune_context_messages(sanitized, pruning_settings, context_window_tokens=100000)
    
    # Convert
    class Message:
        def __init__(self, d):
            for k, v in d.items():
                setattr(self, k, v)
    
    llm_messages = [Message(m) for m in pruned]
    converted = convert_to_llm(llm_messages)
    
    # Verify
    assert len(converted) >= 7
    assert "thinking" not in str(converted)
    assert "usage" not in str(converted)
    assert "cost" not in str(converted)
    
    # Summaries should be user messages
    summary_msgs = [m for m in converted if "Summary" in str(m.get("content", ""))]
    assert len(summary_msgs) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

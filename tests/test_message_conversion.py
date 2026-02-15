"""
Unit tests for message conversion functionality.

Tests convert_to_llm() with support for branchSummary and compactionSummary types.
"""
import pytest
from openclaw.agents.context import convert_to_llm
from openclaw.agents.types import AgentMessage


def test_user_message_conversion():
    """Test conversion of user message"""
    class UserMsg:
        role = "user"
        content = "Hello, assistant!"
    
    messages = [UserMsg()]
    converted = convert_to_llm(messages)
    
    assert len(converted) == 1
    assert converted[0]["role"] == "user"
    assert converted[0]["content"] == "Hello, assistant!"


def test_assistant_message_conversion():
    """Test conversion of assistant message"""
    class AssistantMsg:
        role = "assistant"
        content = "Hello, user!"
    
    messages = [AssistantMsg()]
    converted = convert_to_llm(messages)
    
    assert len(converted) == 1
    assert converted[0]["role"] == "assistant"
    assert converted[0]["content"] == "Hello, user!"


def test_tool_result_conversion():
    """Test conversion of tool result message"""
    class ToolResultMsg:
        role = "toolResult"
        content = "File content"
        tool_call_id = "call-123"
    
    messages = [ToolResultMsg()]
    converted = convert_to_llm(messages)
    
    assert len(converted) == 1
    assert converted[0]["role"] == "tool"
    assert converted[0]["content"] == "File content"
    assert converted[0]["tool_call_id"] == "call-123"


def test_system_message_conversion():
    """Test conversion of system message"""
    class SystemMsg:
        role = "system"
        content = "You are a helpful assistant"
    
    messages = [SystemMsg()]
    converted = convert_to_llm(messages)
    
    assert len(converted) == 1
    assert converted[0]["role"] == "system"
    assert converted[0]["content"] == "You are a helpful assistant"


def test_branch_summary_conversion():
    """Test conversion of branch summary message"""
    class BranchSummaryMsg:
        role = "branchSummary"
        summary = "Branch work completed successfully"
        timestamp = 1234567890
    
    messages = [BranchSummaryMsg()]
    converted = convert_to_llm(messages)
    
    assert len(converted) == 1
    assert converted[0]["role"] == "user"
    assert "Branch Summary" in converted[0]["content"]
    assert "Auto-generated" in converted[0]["content"]
    assert "parallel branch" in converted[0]["content"]
    assert "Branch work completed successfully" in converted[0]["content"]
    assert converted[0]["timestamp"] == 1234567890


def test_compaction_summary_conversion():
    """Test conversion of compaction summary message"""
    class CompactionSummaryMsg:
        role = "compactionSummary"
        summary = "Earlier conversation about file operations"
        timestamp = 1234567890
    
    messages = [CompactionSummaryMsg()]
    converted = convert_to_llm(messages)
    
    assert len(converted) == 1
    assert converted[0]["role"] == "user"
    assert "Compaction Summary" in converted[0]["content"]
    assert "Auto-generated" in converted[0]["content"]
    assert "earlier conversation" in converted[0]["content"]
    assert "Earlier conversation about file operations" in converted[0]["content"]
    assert converted[0]["timestamp"] == 1234567890


def test_branch_summary_prefix():
    """Test that branch summary has correct prefix"""
    class BranchSummaryMsg:
        role = "branchSummary"
        summary = "Test summary"
    
    messages = [BranchSummaryMsg()]
    converted = convert_to_llm(messages)
    
    content = converted[0]["content"]
    
    # Check prefix structure
    assert content.startswith("# Branch Summary (Auto-generated)")
    assert "\n\nThe following is a summary of a parallel branch that was merged:\n\n" in content
    assert content.endswith("Test summary")


def test_compaction_summary_prefix():
    """Test that compaction summary has correct prefix"""
    class CompactionSummaryMsg:
        role = "compactionSummary"
        summary = "Test summary"
    
    messages = [CompactionSummaryMsg()]
    converted = convert_to_llm(messages)
    
    content = converted[0]["content"]
    
    # Check prefix structure
    assert content.startswith("# Compaction Summary (Auto-generated)")
    assert "\n\nThe following is a summary of earlier conversation history:\n\n" in content
    assert content.endswith("Test summary")


def test_mixed_message_types():
    """Test conversion of mixed message types"""
    class UserMsg:
        role = "user"
        content = "Question"
    
    class AssistantMsg:
        role = "assistant"
        content = "Answer"
    
    class BranchSummaryMsg:
        role = "branchSummary"
        summary = "Branch summary"
    
    messages = [UserMsg(), AssistantMsg(), BranchSummaryMsg()]
    converted = convert_to_llm(messages)
    
    assert len(converted) == 3
    assert converted[0]["role"] == "user"
    assert converted[1]["role"] == "assistant"
    assert converted[2]["role"] == "user"  # Summary converted to user
    assert "Branch Summary" in converted[2]["content"]


def test_empty_message_list():
    """Test conversion of empty message list"""
    messages = []
    converted = convert_to_llm(messages)
    assert len(converted) == 0


def test_message_without_role():
    """Test that messages without role are skipped"""
    class InvalidMsg:
        content = "No role"
    
    class ValidMsg:
        role = "user"
        content = "Has role"
    
    messages = [InvalidMsg(), ValidMsg()]
    converted = convert_to_llm(messages)
    
    assert len(converted) == 1
    assert converted[0]["content"] == "Has role"


def test_assistant_with_list_content():
    """Test assistant message with list content"""
    class AssistantMsg:
        role = "assistant"
        content = [
            {"type": "text", "text": "Part 1"},
            {"type": "text", "text": "Part 2"},
        ]
    
    messages = [AssistantMsg()]
    converted = convert_to_llm(messages)
    
    assert len(converted) == 1
    assert converted[0]["role"] == "assistant"
    # Text parts should be combined
    assert "Part 1" in converted[0]["content"]
    assert "Part 2" in converted[0]["content"]


def test_assistant_with_tool_calls():
    """Test assistant message with tool calls"""
    class AssistantMsg:
        role = "assistant"
        content = "Let me read that file"
        tool_calls = [{"name": "read", "arguments": {"path": "file.txt"}}]
    
    messages = [AssistantMsg()]
    converted = convert_to_llm(messages)
    
    assert len(converted) == 1
    assert converted[0]["role"] == "assistant"
    assert "tool_calls" in converted[0]
    assert len(converted[0]["tool_calls"]) == 1


def test_assistant_with_thinking():
    """Test assistant message with thinking field"""
    class AssistantMsg:
        role = "assistant"
        content = "Response"
        thinking = "Internal reasoning"
    
    messages = [AssistantMsg()]
    converted = convert_to_llm(messages)
    
    assert len(converted) == 1
    assert converted[0]["role"] == "assistant"
    assert "thinking" in converted[0]
    assert converted[0]["thinking"] == "Internal reasoning"


def test_preserves_message_order():
    """Test that message order is preserved"""
    class UserMsg1:
        role = "user"
        content = "First"
    
    class AssistantMsg1:
        role = "assistant"
        content = "Second"
    
    class UserMsg2:
        role = "user"
        content = "Third"
    
    messages = [UserMsg1(), AssistantMsg1(), UserMsg2()]
    converted = convert_to_llm(messages)
    
    assert len(converted) == 3
    assert converted[0]["content"] == "First"
    assert converted[1]["content"] == "Second"
    assert converted[2]["content"] == "Third"


def test_branch_summary_without_timestamp():
    """Test branch summary without timestamp field"""
    class BranchSummaryMsg:
        role = "branchSummary"
        summary = "Test summary"
        # No timestamp
    
    messages = [BranchSummaryMsg()]
    converted = convert_to_llm(messages)
    
    assert len(converted) == 1
    assert converted[0]["role"] == "user"
    assert "timestamp" not in converted[0]


def test_compaction_summary_without_timestamp():
    """Test compaction summary without timestamp field"""
    class CompactionSummaryMsg:
        role = "compactionSummary"
        summary = "Test summary"
        # No timestamp
    
    messages = [CompactionSummaryMsg()]
    converted = convert_to_llm(messages)
    
    assert len(converted) == 1
    assert converted[0]["role"] == "user"
    assert "timestamp" not in converted[0]


def test_complex_conversation_flow():
    """Test complex conversation with all message types"""
    class UserMsg:
        role = "user"
        content = "Please help"
    
    class AssistantMsg:
        role = "assistant"
        content = "Sure!"
    
    class ToolResultMsg:
        role = "toolResult"
        content = "Tool output"
        tool_call_id = "call-1"
    
    class CompactionMsg:
        role = "compactionSummary"
        summary = "Previous work"
    
    class BranchMsg:
        role = "branchSummary"
        summary = "Parallel work"
    
    messages = [
        CompactionMsg(),
        UserMsg(),
        AssistantMsg(),
        ToolResultMsg(),
        BranchMsg(),
    ]
    
    converted = convert_to_llm(messages)
    
    assert len(converted) == 5
    assert converted[0]["role"] == "user"  # Compaction -> user
    assert "Compaction Summary" in converted[0]["content"]
    assert converted[1]["role"] == "user"
    assert converted[2]["role"] == "assistant"
    assert converted[3]["role"] == "tool"
    assert converted[4]["role"] == "user"  # Branch -> user
    assert "Branch Summary" in converted[4]["content"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

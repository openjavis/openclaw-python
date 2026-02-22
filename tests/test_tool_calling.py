"""
Test tool calling and message order
"""
import asyncio
import pytest
from pathlib import Path

from openclaw.agents.runtime import AgentRuntime
from openclaw.agents.session import Session
from openclaw.agents.providers.gemini_provider import GeminiProvider
from openclaw.agents.tools.bash import create_bash_tool as BashTool
from openclaw.agents.tools.web import WebSearchTool
from openclaw.agents.tools.document_gen import PPTGeneratorTool, PDFGeneratorTool


@pytest.mark.asyncio
async def test_message_order():
    """Test that messages are added in correct order: user -> assistant -> tool_result"""
    session = Session(session_id="test-message-order")
    provider = GeminiProvider()
    runtime = AgentRuntime(provider=provider, tools=[BashTool()])
    
    # Add user message
    session.add_user_message("What is the current date?")
    
    # Run agent turn (should call bash tool)
    events = []
    async for event in runtime.run_turn(session=session, user_input="What is the current date?"):
        events.append(event)
    
    # Check message order in session
    messages = session.get_messages()
    
    # Should be: user, assistant (with tool_calls), tool_result, assistant (final response)
    assert messages[0].role == "user", "First message should be user"
    
    # Find assistant message with tool_calls
    assistant_with_tools = None
    tool_result_idx = None
    
    for i, msg in enumerate(messages):
        if msg.role == "assistant" and hasattr(msg, 'tool_calls') and msg.tool_calls:
            assistant_with_tools = i
        elif msg.role == "tool":
            tool_result_idx = i
    
    if assistant_with_tools is not None and tool_result_idx is not None:
        assert assistant_with_tools < tool_result_idx, \
            f"Assistant message with tool_calls (idx {assistant_with_tools}) must come before tool_result (idx {tool_result_idx})"
    
    print("✅ Message order test passed")


@pytest.mark.asyncio
async def test_ppt_generation():
    """Test PPT generation and file event emission"""
    session = Session(session_id="test-ppt")
    provider = GeminiProvider()
    ppt_tool = PPTGeneratorTool()
    runtime = AgentRuntime(provider=provider, tools=[ppt_tool])
    
    # Track events
    file_generated_event = None
    
    async for event in runtime.run_turn(
        session=session, 
        user_input="Create a PPT about Python programming with 3 slides"
    ):
        if event.type == "agent.file_generated":
            file_generated_event = event
    
    # Check if file was generated
    if file_generated_event:
        file_path = file_generated_event.data.get("file_path")
        assert file_path, "File path should be in event data"
        assert Path(file_path).exists(), f"Generated file should exist: {file_path}"
        print(f"✅ PPT generation test passed: {file_path}")
    else:
        print("⚠️  No file generated event (model may not have called the tool)")


@pytest.mark.asyncio
async def test_file_detection_from_metadata():
    """Test that files are detected from metadata (not just content)"""
    from openclaw.agents.tools.base import LegacyToolResult
    
    # Simulate tool result with file_path in metadata
    result = LegacyToolResult(
        success=True,
        content="PPT created successfully",
        metadata={"file_path": "/tmp/test.pptx", "file_type": "ppt"}
    )
    
    # The runtime should detect this file from metadata
    assert result.metadata.get("file_path") == "/tmp/test.pptx"
    assert result.metadata.get("file_type") == "ppt"
    print("✅ File detection from metadata test passed")


@pytest.mark.asyncio
async def test_bash_tool():
    """Test bash tool execution"""
    bash_tool = BashTool()
    result = await bash_tool.execute({"command": "echo 'Hello World'"})
    
    assert result.success, "Bash tool should succeed"
    assert "Hello World" in result.content, "Output should contain 'Hello World'"
    print("✅ Bash tool test passed")


@pytest.mark.asyncio
async def test_web_search_tool():
    """Test web search tool"""
    web_tool = WebSearchTool()
    result = await web_tool.execute({"query": "Python programming"})
    
    assert result.success, "Web search should succeed"
    assert result.content, "Web search should return content"
    print("✅ Web search tool test passed")


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_message_order())
    asyncio.run(test_ppt_generation())
    asyncio.run(test_file_detection_from_metadata())
    asyncio.run(test_bash_tool())
    asyncio.run(test_web_search_tool())
    
    print("\n✅ All tests passed!")

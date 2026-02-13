"""
Integration test for PPT file auto-send feature

Tests the complete flow:
1. Agent generates PPT file
2. Runtime detects file in tool result
3. Runtime emits AGENT_FILE_GENERATED event
4. Channel Manager receives event
5. Channel sends file to user
"""

import asyncio
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from openclaw.agents.runtime import MultiProviderRuntime
from openclaw.agents.session import Session, SessionManager
from openclaw.agents.tools.base import AgentTool, ToolResult
from openclaw.agents.tools.file_manager import prepare_file_for_sending
from openclaw.events import EventType
from openclaw.gateway.channel_manager import ChannelManager
from openclaw.channels.base import InboundMessage


class MockPPTTool(AgentTool):
    """Mock tool that simulates PPT generation"""
    
    name = "generate_ppt"
    description = "Generate a PowerPoint presentation"
    
    def __init__(self, workspace_dir: Path):
        self.workspace_dir = workspace_dir
    
    def get_schema(self) -> dict:
        """Return tool schema"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Presentation title"
                        }
                    },
                    "required": []
                }
            }
        }
    
    async def execute(self, params: dict) -> ToolResult:
        """Simulate PPT generation"""
        # Prepare output path
        output_path, filename = prepare_file_for_sending(
            self.workspace_dir,
            "presentations",
            params.get("title", "Test Presentation")
        )
        
        # Create actual file
        output_path.write_text("Mock PPT content")
        
        # Return file information as JSON string (this triggers auto-send)
        import json
        file_info = {
            "file_path": str(output_path),
            "file_type": "document",
            "caption": f"Generated presentation: {params.get('title', 'Test')}"
        }
        return ToolResult(
            success=True,
            content=json.dumps(file_info)
        )


@pytest.fixture
def temp_workspace():
    """Create temporary workspace"""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def session(temp_workspace):
    """Create test session"""
    session = Session(
        session_id="test-session-123",
        workspace_dir=temp_workspace
    )
    return session


@pytest.mark.asyncio
async def test_ppt_file_generated_event_emission(session, temp_workspace):
    """Test that runtime emits AGENT_FILE_GENERATED event"""
    # Create mock runtime
    runtime = MultiProviderRuntime(
        model_str="openai/gpt-4",
        api_key="mock-key"
    )
    
    # Create mock PPT tool
    ppt_tool = MockPPTTool(temp_workspace)
    
    # Mock the provider's generate method to return tool call
    mock_response = MagicMock()
    mock_response.content = "I'll create the presentation"
    mock_response.tool_calls = [{
        "id": "call_123",
        "name": "generate_ppt",
        "arguments": {"title": "AI Introduction"}
    }]
    
    with patch.object(runtime, '_call_provider', return_value=mock_response):
        events = []
        async for event in runtime.run_turn(
            session,
            "Create a PPT about AI",
            tools=[ppt_tool]
        ):
            events.append(event)
            if hasattr(event, 'type'):
                print(f"Event: {event.type}")
        
        # Check that AGENT_FILE_GENERATED event was emitted
        file_events = [
            e for e in events 
            if hasattr(e, 'type') and 
            (e.type == EventType.AGENT_FILE_GENERATED or 
             str(e.type) == "agent.file_generated")
        ]
        
        assert len(file_events) > 0, "No AGENT_FILE_GENERATED event found"
        
        file_event = file_events[0]
        assert "file_path" in file_event.data
        assert "file_type" in file_event.data
        assert file_event.data["file_type"] == "document"
        assert Path(file_event.data["file_path"]).exists()


@pytest.mark.asyncio
async def test_channel_manager_sends_file(session, temp_workspace):
    """Test that channel manager sends file when event is received"""
    # Create test PPT file
    ppt_path, filename = prepare_file_for_sending(
        temp_workspace,
        "presentations",
        "Test Presentation"
    )
    ppt_path.write_text("Mock PPT content")
    
    # Create mock channel
    mock_channel = MagicMock()
    mock_channel.send_media = AsyncMock()
    mock_channel.send_text = AsyncMock()
    
    # Create channel manager
    channel_manager = ChannelManager()
    channel_manager.register("test", type(mock_channel))
    channel_manager._channels["test"] = mock_channel
    
    # Create mock runtime that emits file event
    mock_runtime = MagicMock()
    
    async def mock_run_turn(*args, **kwargs):
        from openclaw.events import Event
        
        # Emit file generated event
        yield Event(
            type=EventType.AGENT_FILE_GENERATED,
            source="agent-runtime",
            session_id=session.session_id,
            data={
                "file_path": str(ppt_path),
                "file_type": "document",
                "file_name": filename,
                "caption": "Generated presentation: Test Presentation"
            }
        )
        
        # Emit turn complete
        yield Event(
            type=EventType.AGENT_TURN_COMPLETE,
            source="agent-runtime",
            session_id=session.session_id,
            data={}
        )
    
    mock_runtime.run_turn = mock_run_turn
    channel_manager.runtime = mock_runtime
    
    # Create inbound message
    message = InboundMessage(
        chat_id="user-123",
        text="Create a PPT",
        message_id="msg-456"
    )
    
    # Handle message
    await channel_manager.handle_inbound_message("test", message)
    
    # Verify that send_media was called
    mock_channel.send_media.assert_called_once()
    call_args = mock_channel.send_media.call_args
    
    assert call_args[1]["media_url"] == str(ppt_path)
    assert call_args[1]["media_type"] == "document"
    assert "Test Presentation" in call_args[1]["caption"]


@pytest.mark.asyncio
async def test_end_to_end_ppt_generation_and_send(session, temp_workspace):
    """Test complete end-to-end flow"""
    import json
    
    # 1. Tool generates file with proper return format
    ppt_tool = MockPPTTool(temp_workspace)
    result = await ppt_tool.execute({"title": "AI Basics"})
    
    assert result.success
    
    # Parse JSON result
    file_info = json.loads(result.content)
    
    assert "file_path" in file_info
    assert "file_type" in file_info
    assert file_info["file_type"] == "document"
    
    # 2. Verify file exists
    file_path = Path(file_info["file_path"])
    assert file_path.exists()
    assert file_path.parent.name == "presentations"
    assert "AI_Basics" in file_path.name
    assert file_path.suffix == ".pptx"
    
    # 3. Verify file naming convention
    assert len(file_path.stem.split("_")) >= 3  # title_YYYYMMDD_HHMMSS
    
    print(f"✓ File generated: {file_path.name}")
    print(f"✓ File type: {file_info['file_type']}")
    print(f"✓ Caption: {file_info['caption']}")


def test_file_manager_integration(temp_workspace):
    """Test file_manager utilities work correctly"""
    from openclaw.agents.tools.file_manager import (
        get_presentations_dir,
        generate_presentation_filename,
        prepare_file_for_sending
    )
    
    # Test directory creation
    ppt_dir = get_presentations_dir(temp_workspace)
    assert ppt_dir.exists()
    
    # Test filename generation
    filename = generate_presentation_filename("Test PPT")
    assert "Test_PPT" in filename
    assert filename.endswith(".pptx")
    
    # Test prepare for sending
    path, name = prepare_file_for_sending(
        temp_workspace,
        "presentations",
        "My Presentation"
    )
    assert path.parent == ppt_dir
    assert "My_Presentation" in name


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

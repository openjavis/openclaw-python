"""
Unit tests for ChannelPlugin base class

Tests the channel plugin interface and basic functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from openclaw.channels.base import (
    ChannelPlugin,
    ChannelCapabilities,
    InboundMessage,
    OutboundMessage,
)


class MockChannel(ChannelPlugin):
    """Mock channel for testing."""
    
    def __init__(self, config: dict):
        self.config = config
        self.started = False
        self.stopped = False
    
    async def start(self):
        """Start the channel."""
        self.started = True
    
    async def stop(self):
        """Stop the channel."""
        self.stopped = True
    
    async def send_message(self, message: OutboundMessage):
        """Send a message."""
        return {"message_id": "123", "ok": True}
    
    def get_capabilities(self) -> ChannelCapabilities:
        """Get channel capabilities."""
        return ChannelCapabilities(
            supports_text=True,
            supports_images=True,
            supports_files=True,
            supports_buttons=True,
        )


class TestChannelCapabilities:
    """Test ChannelCapabilities dataclass."""
    
    def test_default_capabilities(self):
        """Test default capabilities."""
        caps = ChannelCapabilities()
        
        # Check defaults (implementation dependent)
        assert hasattr(caps, "supports_text")
        assert hasattr(caps, "supports_images")
    
    def test_custom_capabilities(self):
        """Test custom capabilities."""
        caps = ChannelCapabilities(
            supports_text=True,
            supports_images=True,
            supports_files=False,
            supports_buttons=True,
        )
        
        assert caps.supports_text is True
        assert caps.supports_images is True
        assert caps.supports_files is False
        assert caps.supports_buttons is True


class TestInboundMessage:
    """Test InboundMessage dataclass."""
    
    def test_create_inbound_message(self):
        """Test creating an inbound message."""
        msg = InboundMessage(
            channel="telegram",
            sender_id="123",
            content="Hello",
            message_id="msg_1",
        )
        
        assert msg.channel == "telegram"
        assert msg.sender_id == "123"
        assert msg.content == "Hello"
        assert msg.message_id == "msg_1"
    
    def test_inbound_message_with_metadata(self):
        """Test inbound message with metadata."""
        msg = InboundMessage(
            channel="telegram",
            sender_id="123",
            content="Hello",
            message_id="msg_1",
            metadata={"chat_type": "private"}
        )
        
        assert msg.metadata == {"chat_type": "private"}


class TestOutboundMessage:
    """Test OutboundMessage dataclass."""
    
    def test_create_outbound_message(self):
        """Test creating an outbound message."""
        msg = OutboundMessage(
            recipient="123",
            content="Hello back",
        )
        
        assert msg.recipient == "123"
        assert msg.content == "Hello back"
    
    def test_outbound_with_images(self):
        """Test outbound message with images."""
        msg = OutboundMessage(
            recipient="123",
            content="Check this out",
            images=["image1.png", "image2.png"]
        )
        
        assert msg.images == ["image1.png", "image2.png"]


class TestChannelPluginLifecycle:
    """Test channel plugin lifecycle."""
    
    @pytest.mark.asyncio
    async def test_start_channel(self):
        """Test starting a channel."""
        channel = MockChannel(config={})
        
        await channel.start()
        
        assert channel.started is True
    
    @pytest.mark.asyncio
    async def test_stop_channel(self):
        """Test stopping a channel."""
        channel = MockChannel(config={})
        
        await channel.stop()
        
        assert channel.stopped is True
    
    @pytest.mark.asyncio
    async def test_start_stop_cycle(self):
        """Test full start/stop cycle."""
        channel = MockChannel(config={})
        
        await channel.start()
        assert channel.started is True
        
        await channel.stop()
        assert channel.stopped is True


class TestChannelMessaging:
    """Test channel messaging functionality."""
    
    @pytest.mark.asyncio
    async def test_send_message(self):
        """Test sending a message."""
        channel = MockChannel(config={})
        message = OutboundMessage(recipient="123", content="Test")
        
        result = await channel.send_message(message)
        
        assert result["ok"] is True
        assert "message_id" in result
    
    def test_get_capabilities(self):
        """Test getting channel capabilities."""
        channel = MockChannel(config={})
        
        caps = channel.get_capabilities()
        
        assert isinstance(caps, ChannelCapabilities)
        assert caps.supports_text is True


class TestChannelConfiguration:
    """Test channel configuration."""
    
    def test_channel_receives_config(self):
        """Test that channel receives configuration."""
        config = {"botToken": "test_token", "enabled": True}
        channel = MockChannel(config=config)
        
        assert channel.config == config
        assert channel.config["botToken"] == "test_token"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

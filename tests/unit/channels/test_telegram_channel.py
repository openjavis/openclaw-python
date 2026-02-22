"""Unit tests for Telegram channel"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from openclaw.channels.telegram.channel import TelegramChannel


class TestTelegramChannel:
    """Test Telegram channel"""

    def test_create_channel(self):
        """Test creating Telegram channel"""
        channel = TelegramChannel(bot_token="test-token")
        assert channel is not None
        assert channel.bot_token == "test-token"

    def test_create_channel_without_token(self):
        """Test creating channel without token raises ValueError"""
        with pytest.raises(ValueError):
            TelegramChannel(bot_token="")

    @pytest.mark.asyncio
    async def test_send_message(self):
        """Test sending message"""
        channel = TelegramChannel(bot_token="test-token")

        with patch.object(channel, "_make_api_call", new_callable=AsyncMock) as mock_call:
            # _make_api_call returns the extracted "result" dict
            mock_call.return_value = {"message_id": 123}

            result = await channel.send_message(
                chat_id="12345",
                text="Test message"
            )

            assert result is not None
            assert "message_id" in result

    @pytest.mark.asyncio
    async def test_send_message_failure(self):
        """Test sending message failure"""
        channel = TelegramChannel(bot_token="test-token")

        with patch.object(channel, "_make_api_call", new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = Exception("API Error")

            with pytest.raises(Exception):
                await channel.send_message(
                    chat_id="12345",
                    text="Test"
                )

    @pytest.mark.asyncio
    async def test_send_photo(self):
        """Test sending photo via _make_api_call"""
        channel = TelegramChannel(bot_token="test-token")

        with patch.object(channel, "_make_api_call", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {"message_id": 124}

            result = await channel.send_photo(
                chat_id="12345",
                photo="https://example.com/image.jpg"
            )

            assert result is not None


class TestTelegramMessageHandling:
    """Test Telegram message handling"""

    def test_parse_message(self):
        """Test parsing Telegram message"""
        channel = TelegramChannel(bot_token="test-token")

        telegram_message = {
            "message_id": 123,
            "from": {"id": 12345, "first_name": "John"},
            "chat": {"id": 12345, "type": "private"},
            "text": "Hello",
            "date": 1234567890
        }

        parsed = channel.parse_message(telegram_message)

        assert parsed is not None
        assert parsed["text"] == "Hello"
        assert parsed["user_id"] == "12345"

    def test_parse_command(self):
        """Test parsing command"""
        channel = TelegramChannel(bot_token="test-token")

        telegram_message = {
            "message_id": 123,
            "from": {"id": 12345, "first_name": "John"},
            "chat": {"id": 12345, "type": "private"},
            "text": "/start",
            "entities": [{"type": "bot_command", "offset": 0, "length": 6}],
            "date": 1234567890
        }

        parsed = channel.parse_message(telegram_message)

        assert parsed is not None
        assert parsed["text"] == "/start"
        assert parsed.get("is_command", False)


def test_telegram_channel_imports():
    """Test that Telegram channel can be imported"""
    try:
        from openclaw.channels.telegram import TelegramChannel
        assert TelegramChannel is not None
    except ImportError as e:
        pytest.fail(f"Failed to import TelegramChannel: {e}")

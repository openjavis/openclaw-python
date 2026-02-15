"""Unit tests for openclaw.telegram.send module.

Tests core message sending functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from openclaw.telegram.send import (
    normalize_chat_id,
    normalize_message_id,
    build_inline_keyboard,
    send_message_telegram,
    react_message_telegram,
    delete_message_telegram,
    edit_message_telegram,
    send_sticker_telegram,
    send_media_group_telegram,
    TelegramSendOptions,
)


class TestNormalizeChatId:
    """Test chat ID normalization."""
    
    def test_numeric_chat_id(self):
        """Test numeric chat ID."""
        assert normalize_chat_id("123456") == "123456"
        assert normalize_chat_id("-100123456") == "-100123456"
    
    def test_username_with_at(self):
        """Test username with @ prefix."""
        assert normalize_chat_id("@username") == "@username"
    
    def test_username_without_at(self):
        """Test username without @ (should add it)."""
        assert normalize_chat_id("username") == "@username"
    
    def test_telegram_prefix_removal(self):
        """Test removal of telegram: prefix."""
        assert normalize_chat_id("telegram:123456") == "123456"
        assert normalize_chat_id("telegram:group:-100123") == "-100123"
    
    def test_tme_link(self):
        """Test t.me link parsing."""
        assert normalize_chat_id("https://t.me/username") == "@username"
        assert normalize_chat_id("t.me/username") == "@username"
    
    def test_empty_chat_id_raises(self):
        """Test empty chat ID raises ValueError."""
        with pytest.raises(ValueError, match="Recipient is required"):
            normalize_chat_id("")
        with pytest.raises(ValueError, match="Recipient is required"):
            normalize_chat_id("   ")


class TestNormalizeMessageId:
    """Test message ID normalization."""
    
    def test_integer_message_id(self):
        """Test integer message ID."""
        assert normalize_message_id(12345) == 12345
    
    def test_string_message_id(self):
        """Test string message ID."""
        assert normalize_message_id("12345") == 12345
    
    def test_invalid_message_id_raises(self):
        """Test invalid message ID raises ValueError."""
        with pytest.raises(ValueError, match="Message ID is required"):
            normalize_message_id("")
        with pytest.raises(ValueError, match="Invalid message ID"):
            normalize_message_id("abc")


class TestBuildInlineKeyboard:
    """Test inline keyboard building."""
    
    def test_empty_buttons(self):
        """Test empty buttons returns None."""
        assert build_inline_keyboard(None) is None
        assert build_inline_keyboard([]) is None
    
    def test_single_button(self):
        """Test single button."""
        buttons = [[{"text": "Test", "callback_data": "test_cb"}]]
        markup = build_inline_keyboard(buttons)
        
        assert markup is not None
        assert len(markup.inline_keyboard) == 1
        assert len(markup.inline_keyboard[0]) == 1
        assert markup.inline_keyboard[0][0].text == "Test"
        assert markup.inline_keyboard[0][0].callback_data == "test_cb"
    
    def test_multiple_rows(self):
        """Test multiple button rows."""
        buttons = [
            [{"text": "Button 1", "callback_data": "cb1"}],
            [{"text": "Button 2", "callback_data": "cb2"}],
        ]
        markup = build_inline_keyboard(buttons)
        
        assert markup is not None
        assert len(markup.inline_keyboard) == 2
    
    def test_invalid_buttons_filtered(self):
        """Test invalid buttons are filtered out."""
        buttons = [
            [
                {"text": "Valid", "callback_data": "valid"},
                {"text": "Missing callback"},  # Invalid
                {"callback_data": "missing_text"},  # Invalid
            ]
        ]
        markup = build_inline_keyboard(buttons)
        
        assert markup is not None
        assert len(markup.inline_keyboard[0]) == 1
    
    def test_callback_data_too_long(self):
        """Test callback data exceeding 64 bytes is filtered."""
        long_data = "x" * 65
        buttons = [[{"text": "Test", "callback_data": long_data}]]
        markup = build_inline_keyboard(buttons)
        
        # Should be filtered out due to length
        assert markup is None


class TestSendMessageTelegram:
    """Test send_message_telegram function."""
    
    @pytest.mark.asyncio
    async def test_send_text_message(self):
        """Test sending a text message."""
        with patch("openclaw.telegram.send.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            
            mock_result = MagicMock()
            mock_result.message_id = 123
            mock_result.chat_id = 456
            mock_bot.send_message = AsyncMock(return_value=mock_result)
            
            config = {
                "channels": {
                    "telegram": {
                        "botToken": "test_token"
                    }
                }
            }
            
            opts = TelegramSendOptions(text_mode="html")
            result = await send_message_telegram(
                to="123456",
                text="Hello World",
                opts=opts,
                config=config
            )
            
            assert result.message_id == "123"
            assert result.chat_id == "456"
            mock_bot.send_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_with_buttons(self):
        """Test sending message with inline keyboard."""
        with patch("openclaw.telegram.send.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            
            mock_result = MagicMock()
            mock_result.message_id = 123
            mock_result.chat_id = 456
            mock_bot.send_message = AsyncMock(return_value=mock_result)
            
            config = {"channels": {"telegram": {"botToken": "test_token"}}}
            
            buttons = [[{"text": "Click me", "callback_data": "action_1"}]]
            opts = TelegramSendOptions(buttons=buttons)
            
            result = await send_message_telegram(
                to="123456",
                text="Choose:",
                opts=opts,
                config=config
            )
            
            assert result.message_id == "123"
            # Verify reply_markup was passed
            call_kwargs = mock_bot.send_message.call_args[1]
            assert "reply_markup" in call_kwargs
    
    @pytest.mark.asyncio
    async def test_send_with_thread_reply(self):
        """Test sending message with thread reply."""
        with patch("openclaw.telegram.send.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            
            mock_result = MagicMock()
            mock_result.message_id = 123
            mock_result.chat_id = 456
            mock_bot.send_message = AsyncMock(return_value=mock_result)
            
            config = {"channels": {"telegram": {"botToken": "test_token"}}}
            
            opts = TelegramSendOptions(
                reply_to_message_id=100,
                message_thread_id=50
            )
            
            result = await send_message_telegram(
                to="123456",
                text="Reply",
                opts=opts,
                config=config
            )
            
            call_kwargs = mock_bot.send_message.call_args[1]
            assert "reply_to_message_id" in call_kwargs or "reply_parameters" in call_kwargs
            assert "message_thread_id" in call_kwargs


class TestReactMessageTelegram:
    """Test react_message_telegram function."""
    
    @pytest.mark.asyncio
    async def test_add_reaction(self):
        """Test adding a reaction."""
        with patch("openclaw.telegram.send.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_bot.set_message_reaction = AsyncMock()
            
            config = {"channels": {"telegram": {"botToken": "test_token"}}}
            
            result = await react_message_telegram(
                chat_id="123456",
                message_id="100",
                emoji="👍",
                config=config
            )
            
            assert result["ok"] is True
            mock_bot.set_message_reaction.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_remove_reaction(self):
        """Test removing a reaction."""
        from openclaw.telegram.send import TelegramReactionOptions
        
        with patch("openclaw.telegram.send.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_bot.set_message_reaction = AsyncMock()
            
            config = {"channels": {"telegram": {"botToken": "test_token"}}}
            opts = TelegramReactionOptions(remove=True)
            
            result = await react_message_telegram(
                chat_id="123456",
                message_id="100",
                emoji="👍",
                opts=opts,
                config=config
            )
            
            assert result["ok"] is True
            # Should call with empty reactions list
            call_args = mock_bot.set_message_reaction.call_args
            assert call_args[1]["reaction"] == []


class TestDeleteMessageTelegram:
    """Test delete_message_telegram function."""
    
    @pytest.mark.asyncio
    async def test_delete_message(self):
        """Test deleting a message."""
        with patch("openclaw.telegram.send.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_bot.delete_message = AsyncMock()
            
            config = {"channels": {"telegram": {"botToken": "test_token"}}}
            
            result = await delete_message_telegram(
                chat_id="123456",
                message_id="100",
                config=config
            )
            
            assert result["ok"] is True
            mock_bot.delete_message.assert_called_once()


class TestEditMessageTelegram:
    """Test edit_message_telegram function."""
    
    @pytest.mark.asyncio
    async def test_edit_message_text(self):
        """Test editing message text."""
        with patch("openclaw.telegram.send.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_bot.edit_message_text = AsyncMock()
            
            config = {"channels": {"telegram": {"botToken": "test_token"}}}
            
            result = await edit_message_telegram(
                chat_id="123456",
                message_id="100",
                text="Updated text",
                config=config
            )
            
            assert result["ok"] is True
            assert result["message_id"] == "100"
            mock_bot.edit_message_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_edit_with_buttons(self):
        """Test editing message with new buttons."""
        from openclaw.telegram.send import TelegramEditOptions
        
        with patch("openclaw.telegram.send.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_bot.edit_message_text = AsyncMock()
            
            config = {"channels": {"telegram": {"botToken": "test_token"}}}
            buttons = [[{"text": "New Button", "callback_data": "new_action"}]]
            opts = TelegramEditOptions(buttons=buttons)
            
            result = await edit_message_telegram(
                chat_id="123456",
                message_id="100",
                text="Updated",
                opts=opts,
                config=config
            )
            
            call_kwargs = mock_bot.edit_message_text.call_args[1]
            assert "reply_markup" in call_kwargs


class TestSendStickerTelegram:
    """Test send_sticker_telegram function."""
    
    @pytest.mark.asyncio
    async def test_send_sticker(self):
        """Test sending a sticker."""
        with patch("openclaw.telegram.send.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            
            mock_result = MagicMock()
            mock_result.message_id = 123
            mock_result.chat_id = 456
            mock_bot.send_sticker = AsyncMock(return_value=mock_result)
            
            config = {"channels": {"telegram": {"botToken": "test_token"}}}
            
            result = await send_sticker_telegram(
                to="123456",
                file_id="sticker_file_id_123",
                config=config
            )
            
            assert result.message_id == "123"
            assert result.chat_id == "456"
            mock_bot.send_sticker.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_sticker_invalid_file_id(self):
        """Test sending sticker with empty file_id raises error."""
        config = {"channels": {"telegram": {"botToken": "test_token"}}}
        
        with pytest.raises(ValueError, match="file_id is required"):
            await send_sticker_telegram(
                to="123456",
                file_id="",
                config=config
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

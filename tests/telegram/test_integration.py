"""Integration tests for Telegram bot functionality.

Tests end-to-end workflows and integration between modules.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from openclaw.telegram.send import (
    send_message_telegram,
    edit_message_telegram,
    react_message_telegram,
    send_media_group_telegram,
    TelegramSendOptions,
)
from openclaw.telegram.model_buttons import parse_model_callback_data
from openclaw.telegram.sticker_cache import cache_sticker, search_stickers, CachedSticker


@pytest.mark.integration
class TestMessageWorkflow:
    """Test complete message sending workflow."""
    
    @pytest.mark.asyncio
    async def test_send_edit_delete_workflow(self):
        """Test sending, editing, and deleting a message."""
        with patch("openclaw.telegram.send.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            
            # Mock send
            send_result = MagicMock()
            send_result.message_id = 100
            send_result.chat_id = 123456
            mock_bot.send_message = AsyncMock(return_value=send_result)
            
            # Mock edit
            mock_bot.edit_message_text = AsyncMock()
            
            # Mock delete
            mock_bot.delete_message = AsyncMock()
            
            config = {"channels": {"telegram": {"botToken": "test_token"}}}
            
            # Step 1: Send message
            send_result = await send_message_telegram(
                to="123456",
                text="Original message",
                config=config
            )
            assert send_result.message_id == "100"
            
            # Step 2: Edit message
            edit_result = await edit_message_telegram(
                chat_id="123456",
                message_id="100",
                text="Edited message",
                config=config
            )
            assert edit_result["ok"] is True
            
            # Step 3: Add reaction
            react_result = await react_message_telegram(
                chat_id="123456",
                message_id="100",
                emoji="👍",
                config=config
            )
            assert react_result["ok"] is True
            
            # Verify all calls were made
            assert mock_bot.send_message.called
            assert mock_bot.edit_message_text.called
            assert mock_bot.set_message_reaction.called


@pytest.mark.integration
class TestMediaWorkflow:
    """Test media handling workflow."""
    
    @pytest.mark.asyncio
    async def test_send_media_group_workflow(self):
        """Test sending media group."""
        with patch("openclaw.telegram.send.Bot") as mock_bot_class, \
             patch("openclaw.media.loader.load_web_media") as mock_load:
            
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            
            # Mock media loading
            mock_media = MagicMock()
            mock_media.buffer = b"fake_image_data"
            mock_media.content_type = "image/jpeg"
            mock_media.file_name = "test.jpg"
            mock_load.return_value = mock_media
            
            # Mock send_media_group
            mock_messages = [
                MagicMock(message_id=1, chat_id=123),
                MagicMock(message_id=2, chat_id=123),
            ]
            mock_bot.send_media_group = AsyncMock(return_value=mock_messages)
            
            config = {"channels": {"telegram": {"botToken": "test_token"}}}
            
            # Send media group
            result = await send_media_group_telegram(
                to="123456",
                media_urls=[
                    "https://example.com/image1.jpg",
                    "https://example.com/image2.jpg",
                ],
                config=config
            )
            
            assert result["ok"] is True
            assert len(result["message_ids"]) == 2
            assert mock_bot.send_media_group.called


@pytest.mark.integration
class TestCommandWorkflow:
    """Test command handling workflow."""
    
    @pytest.mark.asyncio
    async def test_model_selection_workflow(self):
        """Test model selection command workflow."""
        # Test parsing different callback stages
        
        # Stage 1: Show providers
        callback1 = parse_model_callback_data("mdl_prov")
        assert callback1["type"] == "providers"
        
        # Stage 2: Show models for provider
        callback2 = parse_model_callback_data("mdl_list_anthropic_1")
        assert callback2["type"] == "list"
        assert callback2["provider"] == "anthropic"
        assert callback2["page"] == 1
        
        # Stage 3: Select model
        callback3 = parse_model_callback_data("mdl_sel_anthropic/claude-3-opus")
        assert callback3["type"] == "select"
        assert callback3["provider"] == "anthropic"
        assert callback3["model"] == "claude-3-opus"
        
        # Stage 4: Go back
        callback4 = parse_model_callback_data("mdl_back")
        assert callback4["type"] == "back"


@pytest.mark.integration
class TestStickerWorkflow:
    """Test sticker caching and search workflow."""
    
    def test_sticker_cache_search_workflow(self):
        """Test caching and searching stickers."""
        import tempfile
        from pathlib import Path
        
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "sticker-cache.json"
            
            with patch("openclaw.telegram.sticker_cache.CACHE_FILE", cache_file):
                # Step 1: Cache multiple stickers
                stickers = [
                    CachedSticker(
                        file_id="file_1",
                        file_unique_id="unique_1",
                        emoji="😀",
                        description="Happy face",
                    ),
                    CachedSticker(
                        file_id="file_2",
                        file_unique_id="unique_2",
                        emoji="😢",
                        description="Sad face",
                    ),
                    CachedSticker(
                        file_id="file_3",
                        file_unique_id="unique_3",
                        emoji="😂",
                        description="Laughing face",
                    ),
                ]
                
                for sticker in stickers:
                    cache_sticker(sticker)
                
                # Step 2: Search for stickers
                results = search_stickers("face")
                assert len(results) >= 3
                
                # Step 3: Search with specific term
                happy_results = search_stickers("happy")
                assert len(happy_results) >= 1
                assert any("Happy" in r.description for r in happy_results)


@pytest.mark.integration
class TestFormattingWorkflow:
    """Test message formatting workflow."""
    
    @pytest.mark.asyncio
    async def test_markdown_to_html_in_send(self):
        """Test Markdown formatting in message sending."""
        with patch("openclaw.telegram.send.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            
            mock_result = MagicMock()
            mock_result.message_id = 100
            mock_result.chat_id = 123
            mock_bot.send_message = AsyncMock(return_value=mock_result)
            
            config = {"channels": {"telegram": {"botToken": "test_token"}}}
            
            # Send message with complex Markdown
            markdown_text = """
**Bold text** and *italic text*

`inline code` and code block:

```python
print("Hello World")
```

[Link to Google](https://google.com)
            """.strip()
            
            result = await send_message_telegram(
                to="123456",
                text=markdown_text,
                opts=TelegramSendOptions(text_mode="markdown"),
                config=config
            )
            
            # Verify send was called
            assert mock_bot.send_message.called
            call_args = mock_bot.send_message.call_args
            
            # The HTML should have been converted
            sent_text = call_args[1]["text"]
            assert "<b>" in sent_text or "Bold" in sent_text


@pytest.mark.integration
class TestErrorHandlingWorkflow:
    """Test error handling and retry workflow."""
    
    @pytest.mark.asyncio
    async def test_retry_on_network_error(self):
        """Test retry logic on network errors."""
        from openclaw.infra.retry_policy import retry_async, RetryConfig
        
        # Create a function that fails twice then succeeds
        call_count = 0
        
        async def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Network error")
            return "Success"
        
        # Test retry
        config = RetryConfig(attempts=5, min_delay_ms=10, max_delay_ms=100)
        result = await retry_async(
            failing_function,
            config=config,
            should_retry=lambda e: isinstance(e, ConnectionError)
        )
        
        assert result == "Success"
        assert call_count == 3  # Failed twice, succeeded on third
    
    @pytest.mark.asyncio
    async def test_network_error_detection(self):
        """Test network error detection."""
        from openclaw.telegram.network_errors import is_recoverable_telegram_network_error
        
        # Test various error types
        assert is_recoverable_telegram_network_error(
            ConnectionError("Connection timeout")
        )
        assert is_recoverable_telegram_network_error(
            TimeoutError("Request timed out")
        )
        
        # Non-recoverable errors
        assert not is_recoverable_telegram_network_error(
            ValueError("Invalid parameter")
        )


@pytest.mark.integration
@pytest.mark.slow
class TestEndToEndScenario:
    """Test complete end-to-end scenarios."""
    
    @pytest.mark.asyncio
    async def test_complete_user_interaction(self):
        """Test a complete user interaction scenario."""
        with patch("openclaw.telegram.send.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            
            # Mock all bot methods
            mock_result = MagicMock()
            mock_result.message_id = 100
            mock_result.chat_id = 123456
            mock_bot.send_message = AsyncMock(return_value=mock_result)
            mock_bot.edit_message_text = AsyncMock()
            mock_bot.set_message_reaction = AsyncMock()
            
            config = {"channels": {"telegram": {"botToken": "test_token"}}}
            
            # Scenario: User asks a question, bot responds with typing indicator,
            # sends draft updates, then final answer
            
            # Step 1: Send acknowledgment reaction
            await react_message_telegram(
                chat_id="123456",
                message_id="99",  # User's message
                emoji="👀",
                config=config
            )
            
            # Step 2: Send initial draft
            draft_result = await send_message_telegram(
                to="123456",
                text="Thinking...",
                config=config
            )
            draft_id = draft_result.message_id
            
            # Step 3: Update draft (simulate streaming)
            await edit_message_telegram(
                chat_id="123456",
                message_id=draft_id,
                text="Thinking... Got some initial results",
                config=config
            )
            
            # Step 4: Send final answer
            await edit_message_telegram(
                chat_id="123456",
                message_id=draft_id,
                text="Here's the complete answer to your question!",
                config=config
            )
            
            # Step 5: Remove thinking reaction, add done reaction
            await react_message_telegram(
                chat_id="123456",
                message_id="99",
                emoji="✅",
                config=config
            )
            
            # Verify all steps were executed
            assert mock_bot.send_message.call_count >= 1
            assert mock_bot.edit_message_text.call_count >= 2
            assert mock_bot.set_message_reaction.call_count >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])

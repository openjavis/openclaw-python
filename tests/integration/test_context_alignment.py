"""
Integration tests for context alignment with TypeScript

Tests end-to-end context loading to verify alignment with TypeScript implementation.
"""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path


class TestContextLoadingFlow:
    """Test complete context loading flow."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_basic_context_flow(self):
        """Test basic context loading flow."""
        from openclaw.agents.context import (
            sanitize_session_history,
            validate_anthropic_turns,
            limit_history_turns,
        )
        
        # Create mock messages
        messages = []
        for i in range(10):
            msg = MagicMock()
            msg.role = "user" if i % 2 == 0 else "assistant"
            msg.content = f"Message {i}"
            messages.append(msg)
        
        # Sanitize
        sanitized = sanitize_session_history(messages)
        assert len(sanitized) > 0
        
        # Validate for Anthropic
        validated = validate_anthropic_turns(sanitized)
        assert len(validated) > 0
        
        # Limit history
        limited = limit_history_turns(validated, limit=3)
        assert len(limited) <= len(validated)
        
        print(f"✓ Context flow: {len(messages)} → {len(sanitized)} → {len(validated)} → {len(limited)}")
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_gemini_validation_flow(self):
        """Test Gemini-specific validation flow."""
        from openclaw.agents.context import (
            sanitize_session_history,
            validate_gemini_turns,
        )
        
        # Create messages with consecutive assistant messages
        messages = []
        msg1 = MagicMock()
        msg1.role = "user"
        msg1.content = "Hello"
        messages.append(msg1)
        
        msg2 = MagicMock()
        msg2.role = "assistant"
        msg2.content = "Hi"
        messages.append(msg2)
        
        msg3 = MagicMock()
        msg3.role = "assistant"
        msg3.content = "How can I help?"
        messages.append(msg3)
        
        # Validate
        validated = validate_gemini_turns(messages)
        
        # Should merge consecutive assistant messages
        assert len(validated) == 2  # user + merged assistant
        print("✓ Gemini validation merged consecutive assistant messages")
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_history_limit_from_config(self):
        """Test history limiting from config."""
        from openclaw.agents.context import get_dm_history_limit_from_session_key
        
        config = {
            "channels": {
                "telegram": {
                    "dmHistoryLimit": 25,
                    "dms": {
                        "user123": {
                            "historyLimit": 100
                        }
                    }
                }
            }
        }
        
        # Test default limit
        limit1 = get_dm_history_limit_from_session_key(
            "agent:main:telegram:dm:user456",
            config
        )
        assert limit1 == 25
        
        # Test per-DM override
        limit2 = get_dm_history_limit_from_session_key(
            "agent:main:telegram:dm:user123",
            config
        )
        assert limit2 == 100
        
        print("✓ History limits correctly resolved from config")


class TestImageInjectionFlow:
    """Test history image injection flow."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_image_injection_workflow(self):
        """Test complete image injection workflow."""
        from openclaw.agents.context import inject_history_images_into_messages
        
        # Create messages
        messages = []
        msg1 = MagicMock()
        msg1.role = "user"
        msg1.content = "Look at this image"
        messages.append(msg1)
        
        msg2 = MagicMock()
        msg2.role = "assistant"
        msg2.content = "I see it"
        messages.append(msg2)
        
        # Inject images
        history_images = {
            0: [{"type": "image", "source": {"type": "base64", "data": "fake_data"}}]
        }
        
        modified = inject_history_images_into_messages(messages, history_images)
        
        assert modified is True
        assert isinstance(messages[0].content, list)
        print("✓ Images successfully injected into history messages")


class TestProviderSpecificValidation:
    """Test provider-specific message validation."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_anthropic_vs_gemini_validation(self):
        """Test that Anthropic and Gemini validations differ appropriately."""
        from openclaw.agents.context import (
            validate_anthropic_turns,
            validate_gemini_turns,
        )
        
        # Create scenario with both consecutive users and assistants
        messages = []
        
        msg1 = MagicMock()
        msg1.role = "user"
        msg1.content = "Hello"
        messages.append(msg1)
        
        msg2 = MagicMock()
        msg2.role = "user"
        msg2.content = "Are you there?"
        messages.append(msg2)
        
        msg3 = MagicMock()
        msg3.role = "assistant"
        msg3.content = "Yes"
        messages.append(msg3)
        
        msg4 = MagicMock()
        msg4.role = "assistant"
        msg4.content = "I'm here"
        messages.append(msg4)
        
        # Anthropic merges consecutive users
        anthropic_result = validate_anthropic_turns(messages)
        # Should have: merged_user, asst, asst
        assert len(anthropic_result) == 3
        
        # Gemini merges consecutive assistants
        gemini_result = validate_gemini_turns(messages)
        # Should have: user, user, merged_asst
        assert len(gemini_result) == 3
        
        print("✓ Provider-specific validations work differently as expected")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])

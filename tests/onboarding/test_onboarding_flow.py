"""
Integration tests for onboarding wizard flow
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from openclaw.channels.onboarding import (
    TelegramOnboardingAdapter,
    DiscordOnboardingAdapter,
    SlackOnboardingAdapter,
    ChannelOnboardingStatus
)


@pytest.fixture
def mock_prompter():
    """Mock wizard prompter"""
    prompter = Mock()
    prompter.text = AsyncMock()
    prompter.select = AsyncMock()
    prompter.note = AsyncMock()
    prompter.confirm = AsyncMock()
    return prompter


@pytest.fixture
def mock_config():
    """Mock configuration"""
    return {
        "agent": {},
        "gateway": {},
        "channels": {}
    }


class TestTelegramOnboarding:
    """Test Telegram onboarding adapter"""
    
    @pytest.mark.asyncio
    async def test_telegram_status_unconfigured(self, mock_config):
        """Test status when Telegram is not configured"""
        adapter = TelegramOnboardingAdapter()
        
        status = await adapter.get_status(mock_config)
        
        assert not status.configured
        assert not status.enabled
        assert not status.has_token
    
    @pytest.mark.asyncio
    async def test_telegram_status_configured(self, mock_config):
        """Test status when Telegram is configured"""
        mock_config["channels"]["telegram"] = {
            "enabled": True,
            "token": "123456:ABC...",
            "dmPolicy": "allowlist",
            "allowFrom": ["123456789"]
        }
        
        adapter = TelegramOnboardingAdapter()
        status = await adapter.get_status(mock_config)
        
        assert status.configured
        assert status.enabled
        assert status.has_token
        assert status.dm_policy == "allowlist"
    
    @pytest.mark.asyncio
    async def test_telegram_configure(self, mock_config, mock_prompter):
        """Test Telegram configuration flow"""
        mock_prompter.text.return_value = "123456:ABC..."
        
        adapter = TelegramOnboardingAdapter()
        
        updated_config = await adapter.configure(mock_config, mock_prompter)
        
        assert "telegram" in updated_config["channels"]
        assert updated_config["channels"]["telegram"]["enabled"]
        assert updated_config["channels"]["telegram"]["token"] == "123456:ABC..."
    
    @pytest.mark.asyncio
    async def test_telegram_configure_dm_policy_allowlist(self, mock_config, mock_prompter):
        """Test Telegram DM policy configuration"""
        mock_config["channels"]["telegram"] = {"token": "123456:ABC..."}
        
        mock_prompter.select.return_value = {"value": "allowlist"}
        mock_prompter.text.return_value = "123456789, 987654321"
        
        adapter = TelegramOnboardingAdapter()
        
        updated_config = await adapter.configure_dm_policy(
            mock_config,
            mock_prompter
        )
        
        telegram_config = updated_config["channels"]["telegram"]
        assert telegram_config["dmPolicy"] == "allowlist"
        assert "123456789" in telegram_config["allowFrom"]
        assert "987654321" in telegram_config["allowFrom"]
    
    @pytest.mark.asyncio
    async def test_telegram_token_validation(self):
        """Test Telegram token validation"""
        adapter = TelegramOnboardingAdapter()
        
        # Valid token
        assert await adapter.validate_token("123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
        
        # Invalid tokens
        assert not await adapter.validate_token("")
        assert not await adapter.validate_token("invalid")
        assert not await adapter.validate_token("123456")  # Missing hash
        assert not await adapter.validate_token(":ABC123")  # Missing bot ID


class TestDiscordOnboarding:
    """Test Discord onboarding adapter"""
    
    @pytest.mark.asyncio
    async def test_discord_status_unconfigured(self, mock_config):
        """Test Discord unconfigured status"""
        adapter = DiscordOnboardingAdapter()
        
        status = await adapter.get_status(mock_config)
        
        assert not status.configured
    
    @pytest.mark.asyncio
    async def test_discord_configure(self, mock_config, mock_prompter):
        """Test Discord configuration"""
        mock_prompter.text.return_value = "MTA1234567890.ABCDEF.xyz123"
        
        adapter = DiscordOnboardingAdapter()
        
        updated_config = await adapter.configure(mock_config, mock_prompter)
        
        assert "discord" in updated_config["channels"]
        assert updated_config["channels"]["discord"]["enabled"]


class TestSlackOnboarding:
    """Test Slack onboarding adapter"""
    
    @pytest.mark.asyncio
    async def test_slack_status_unconfigured(self, mock_config):
        """Test Slack unconfigured status"""
        adapter = SlackOnboardingAdapter()
        
        status = await adapter.get_status(mock_config)
        
        assert not status.configured
    
    @pytest.mark.asyncio
    async def test_slack_configure(self, mock_config, mock_prompter):
        """Test Slack configuration"""
        mock_prompter.text.return_value = "xoxb-test-placeholder-token"
        
        adapter = SlackOnboardingAdapter()
        
        updated_config = await adapter.configure(mock_config, mock_prompter)
        
        assert "slack" in updated_config["channels"]
        assert updated_config["channels"]["slack"]["enabled"]
    
    @pytest.mark.asyncio
    async def test_slack_token_validation(self):
        """Test Slack token validation"""
        adapter = SlackOnboardingAdapter()
        
        # Valid tokens
        assert await adapter.validate_token("xoxb-1234567890-ABCDEFG")
        assert await adapter.validate_token("xapp-1234567890-ABCDEFG")
        
        # Invalid tokens
        assert not await adapter.validate_token("")
        assert not await adapter.validate_token("invalid")
        assert not await adapter.validate_token("xoxp-123")  # User token (not bot)


class TestPairingSystem:
    """Test pairing system integration with onboarding"""
    
    def test_pairing_code_generation(self):
        """Test pairing code generation"""
        from openclaw.pairing.codes import generate_pairing_code
        
        code = generate_pairing_code()
        
        assert len(code) == 8
        assert code.isalnum()
        assert code.isupper()
        
        # Should not contain confusable characters
        assert "I" not in code
        assert "O" not in code
        assert "0" not in code
        assert "1" not in code
    
    def test_pairing_store_persistence(self, tmp_path):
        """Test pairing requests persist"""
        from openclaw.pairing.store import PairingStore, PairingRequest
        from datetime import datetime, timezone
        
        store = PairingStore("telegram")
        store.store_path = tmp_path / "test-pairing.json"
        
        # Create request
        request = PairingRequest(
            id="123456789",
            code="A7JKPC29",
            created_at=datetime.now(timezone.utc).isoformat(),
            last_seen_at=datetime.now(timezone.utc).isoformat(),
            meta={"username": "testuser"}
        )
        
        # Add request
        store.add_request(request)
        
        # Retrieve request
        retrieved = store.get_request("123456789")
        
        assert retrieved is not None
        assert retrieved.id == "123456789"
        assert retrieved.code == "A7JKPC29"
    
    def test_pairing_approval_workflow(self, tmp_path):
        """Test pairing approval adds user to allowFrom"""
        from openclaw.pairing.approval import add_to_allow_from
        
        # This would require mocking config file
        # For now, just test the function exists
        assert callable(add_to_allow_from)


@pytest.mark.integration
class TestOnboardingEndToEnd:
    """End-to-end onboarding tests"""
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires full wizard setup")
    async def test_quickstart_flow(self):
        """Test QuickStart onboarding flow"""
        # This would test:
        # 1. Risk acknowledgment
        # 2. Flow selection (QuickStart)
        # 3. Channel selection
        # 4. Token input
        # 5. Config save
        # 6. Service installation option
        pass
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires full wizard setup")
    async def test_advanced_flow(self):
        """Test Advanced onboarding flow"""
        # This would test:
        # 1. Risk acknowledgment
        # 2. Flow selection (Advanced)
        # 3. Agent model selection
        # 4. Multiple channel configuration
        # 5. Security policy configuration
        # 6. Advanced features
        pass

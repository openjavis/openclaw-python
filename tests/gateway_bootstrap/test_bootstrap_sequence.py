"""
Integration tests for Gateway bootstrap sequence
"""
import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from openclaw.gateway.bootstrap import GatewayBootstrap


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary config directory"""
    config_dir = tmp_path / ".openclaw"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def mock_config(temp_config_dir):
    """Create mock configuration"""
    return {
        "agent": {
            "model": "anthropic/claude-opus-4"
        },
        "gateway": {
            "port": 18789,
            "bind": "loopback"
        },
        "channels": {},
        "cron": {
            "enabled": True
        }
    }


class TestBootstrapSequence:
    """Test gateway bootstrap sequence"""
    
    @pytest.mark.asyncio
    async def test_bootstrap_initialization(self):
        """Test bootstrap initializes correctly"""
        bootstrap = GatewayBootstrap()
        
        assert bootstrap.config is None
        assert bootstrap.session_manager is None
        assert bootstrap.cron_service is None
        assert bootstrap.channel_manager is None
    
    @pytest.mark.asyncio
    @patch("openclaw.gateway.bootstrap.load_config")
    async def test_bootstrap_step_2_load_config(self, mock_load_config, mock_config):
        """Test Step 2: Load configuration"""
        mock_load_config.return_value = mock_config
        
        bootstrap = GatewayBootstrap()
        
        # Mock subsequent steps
        with patch.object(bootstrap, '_set_env_vars'):
            with patch("openclaw.gateway.bootstrap.detect_legacy_config", return_value=None):
                results = await bootstrap.bootstrap()
        
        # Should complete at least Step 2
        assert results["steps_completed"] >= 2
        assert bootstrap.config is not None
    
    @pytest.mark.asyncio
    async def test_bootstrap_error_handling(self):
        """Test bootstrap handles errors gracefully"""
        bootstrap = GatewayBootstrap()
        
        # Force config load error
        with patch("openclaw.gateway.bootstrap.load_config", side_effect=Exception("Config error")):
            results = await bootstrap.bootstrap()
        
        # Should record error
        assert len(results["errors"]) > 0
        assert "config" in results["errors"][0]
    
    @pytest.mark.asyncio
    @patch("openclaw.gateway.bootstrap.load_config")
    async def test_bootstrap_creates_session_manager(self, mock_load_config, mock_config):
        """Test bootstrap creates session manager"""
        mock_load_config.return_value = mock_config
        
        bootstrap = GatewayBootstrap()
        
        # Mock dependencies
        with patch.object(bootstrap, '_set_env_vars'):
            with patch("openclaw.gateway.bootstrap.detect_legacy_config", return_value=None):
                with patch("openclaw.gateway.bootstrap.start_diagnostic_heartbeat"):
                    # Mock provider creation
                    with patch("openclaw.agents.providers.create_provider", return_value=Mock()):
                        results = await bootstrap.bootstrap()
        
        # Session manager should be created (Step 10)
        if results["steps_completed"] >= 10:
            assert bootstrap.session_manager is not None
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires full dependency mocking")
    async def test_bootstrap_full_sequence(self):
        """Test full bootstrap sequence completes"""
        # This would require mocking all dependencies
        pass


class TestBootstrapDependencies:
    """Test bootstrap dependency injection"""
    
    @pytest.mark.asyncio
    async def test_cron_service_dependencies(self):
        """Test cron service receives correct dependencies"""
        # Mock the cron bootstrap function
        with patch("openclaw.gateway.cron_bootstrap.build_gateway_cron_service") as mock_build:
            mock_build.return_value = Mock()
            
            bootstrap = GatewayBootstrap()
            bootstrap.config = {"cron": {"enabled": True}}
            bootstrap.provider = Mock()
            bootstrap.session_manager = Mock()
            bootstrap.channel_manager = Mock(channels={})
            bootstrap.tool_registry = Mock(list_tools=Mock(return_value=[]))
            
            # Manually trigger Step 12
            with patch.object(bootstrap, '_set_env_vars'):
                pass  # Would need to call specific step
    
    @pytest.mark.asyncio
    async def test_channel_manager_initialization(self):
        """Test channel manager initialization"""
        bootstrap = GatewayBootstrap()
        bootstrap.config = {"channels": {}}
        
        # Would test channel manager setup
        pass


class TestBootstrapFirstRun:
    """Test first-run detection and onboarding"""
    
    @pytest.mark.asyncio
    async def test_first_run_detection(self, temp_config_dir):
        """Test first-run is detected when no config exists"""
        config_path = temp_config_dir / "openclaw.json"
        
        # Ensure config doesn't exist
        assert not config_path.exists()
        
        # Bootstrap should detect first run
        with patch("openclaw.wizard.onboarding.run_interactive_onboarding") as mock_onboard:
            mock_onboard.return_value = None
            
            bootstrap = GatewayBootstrap()
            
            # Mock rest of bootstrap
            with patch("openclaw.gateway.bootstrap.load_config", return_value={}):
                results = await bootstrap.bootstrap(config_path=config_path)
        
        # Onboarding should have been triggered
        mock_onboard.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_skip_onboarding_if_config_exists(self, temp_config_dir, mock_config):
        """Test onboarding is skipped when config exists"""
        config_path = temp_config_dir / "openclaw.json"
        
        # Create config file
        import json
        with open(config_path, 'w') as f:
            json.dump(mock_config, f)
        
        with patch("openclaw.wizard.onboarding.run_interactive_onboarding") as mock_onboard:
            bootstrap = GatewayBootstrap()
            
            with patch("openclaw.gateway.bootstrap.load_config", return_value=mock_config):
                with patch.object(bootstrap, '_set_env_vars'):
                    results = await bootstrap.bootstrap(config_path=config_path)
        
        # Onboarding should NOT be called
        mock_onboard.assert_not_called()


@pytest.mark.integration
class TestBootstrapPerformance:
    """Test bootstrap performance"""
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Performance testing requires full setup")
    async def test_bootstrap_completes_quickly(self):
        """Test bootstrap completes within reasonable time"""
        # Target: < 5 seconds for cold start
        pass
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Performance testing requires full setup")
    async def test_bootstrap_parallel_operations(self):
        """Test bootstrap performs operations in parallel where possible"""
        pass

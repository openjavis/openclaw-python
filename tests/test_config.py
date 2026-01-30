"""Config tests"""

from pathlib import Path

import pytest

from openclaw.config import ClawdbotConfig, load_config


def test_default_config():
    """Test default configuration"""
    config = ClawdbotConfig()

    assert config.gateway is not None
    assert config.gateway.port == 18789
    assert config.gateway.bind == "loopback"

    assert config.agent is not None
    assert config.agent.model is not None


def test_config_validation():
    """Test config validation"""
    config = ClawdbotConfig(
        gateway={"port": 8080}, agent={"model": "anthropic/claude-opus-4-5-20250514"}
    )

    assert config.gateway.port == 8080
    assert config.agent.model == "anthropic/claude-opus-4-5-20250514"


def test_config_serialization():
    """Test config to/from dict"""
    config = ClawdbotConfig()
    config_dict = config.model_dump()

    assert isinstance(config_dict, dict)
    assert "gateway" in config_dict
    assert "agent" in config_dict

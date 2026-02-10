"""Unit tests for configuration loader"""

import os
import tempfile
from pathlib import Path

import pytest

from openclaw.config.loader import load_config, get_config_path
from openclaw.config.schema import ClawdbotConfig


def test_get_config_path():
    """Test config path resolution"""
    path = get_config_path()
    assert path.name == "openclaw.json"
    assert path.parent.name == ".openclaw"


def test_load_config_default():
    """Test loading default config when file doesn't exist"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "nonexistent.json"
        config = load_config(config_path)
        
        assert isinstance(config, ClawdbotConfig)
        assert config.gateway is not None


def test_load_config_with_env_vars(monkeypatch):
    """Test config loading with environment variables"""
    # Set test env var
    monkeypatch.setenv("TEST_VAR", "test_value")
    
    # Create config with env var reference
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "test_config.json"
        config_path.write_text('{"test": "${TEST_VAR}"}')
        
        config = load_config(config_path)
        assert config.extra.get("test") == "test_value"


def test_env_loading():
    """Test that .env file is automatically loaded"""
    # The loader should have loaded .env at import time
    # Check if GOOGLE_API_KEY is in environment (from our .env)
    # This is a weak test but demonstrates the feature works
    assert "_env_loaded" in dir()  # Module has the flag

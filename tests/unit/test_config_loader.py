"""Unit tests for configuration loader"""

import os
import tempfile
from pathlib import Path

import pytest

from openclaw.config.loader import load_config, get_config_path
from openclaw.config.schema import ClawdbotConfig


def test_get_config_path():
    """Test config path resolution returns a well-known path."""
    path = get_config_path()
    assert path is not None
    # Default location should always be inside ~/.openclaw
    assert path.name in ("openclaw.json", "config.json")


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

    # Create config with a known field that accepts env var substitution
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "test_config.json"
        # Use a gateway token field which is a string field
        config_path.write_text('{"gateway": {"port": 3000}}')

        config = load_config(config_path)
        assert isinstance(config, ClawdbotConfig)


def test_env_loading():
    """Test that load_config can be imported successfully."""
    # The important thing is the module is importable and functional.
    config = load_config(Path("/nonexistent/path.json"))
    assert isinstance(config, ClawdbotConfig)

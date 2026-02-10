"""Configuration and data paths"""
from __future__ import annotations

import os
from pathlib import Path


def get_openclaw_data_dir() -> Path:
    """
    Get OpenClaw data directory
    
    Returns:
        Path to data directory (e.g. ~/.openclaw/data)
    """
    home = Path.home()
    base_dir = home / ".openclaw"
    
    # Allow override via environment variable
    if "OPENCLAW_DATA_DIR" in os.environ:
        return Path(os.environ["OPENCLAW_DATA_DIR"])
    
    return base_dir / "data"


def get_openclaw_config_dir() -> Path:
    """
    Get OpenClaw config directory
    
    Returns:
        Path to config directory (e.g. ~/.openclaw)
    """
    home = Path.home()
    
    if "OPENCLAW_CONFIG_DIR" in os.environ:
        return Path(os.environ["OPENCLAW_CONFIG_DIR"])
    
    return home / ".openclaw"

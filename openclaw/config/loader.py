"""Configuration loading and persistence"""

import json
import os
from pathlib import Path

import pyjson5
from dotenv import load_dotenv

from .env_substitution import resolve_config_env_vars
from .includes import resolve_config_includes, ConfigIncludeError
from .schema import ClawdbotConfig

# Load .env file at module import time
_env_loaded = False
def _ensure_env_loaded():
    """Ensure .env file is loaded"""
    global _env_loaded
    if not _env_loaded:
        # Try to load .env from current directory or parent directories
        env_path = Path.cwd() / ".env"
        if env_path.exists():
            load_dotenv(env_path)
        else:
            # Try workspace root
            workspace_root = Path(__file__).parent.parent.parent
            env_path = workspace_root / ".env"
            if env_path.exists():
                load_dotenv(env_path)
        _env_loaded = True


def get_config_path() -> Path:
    """Get the config file path"""
    config_dir = Path.home() / ".openclaw"
    config_dir.mkdir(exist_ok=True, parents=True)
    return config_dir / "openclaw.json"


def merge_config_dict(base: dict, updates: dict) -> dict:
    """Deep merge configuration dictionaries"""
    result = base.copy()
    
    for key, value in updates.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_config_dict(result[key], value)
        else:
            result[key] = value
    
    return result


def load_config(config_path: Path | None = None) -> ClawdbotConfig:
    """Load configuration from file or return defaults"""
    # Ensure .env is loaded first
    _ensure_env_loaded()
    
    if config_path is None:
        config_path = get_config_path()

    if not config_path.exists():
        # Return default config
        return ClawdbotConfig()

    try:
        with open(config_path, encoding="utf-8") as f:
            # Support JSON5 for comments
            config_data = pyjson5.load(f)
        
        # Resolve @include directives
        try:
            config_data = resolve_config_includes(
                config_data,
                str(config_path),
                read_file=lambda p: Path(p).read_text(encoding="utf-8"),
                parse_json=pyjson5.loads,
            )
        except ConfigIncludeError as e:
            print(f"Warning: Config include error: {e}")
        
        # Resolve environment variable substitutions
        config_data = resolve_config_env_vars(config_data, os.environ)
        
        return ClawdbotConfig(**config_data)
    except Exception as e:
        print(f"Warning: Failed to load config from {config_path}: {e}")
        print("Using default configuration")
        return ClawdbotConfig()


def save_config(config: ClawdbotConfig, config_path: Path | None = None) -> None:
    """Save configuration to file"""
    if config_path is None:
        config_path = get_config_path()

    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert to dict, excluding None values for cleaner output
    config_dict = config.model_dump(exclude_none=True)

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_dict, f, indent=2, ensure_ascii=False)
    
    print(f"Configuration saved to {config_path}")

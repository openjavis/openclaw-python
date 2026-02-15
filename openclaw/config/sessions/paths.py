"""Session store paths."""

from pathlib import Path
from typing import Optional


def get_default_store_path(agent_id: str = "main") -> Path:
    """
    Get default session store path.
    
    Args:
        agent_id: Agent identifier (default: "main"). Supports multi-agent setups.
    
    Returns:
        Path to session store file (store.json)
    """
    # Use .openclaw directory in home
    home = Path.home()
    
    # Agent-specific store path (for multi-agent support)
    if agent_id and agent_id != "main":
        store_dir = home / ".openclaw" / "sessions" / agent_id
    else:
        store_dir = home / ".openclaw" / "sessions"
    
    store_dir.mkdir(parents=True, exist_ok=True)
    return store_dir / "store.json"


def get_store_path(custom_path: Optional[str] = None) -> Path:
    """Get session store path."""
    if custom_path:
        return Path(custom_path)
    return get_default_store_path()


def resolve_session_store_path(config: dict = None) -> Path:
    """Resolve session store path from config.
    
    Args:
        config: Configuration dict
        
    Returns:
        Path to session store
    """
    if config:
        custom_path = config.get("sessions", {}).get("storePath")
        if custom_path:
            return Path(custom_path)
    
    return get_default_store_path()


__all__ = ["get_default_store_path", "get_store_path", "resolve_session_store_path"]

"""
Runtime parameter resolution for system prompt

Collects runtime information and resolves configuration parameters
for use in system prompt construction.
"""

from __future__ import annotations

import logging
import os
import platform
import socket
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def build_system_prompt_params(
    config: dict | None = None,
    workspace_dir: Path | None = None,
    runtime: dict | None = None
) -> dict:
    """
    Build system prompt parameters
    
    Resolves timezone, repo root, and runtime information for use in
    the system prompt builder.
    
    Matches TypeScript buildSystemPromptParams() from system-prompt-params.ts:33-58
    
    Args:
        config: OpenClaw configuration dict
        workspace_dir: Workspace directory
        runtime: Runtime information dict (optional override with keys:
                agent_id, model, channel, capabilities, default_model)
    
    Returns:
        Dict with keys:
        - user_timezone: str (resolved IANA timezone, never None)
        - runtime_info: dict (agent_id, host, os, arch, python_version, model, 
                              default_model, channel, capabilities, repo_root)
        - repo_root: str | None
    """
    # Resolve user timezone from config
    timezone_config = None
    if config and hasattr(config, "agents"):
        if hasattr(config.agents, "defaults"):
            timezone_config = getattr(config.agents.defaults, "userTimezone", None)
    elif isinstance(config, dict):
        timezone_config = config.get("agents", {}).get("defaults", {}).get("userTimezone")
    
    # Use resolve_user_timezone which handles validation and fallbacks
    user_timezone = resolve_user_timezone(timezone_config)
    
    # Get runtime info
    if not runtime:
        runtime = {}
    
    runtime_info = get_runtime_info(
        agent_id=runtime.get("agent_id"),
        model=runtime.get("model"),
        channel=runtime.get("channel"),
        default_model=runtime.get("default_model"),
        capabilities=runtime.get("capabilities"),
    )
    
    # Find repo root
    repo_root = None
    if workspace_dir:
        repo_root = resolve_repo_root(workspace_dir)
    
    if repo_root:
        runtime_info["repo_root"] = str(repo_root)
    
    return {
        "user_timezone": user_timezone,
        "runtime_info": runtime_info,
        "repo_root": str(repo_root) if repo_root else None
    }


def get_runtime_info(
    agent_id: str | None = None,
    model: str | None = None,
    channel: str | None = None,
    default_model: str | None = None,
    capabilities: list[str] | None = None,
) -> dict:
    """
    Collect runtime information
    
    Args:
        agent_id: Agent identifier (optional)
        model: Model name (optional)
        channel: Channel name (optional)
        default_model: Default model name (optional)
        capabilities: List of capabilities (optional)
    
    Returns:
        Dict with runtime information:
        - agent_id: str | None
        - host: str
        - os: str
        - arch: str
        - python_version: str
        - model: str | None
        - default_model: str | None
        - channel: str | None
        - capabilities: list[str] | None
    """
    # Get hostname
    try:
        host = socket.gethostname()
    except Exception:
        host = "unknown"
    
    # Get OS and architecture
    os_name = platform.system().lower()
    arch = platform.machine().lower()
    
    # Get Python version
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    
    result = {
        "agent_id": agent_id,
        "host": host,
        "os": os_name,
        "arch": arch,
        "python_version": python_version,
        "model": model,
        "channel": channel,
    }
    
    # Add optional fields if provided
    if default_model:
        result["default_model"] = default_model
    if capabilities:
        result["capabilities"] = capabilities
    
    return result


def resolve_repo_root(start_dir: Path) -> Path | None:
    """
    Find git repository root by walking up directories
    
    Args:
        start_dir: Directory to start searching from
    
    Returns:
        Path to git root, or None if not found
    """
    current = start_dir.resolve()
    
    # Walk up to 12 levels
    for _ in range(12):
        git_path = current / ".git"
        
        try:
            if git_path.exists() and (git_path.is_dir() or git_path.is_file()):
                logger.debug(f"Found git root: {current}")
                return current
        except Exception as e:
            logger.debug(f"Error checking .git at {current}: {e}")
        
        # Move to parent
        parent = current.parent
        if parent == current:
            # Reached filesystem root
            break
        current = parent
    
    logger.debug(f"No git root found starting from {start_dir}")
    return None


def resolve_user_timezone(timezone_config: str | None = None) -> str:
    """
    Resolve user timezone from config or system
    
    Matches TypeScript resolveUserTimezone() from date-time.ts:8-20
    Returns IANA timezone identifier (e.g., 'America/New_York')
    Falls back to system timezone, then UTC if detection fails
    
    Args:
        timezone_config: Timezone string from config (e.g., "America/New_York")
    
    Returns:
        Resolved IANA timezone string (never None, defaults to "UTC")
    """
    # If configured timezone is provided, validate it
    trimmed = timezone_config.strip() if timezone_config else None
    if trimmed:
        try:
            # Try to validate with zoneinfo (Python 3.9+)
            try:
                from zoneinfo import ZoneInfo
                ZoneInfo(trimmed)
                return trimmed
            except ImportError:
                # Fallback for Python < 3.9 or if zoneinfo not available
                # Just basic validation
                if "/" in trimmed or trimmed == "UTC":
                    return trimmed
        except Exception:
            # Invalid timezone, fall through to auto-detection
            logger.debug(f"Invalid timezone: {trimmed}, falling back to auto-detection")
    
    # Auto-detect system timezone
    try:
        # Try to get IANA timezone from system
        # On Unix-like systems, check TZ environment variable first
        tz_env = os.environ.get('TZ', '').strip()
        if tz_env and "/" in tz_env:
            try:
                from zoneinfo import ZoneInfo
                ZoneInfo(tz_env)
                return tz_env
            except Exception:
                pass
        
        # Try to detect from system configuration
        # This is a best-effort approach
        try:
            import time
            # Try tzname first
            if hasattr(time, 'tzname') and time.tzname and time.tzname[0]:
                # Convert abbreviation to IANA if possible
                # This is imperfect but better than nothing
                tz_abbr = time.tzname[0]
                # Some common mappings
                abbr_map = {
                    'EST': 'America/New_York',
                    'EDT': 'America/New_York',
                    'CST': 'America/Chicago',
                    'CDT': 'America/Chicago',
                    'MST': 'America/Denver',
                    'MDT': 'America/Denver',
                    'PST': 'America/Los_Angeles',
                    'PDT': 'America/Los_Angeles',
                }
                if tz_abbr in abbr_map:
                    return abbr_map[tz_abbr]
        except Exception:
            pass
        
        # Try platform-specific detection
        if platform.system() == 'Darwin':  # macOS
            try:
                import subprocess
                result = subprocess.check_output(
                    ['defaults', 'read', '/Library/Preferences/.GlobalPreferences.plist', 'com.apple.TimeZone'],
                    stderr=subprocess.DEVNULL,
                    timeout=1
                ).decode('utf-8').strip()
                if result and "/" in result:
                    return result
            except Exception:
                pass
        elif platform.system() == 'Linux':
            # Try to read /etc/timezone
            try:
                with open('/etc/timezone', 'r') as f:
                    tz = f.read().strip()
                    if tz and "/" in tz:
                        return tz
            except Exception:
                pass
            
            # Try to resolve /etc/localtime symlink
            try:
                localtime = Path('/etc/localtime')
                if localtime.is_symlink():
                    target = localtime.resolve()
                    # Extract timezone from path like /usr/share/zoneinfo/America/New_York
                    target_str = str(target)
                    if 'zoneinfo/' in target_str:
                        tz = target_str.split('zoneinfo/')[-1]
                        if "/" in tz:
                            return tz
            except Exception:
                pass
    except Exception as e:
        logger.debug(f"Failed to auto-detect timezone: {e}")
    
    # Final fallback to UTC
    return "UTC"

"""
Browser control service.

Starts and manages browser instances and relay servers.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .extension_relay import ChromeExtensionRelay
from .profiles import BrowserProfile, ProfileContext, ProfileManager

logger = logging.getLogger(__name__)


@dataclass
class ResolvedBrowserConfig:
    """Resolved browser configuration"""
    enabled: bool
    profiles: dict[str, BrowserProfile]
    control_port: int
    default_profile: str = "default"


@dataclass
class BrowserServerState:
    """Browser control server state"""
    server: Any
    port: int
    resolved: ResolvedBrowserConfig
    profiles: dict[str, ProfileContext]
    relay: ChromeExtensionRelay | None = None


async def start_browser_control_service_from_config(
    config: dict | None = None
) -> BrowserServerState | None:
    """
    Start browser control service from configuration.
    
    Args:
        config: OpenClaw configuration
        
    Returns:
        BrowserServerState or None if disabled
    """
    if not config:
        return None
    
    browser_config = config.get('browser', {})
    
    # Check if enabled
    if not browser_config.get('enabled', False):
        logger.info("Browser control is disabled")
        return None
    
    # Resolve configuration
    resolved = resolve_browser_config(browser_config, config)
    
    if not resolved.enabled:
        return None
    
    # Start relay for extension profiles
    relay = None
    for profile in resolved.profiles.values():
        if profile.mode == "extension":
            relay = ChromeExtensionRelay()
            await relay.start()
            logger.info(f"Started extension relay on port {relay.port}")
            break
    
    # Create server state
    state = BrowserServerState(
        server=None,  # HTTP server would be added here
        port=resolved.control_port,
        resolved=resolved,
        profiles={},
        relay=relay
    )
    
    logger.info(f"Browser control service started on port {resolved.control_port}")
    
    return state


def resolve_browser_config(
    browser_config: dict,
    openclaw_config: dict
) -> ResolvedBrowserConfig:
    """
    Resolve browser configuration from config dict.
    
    Args:
        browser_config: Browser section of config
        openclaw_config: Full OpenClaw config
        
    Returns:
        Resolved browser configuration
    """
    enabled = browser_config.get('enabled', False)
    control_port = browser_config.get('controlPort', 3110)
    
    # Parse profiles
    profiles = {}
    profiles_config = browser_config.get('profiles', {})
    
    # Default profile
    default_profile_config = profiles_config.get('default', {})
    profiles['default'] = BrowserProfile(
        name='default',
        mode=default_profile_config.get('mode', 'extension'),
        headless=default_profile_config.get('headless', False),
        cdp_port=default_profile_config.get('cdpPort')
    )
    
    # Sandbox profile
    if 'sandbox' in profiles_config:
        sandbox_config = profiles_config['sandbox']
        profiles['sandbox'] = BrowserProfile(
            name='sandbox',
            mode=sandbox_config.get('mode', 'extension'),
            headless=sandbox_config.get('headless', True),
            cdp_port=sandbox_config.get('cdpPort')
        )
    
    # Additional profiles
    for name, profile_config in profiles_config.items():
        if name not in ['default', 'sandbox']:
            profiles[name] = BrowserProfile(
                name=name,
                mode=profile_config.get('mode', 'extension'),
                headless=profile_config.get('headless', False),
                cdp_port=profile_config.get('cdpPort')
            )
    
    return ResolvedBrowserConfig(
        enabled=enabled,
        profiles=profiles,
        control_port=control_port,
        default_profile='default'
    )


async def launch_openclaw_chrome(
    profile: BrowserProfile,
    user_data_dir: Path
) -> Any:
    """
    Launch Chrome process for OpenClaw.
    
    Args:
        profile: Browser profile
        user_data_dir: User data directory
        
    Returns:
        Chrome process handle
    """
    # Build Chrome launch args
    args = [
        f"--remote-debugging-port={profile.cdp_port}" if profile.cdp_port else "",
        f"--user-data-dir={user_data_dir}",
    ]
    
    if profile.headless:
        args.append("--headless=new")
    
    if profile.extension_path:
        args.append(f"--load-extension={profile.extension_path}")
    
    # Add custom args
    args.extend(profile.args)
    
    # Remove empty args
    args = [a for a in args if a]
    
    # Launch Chrome (placeholder - would use subprocess or playwright)
    logger.info(f"Would launch Chrome with args: {args}")
    
    return None


__all__ = [
    "BrowserServerState",
    "ResolvedBrowserConfig",
    "start_browser_control_service_from_config",
    "resolve_browser_config",
    "launch_openclaw_chrome",
]

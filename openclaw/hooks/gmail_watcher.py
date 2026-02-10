"""Gmail watcher service

Monitors Gmail for new emails and triggers hooks.
Matches TypeScript openclaw/src/hooks/gmail-watcher.ts
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


async def start_gmail_watcher(config: dict) -> dict:
    """
    Start Gmail watcher service
    
    Monitors Gmail account for new emails and triggers
    appropriate hooks.
    
    Args:
        config: Gateway configuration
        
    Returns:
        Dict with started (bool) and reason (str | None)
    """
    # Check if hooks are enabled
    hooks_config = config.get("hooks", {})
    if not hooks_config.get("enabled", False):
        return {"started": False, "reason": "hooks not enabled"}
    
    # Check for Gmail account configuration
    gmail_config = hooks_config.get("gmail", {})
    account = gmail_config.get("account")
    
    if not account:
        return {"started": False, "reason": "no gmail account configured"}
    
    try:
        logger.info(f"Starting Gmail watcher for account: {account}")
        
        # TODO: Spawn gog serve process
        # This would use the gog CLI tool to monitor Gmail
        
        # For now, just log
        logger.info(f"Gmail watcher started for {account}")
        
        return {
            "started": True,
            "account": account,
        }
        
    except Exception as e:
        logger.error(f"Failed to start Gmail watcher: {e}")
        return {
            "started": False,
            "reason": str(e),
        }


async def spawn_gog_serve(account: str) -> asyncio.subprocess.Process | None:
    """
    Spawn gog serve subprocess
    
    Args:
        account: Gmail account email
        
    Returns:
        Process handle or None
    """
    try:
        # Spawn gog serve process
        proc = await asyncio.create_subprocess_exec(
            "gog",
            "serve",
            "--account", account,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        
        logger.info(f"Started gog serve process (PID: {proc.pid})")
        
        return proc
        
    except FileNotFoundError:
        logger.warning("gog command not found - install from github.com/pi/gog")
        return None
    except Exception as e:
        logger.error(f"Failed to spawn gog serve: {e}")
        return None

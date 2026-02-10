"""Onboarding wizard

First-run onboarding experience for new users.
Matches TypeScript openclaw/src/wizard/onboarding.ts
"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


async def run_onboarding_wizard(config: dict, workspace_dir: Path) -> dict:
    """
    Run onboarding wizard
    
    Guides new users through initial setup:
    - API key configuration
    - Model selection
    - Channel setup
    - First task
    
    Args:
        config: Gateway configuration
        workspace_dir: Workspace directory
        
    Returns:
        Dict with wizard results
    """
    logger.info("Starting onboarding wizard")
    
    # TODO: Interactive wizard prompts
    # This would guide users through:
    # 1. Setting up LLM API keys
    # 2. Choosing default model
    # 3. Configuring first channel (Telegram, Discord, etc.)
    # 4. Running first agent task
    
    logger.info("Onboarding wizard complete")
    
    return {
        "completed": True,
        "skipped": False,
    }


def is_first_run(workspace_dir: Path) -> bool:
    """
    Check if this is the first run
    
    Args:
        workspace_dir: Workspace directory
        
    Returns:
        True if first run
    """
    marker_file = workspace_dir / ".openclaw" / "onboarding-complete"
    return not marker_file.exists()

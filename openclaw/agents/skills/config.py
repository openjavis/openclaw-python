"""
Skill configuration management.

Handles skill-specific configuration from OpenClaw config.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def get_skill_config(config: dict | None, skill_key: str) -> dict | None:
    """
    Get configuration for a specific skill.
    
    Looks in: config.skills.entries.<skill_key>
    
    Args:
        config: OpenClaw configuration
        skill_key: Skill configuration key
        
    Returns:
        Skill configuration dict or None
    """
    if not config:
        return None
    
    skills_config = config.get('skills', {})
    entries = skills_config.get('entries', {})
    
    return entries.get(skill_key)


def is_skill_enabled(config: dict | None, skill_key: str) -> bool:
    """
    Check if a skill is enabled in configuration.
    
    Default is enabled (True) unless explicitly set to False.
    
    Args:
        config: OpenClaw configuration
        skill_key: Skill configuration key
        
    Returns:
        True if skill is enabled
    """
    skill_config = get_skill_config(config, skill_key)
    
    if skill_config is None:
        return True  # Default enabled
    
    enabled = skill_config.get('enabled')
    if enabled is None:
        return True  # Default enabled
    
    return bool(enabled)


def get_skill_value(config: dict | None, skill_key: str, value_key: str, default: Any = None) -> Any:
    """
    Get a specific value from skill configuration.
    
    Args:
        config: OpenClaw configuration
        skill_key: Skill configuration key
        value_key: Key within skill config
        default: Default value if not found
        
    Returns:
        Configuration value or default
    """
    skill_config = get_skill_config(config, skill_key)
    
    if skill_config is None:
        return default
    
    return skill_config.get(value_key, default)


__all__ = [
    "get_skill_config",
    "is_skill_enabled",
    "get_skill_value",
]

"""
Skill eligibility checking.

Determines whether a skill should be included based on:
- Configuration (enabled/disabled)
- Platform requirements (os)
- Binary requirements (bins, anyBins)
- Environment variable requirements (env)
- Config path requirements (config)
"""
from __future__ import annotations

import logging
import platform
import shutil
from typing import Any

from .types import SkillEntry, SkillEligibilityContext

logger = logging.getLogger(__name__)


def should_include_skill(
    entry: SkillEntry,
    config: dict | None,
    eligibility: SkillEligibilityContext
) -> bool:
    """
    Check if a skill should be included.
    
    Eligibility rules (matches pi-coding-agent):
    1. skills.entries.<key>.enabled === False → exclude
    2. Bundled skill + allowBundled settings → must be in whitelist
    3. metadata.os → must match runtime platform
    4. metadata.always === True → include
    5. requires.bins → all must exist in PATH
    6. requires.anyBins → at least one must exist
    7. requires.env → all must be set
    8. requires.config → all config paths must be truthy
    
    Args:
        entry: Skill entry to check
        config: OpenClaw configuration
        eligibility: Runtime eligibility context
        
    Returns:
        True if skill should be included
    """
    skill = entry.skill
    skill_key = entry.skill_key
    
    # Rule 1: Check if explicitly disabled in config
    if config:
        skills_config = config.get('skills', {})
        entries_config = skills_config.get('entries', {})
        skill_entry_config = entries_config.get(skill_key, {})
        
        if skill_entry_config.get('enabled') is False:
            logger.debug(f"Skill {skill.name} disabled in config")
            return False
    
    # Rule 2: Check bundled skill allowlist
    if entry.source == "bundled" and config:
        skills_config = config.get('skills', {})
        allow_bundled = skills_config.get('allowBundled')
        
        if allow_bundled is not None:
            if isinstance(allow_bundled, bool):
                if not allow_bundled:
                    logger.debug(f"Bundled skill {skill.name} excluded (allowBundled=false)")
                    return False
            elif isinstance(allow_bundled, list):
                if skill.name not in allow_bundled and skill_key not in allow_bundled:
                    logger.debug(f"Bundled skill {skill.name} not in allowBundled list")
                    return False
    
    # Rule 3: Check OS requirement
    if skill.metadata and skill.metadata.os:
        if eligibility.platform not in skill.metadata.os:
            logger.debug(f"Skill {skill.name} requires OS {skill.metadata.os}, got {eligibility.platform}")
            return False
    
    # Rule 4: Always include if marked
    if skill.metadata and skill.metadata.always:
        logger.debug(f"Skill {skill.name} marked as always, including")
        return True
    
    # Rule 5-8: Check requirements
    if skill.metadata and skill.metadata.requires:
        if not check_skill_requirements(skill.metadata.requires, eligibility, config):
            logger.debug(f"Skill {skill.name} requirements not met")
            return False
    
    logger.debug(f"Skill {skill.name} eligible for inclusion")
    return True


def check_skill_requirements(
    requires: Any,
    eligibility: SkillEligibilityContext,
    config: dict | None
) -> bool:
    """
    Check if skill requirements are met.
    
    Args:
        requires: SkillRequires object
        eligibility: Runtime eligibility context
        config: OpenClaw configuration
        
    Returns:
        True if all requirements are met
    """
    # Check bins (all required)
    if hasattr(requires, 'bins') and requires.bins:
        for bin_name in requires.bins:
            if bin_name not in eligibility.available_bins:
                logger.debug(f"Required binary not found: {bin_name}")
                return False
    
    # Check anyBins (at least one required)
    if hasattr(requires, 'any_bins') and requires.any_bins:
        found = any(bin_name in eligibility.available_bins for bin_name in requires.any_bins)
        if not found:
            logger.debug(f"None of the required binaries found: {requires.any_bins}")
            return False
    
    # Check env (all required)
    if hasattr(requires, 'env') and requires.env:
        for env_var in requires.env:
            if env_var not in eligibility.env_vars:
                logger.debug(f"Required environment variable not set: {env_var}")
                return False
    
    # Check config paths (all must be truthy)
    if hasattr(requires, 'config') and requires.config:
        if not config:
            logger.debug(f"Config required but not provided")
            return False
        
        for config_path in requires.config:
            if not _check_config_path(config, config_path):
                logger.debug(f"Required config path not truthy: {config_path}")
                return False
    
    return True


def _check_config_path(config: dict, path: str) -> bool:
    """
    Check if a config path is truthy.
    
    Supports dot notation: "api.keys.openai"
    
    Args:
        config: Configuration dict
        path: Dot-separated path
        
    Returns:
        True if path exists and is truthy
    """
    parts = path.split('.')
    current = config
    
    for part in parts:
        if not isinstance(current, dict):
            return False
        
        if part not in current:
            return False
        
        current = current[part]
    
    # Check if truthy (not None, not False, not empty string)
    return bool(current)


def build_eligibility_context() -> SkillEligibilityContext:
    """
    Build eligibility context from runtime environment.
    
    Returns:
        SkillEligibilityContext with current runtime info
    """
    import os
    
    # Get platform
    system = platform.system().lower()
    if system == 'darwin':
        platform_name = 'darwin'
    elif system == 'linux':
        platform_name = 'linux'
    elif system == 'windows':
        platform_name = 'win32'
    else:
        platform_name = system
    
    # Find available binaries
    available_bins = set()
    
    # Common bins to check
    common_bins = [
        'git', 'gh', 'docker', 'python', 'python3', 'node', 'npm',
        'go', 'cargo', 'rustc', 'uv', 'brew', 'apt', 'curl', 'wget',
        'jq', 'tmux', 'ssh', 'rsync', 'tar', 'gzip', 'zip', 'unzip'
    ]
    
    for bin_name in common_bins:
        if shutil.which(bin_name):
            available_bins.add(bin_name)
    
    # Get environment variables
    env_vars = dict(os.environ)
    
    return SkillEligibilityContext(
        platform=platform_name,
        available_bins=available_bins,
        env_vars=env_vars
    )


__all__ = [
    "should_include_skill",
    "check_skill_requirements",
    "build_eligibility_context",
]

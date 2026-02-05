"""Skill eligibility checking system."""
import os
import shutil
import sys
from typing import Optional


class SkillEligibilityChecker:
    """Checks if a skill can be loaded based on requirements."""
    
    def __init__(self, config: dict):
        self.config = config
    
    def check(self, skill) -> tuple[bool, Optional[str]]:
        """
        Check if a skill meets all requirements.
        
        Returns:
            (is_eligible, reason_if_not)
        """
        metadata = getattr(skill, 'metadata', {})
        
        # Check if explicitly disabled in config
        skill_config = self._get_skill_config(skill.name)
        if skill_config.get('enabled') is False:
            return False, "Disabled in config"
        
        # Check OS requirements
        required_os = metadata.get('os', [])
        if required_os and sys.platform not in required_os:
            return False, f"Requires OS: {', '.join(required_os)}"
        
        # Check required binaries
        requires_bins = metadata.get('requires', {}).get('bins', [])
        for binary in requires_bins:
            if not shutil.which(binary):
                return False, f"Missing binary: {binary}"
        
        # Check anyBins (at least one must exist)
        any_bins = metadata.get('requires', {}).get('anyBins', [])
        if any_bins:
            found = any(shutil.which(bin_name) for bin_name in any_bins)
            if not found:
                return False, f"Missing any of: {', '.join(any_bins)}"
        
        # Check required environment variables
        requires_env = metadata.get('requires', {}).get('env', [])
        for env_var in requires_env:
            # Check system environment
            if os.getenv(env_var):
                continue
            
            # Check config env
            if skill_config.get('env', {}).get(env_var):
                continue
            
            # Check apiKey for primaryEnv
            primary_env = metadata.get('primaryEnv')
            if primary_env == env_var and skill_config.get('apiKey'):
                continue
            
            return False, f"Missing env: {env_var}"
        
        # Check config requirements
        requires_config = metadata.get('requires', {}).get('config', [])
        for config_path in requires_config:
            value = self._resolve_config_value(config_path)
            if not value:
                return False, f"Missing config: {config_path}"
        
        # always: true overrides all checks
        if metadata.get('always') is True:
            return True, None
        
        return True, None
    
    def _get_skill_config(self, skill_name: str) -> dict:
        """Get skill-specific config."""
        return (
            self.config
            .get('skills', {})
            .get('entries', {})
            .get(skill_name, {})
        )
    
    def _resolve_config_value(self, path: str):
        """Resolve nested config value by dot-separated path."""
        parts = path.split('.')
        value = self.config
        
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
                if value is None:
                    return None
            else:
                return None
        
        return value

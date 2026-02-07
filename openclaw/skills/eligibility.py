"""Skill eligibility checking system."""

import os
import shutil
import sys


class SkillEligibilityChecker:
    """Checks if a skill can be loaded based on requirements."""

    def __init__(self, config: dict):
        self.config = config

    def check(self, skill) -> tuple[bool, str | None]:
        """
        Check if a skill meets all requirements.

        Returns:
            (is_eligible, reason_if_not)
        """
        metadata = getattr(skill, "metadata", {})

        # Normalize metadata to a plain dict so callers can use either a
        # mapping or a Pydantic model (SkillMetadata). Also support legacy
        # flat keys like `requires_bins` by converting them into the
        # nested `requires` structure expected below.
        if not isinstance(metadata, dict):
            # Try Pydantic v2 model_dump, then .dict()
            if hasattr(metadata, "model_dump"):
                try:
                    metadata_dict = metadata.model_dump()
                except Exception:
                    metadata_dict = dict(metadata.__dict__)
            elif hasattr(metadata, "dict"):
                try:
                    metadata_dict = metadata.dict()
                except Exception:
                    metadata_dict = dict(metadata.__dict__)
            else:
                try:
                    metadata_dict = dict(metadata.__dict__)
                except Exception:
                    metadata_dict = {}
        else:
            metadata_dict = metadata

        # Normalize 'requires' structure: accept flat keys like requires_bins
        requires = metadata_dict.get("requires") or {}
        # bins
        if "requires_bins" in metadata_dict and metadata_dict.get("requires_bins"):
            requires["bins"] = list(requires.get("bins", [])) + list(
                metadata_dict.get("requires_bins") or []
            )
        if "bins" in requires and requires.get("bins") is None:
            requires["bins"] = []
        # anyBins
        if "any_bins" in metadata_dict and metadata_dict.get("any_bins"):
            requires["anyBins"] = list(requires.get("anyBins", [])) + list(
                metadata_dict.get("any_bins") or []
            )
        if "anyBins" in metadata_dict and metadata_dict.get("anyBins"):
            requires["anyBins"] = list(requires.get("anyBins", [])) + list(
                metadata_dict.get("anyBins") or []
            )
        # env
        if "requires_env" in metadata_dict and metadata_dict.get("requires_env"):
            requires["env"] = list(requires.get("env", [])) + list(
                metadata_dict.get("requires_env") or []
            )
        if "requires_config" in metadata_dict and metadata_dict.get("requires_config"):
            requires["config"] = list(requires.get("config", [])) + list(
                metadata_dict.get("requires_config") or []
            )

        # Use normalized metadata for checks
        metadata = metadata_dict
        metadata["requires"] = requires

        # Check if explicitly disabled in config
        skill_config = self._get_skill_config(skill.name)
        if skill_config.get("enabled") is False:
            return False, "Disabled in config"

        # Check OS requirements
        required_os = metadata.get("os", [])
        if required_os and sys.platform not in required_os:
            return False, f"Requires OS: {', '.join(required_os)}"

        # Check required binaries
        requires_bins = metadata.get("requires", {}).get("bins", [])
        for binary in requires_bins:
            if not shutil.which(binary):
                return False, f"Missing binary: {binary}"

        # Check anyBins (at least one must exist)
        any_bins = metadata.get("requires", {}).get("anyBins", [])
        if any_bins:
            found = any(shutil.which(bin_name) for bin_name in any_bins)
            if not found:
                return False, f"Missing any of: {', '.join(any_bins)}"

        # Check required environment variables
        requires_env = metadata.get("requires", {}).get("env", [])
        for env_var in requires_env:
            # Check system environment
            if os.getenv(env_var):
                continue

            # Check config env
            if skill_config.get("env", {}).get(env_var):
                continue

            # Check apiKey for primaryEnv
            primary_env = metadata.get("primaryEnv")
            if primary_env == env_var and skill_config.get("apiKey"):
                continue

            return False, f"Missing env: {env_var}"

        # Check config requirements
        requires_config = metadata.get("requires", {}).get("config", [])
        for config_path in requires_config:
            value = self._resolve_config_value(config_path)
            if not value:
                return False, f"Missing config: {config_path}"

        # always: true overrides all checks
        if metadata.get("always") is True:
            return True, None

        return True, None

    def _get_skill_config(self, skill_name: str) -> dict:
        """Get skill-specific config."""
        return self.config.get("skills", {}).get("entries", {}).get(skill_name, {})

    def _resolve_config_value(self, path: str):
        """Resolve nested config value by dot-separated path."""
        parts = path.split(".")
        value = self.config

        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
                if value is None:
                    return None
            else:
                return None

        return value

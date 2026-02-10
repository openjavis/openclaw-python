"""Skill command integration

Loads and manages skill commands from workspace.
Matches TypeScript openclaw/src/auto-reply/skill-commands.ts
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SkillCommandLoader:
    """
    Loader for skill commands
    
    Skills are loaded from workspace directory and registered as commands.
    """
    
    def __init__(self, workspace_path: Path | None = None):
        """
        Initialize skill command loader
        
        Args:
            workspace_path: Path to workspace directory
        """
        if workspace_path is None:
            workspace_path = Path.home() / ".openclaw" / "workspace"
        
        self.workspace_path = workspace_path
        self.skills: dict[str, dict[str, Any]] = {}
    
    def load_skills(self) -> int:
        """
        Load skills from workspace
        
        Returns:
            Number of skills loaded
        """
        skills_dir = self.workspace_path / "skills"
        
        if not skills_dir.exists():
            logger.debug(f"Skills directory not found: {skills_dir}")
            return 0
        
        count = 0
        
        # Scan for skill directories
        for skill_dir in skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            
            # Look for skill.json
            skill_file = skill_dir / "skill.json"
            
            if skill_file.exists():
                try:
                    skill = self._load_skill(skill_file)
                    self.skills[skill["name"]] = skill
                    count += 1
                except Exception as e:
                    logger.error(f"Error loading skill from {skill_file}: {e}")
        
        logger.info(f"Loaded {count} skills")
        
        return count
    
    def _load_skill(self, skill_file: Path) -> dict[str, Any]:
        """
        Load skill from file
        
        Args:
            skill_file: Path to skill.json
            
        Returns:
            Skill definition
        """
        import json
        
        with open(skill_file) as f:
            skill = json.load(f)
        
        # Validate required fields
        if "name" not in skill:
            raise ValueError("Skill must have 'name' field")
        
        if "dispatch" not in skill:
            raise ValueError("Skill must have 'dispatch' field")
        
        return skill
    
    def get_skill(self, skill_name: str) -> dict[str, Any] | None:
        """
        Get skill by name
        
        Args:
            skill_name: Skill name
            
        Returns:
            Skill definition or None
        """
        return self.skills.get(skill_name)
    
    def get_all_skills(self) -> list[dict[str, Any]]:
        """Get all loaded skills"""
        return list(self.skills.values())


def rewrite_prompt_for_skill(skill: dict[str, Any], args: list[str]) -> str:
    """
    Rewrite prompt for skill dispatch
    
    For skills with dispatch_mode="prompt", rewrites the user's message
    to include skill instructions.
    
    Args:
        skill: Skill definition
        args: Command arguments
        
    Returns:
        Rewritten prompt
    """
    dispatch_mode = skill.get("dispatch", {}).get("mode", "tool")
    
    if dispatch_mode != "prompt":
        return ""
    
    # Get prompt template
    prompt_template = skill.get("dispatch", {}).get("prompt_template", "")
    
    if not prompt_template:
        return ""
    
    # Replace {args} placeholder
    args_str = " ".join(args)
    prompt = prompt_template.replace("{args}", args_str)
    
    return prompt


def get_skill_tool_names(skill: dict[str, Any]) -> list[str]:
    """
    Get tool names for skill
    
    For skills with dispatch_mode="tool", returns the list of tools to enable.
    
    Args:
        skill: Skill definition
        
    Returns:
        List of tool names
    """
    dispatch_mode = skill.get("dispatch", {}).get("mode", "tool")
    
    if dispatch_mode != "tool":
        return []
    
    return skill.get("dispatch", {}).get("tools", [])

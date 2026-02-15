"""
Skills Status - builds skill status reports for workspaces

Aligned with openclaw/src/agents/skills-status.ts
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def build_workspace_skill_status(
    workspace_dir: Path,
    config: dict | None = None,
    eligibility: dict | None = None,
) -> dict[str, Any]:
    """
    Build skill status report for workspace
    
    Args:
        workspace_dir: Workspace directory path
        config: Optional config dict
        eligibility: Optional eligibility info (remote skills, etc.)
        
    Returns:
        Skill status report matching TypeScript SkillStatusReport
    """
    skills_dir = workspace_dir / ".openclaw" / "skills"
    
    skills = []
    if skills_dir.exists():
        for skill_path in skills_dir.glob("*/SKILL.md"):
            skill_name = skill_path.parent.name
            
            # Parse basic skill metadata from SKILL.md
            try:
                with open(skill_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Extract first line as description
                    first_line = content.split('\n')[0] if content else ""
                    description = first_line.strip('# ').strip()
            except Exception as e:
                logger.warning(f"Failed to parse skill {skill_name}: {e}")
                description = ""
            
            skill_entry = {
                "name": skill_name,
                "description": description,
                "source": "managed",
                "bundled": False,
                "filePath": str(skill_path),
                "baseDir": str(skill_path.parent),
                "skillKey": f"managed:{skill_name}",
                "enabled": True,
                "eligible": True,
                "always": False,
                "disabled": False,
                "blockedByAllowlist": False,
                # Requirements and missing checks
                "requirements": {
                    "bins": [],
                    "anyBins": [],
                    "env": [],
                    "config": [],
                    "os": []
                },
                "missing": {
                    "bins": [],
                    "anyBins": [],
                    "env": [],
                    "config": [],
                    "os": []
                }
            }
            
            skills.append(skill_entry)
    
    return {
        "workspaceDir": str(workspace_dir),
        "managedSkillsDir": str(skills_dir),
        "skills": skills,
    }


def list_skill_names(workspace_dir: Path) -> list[str]:
    """List all skill names in workspace"""
    skills_dir = workspace_dir / ".openclaw" / "skills"
    if not skills_dir.exists():
        return []
    
    return [p.parent.name for p in skills_dir.glob("*/SKILL.md")]


def get_skill_path(workspace_dir: Path, skill_name: str) -> Path | None:
    """Get skill path by name"""
    skills_dir = workspace_dir / ".openclaw" / "skills"
    skill_path = skills_dir / skill_name / "SKILL.md"
    
    if skill_path.exists():
        return skill_path
    return None

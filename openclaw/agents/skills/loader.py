"""
Skill loader

Loads skills from directories.
Matches TypeScript loadSkillsFromDir from @mariozechner/pi-coding-agent
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .frontmatter import (
    extract_description_from_body,
    parse_frontmatter,
    parse_invocation_policy,
    parse_openclaw_metadata,
)
from .types import Skill, SkillEntry

logger = logging.getLogger(__name__)


class SkillLoader:
    """Skill loader class for managing skills from multiple directories"""
    
    def __init__(self, bundled_skills_dir: Path | str | None = None):
        """
        Initialize skill loader
        
        Args:
            bundled_skills_dir: Directory containing bundled skills
        """
        self.bundled_skills_dir = Path(bundled_skills_dir) if bundled_skills_dir else None
        self.skills: list[Skill] = []
    
    def load_all_skills(self) -> None:
        """Load all skills from configured directories"""
        if self.bundled_skills_dir:
            bundled = load_skills_from_dir(self.bundled_skills_dir, source="bundled")
            self.skills.extend(bundled)
            logger.info(f"Loaded {len(bundled)} bundled skills")
    
    def get_skills(self) -> list[Skill]:
        """Get all loaded skills"""
        return self.skills


def load_skills_from_dir(
    directory: Path | str,
    source: str = "workspace"
) -> list[Skill]:
    """
    Load skills from directory (matches pi-coding-agent loadSkillsFromDir).
    
    Scans for SKILL.md files in subdirectories.
    Each subdirectory with a SKILL.md is considered a skill.
    
    Args:
        directory: Directory to scan for skills
        source: Source identifier (workspace, bundled, etc.)
    
    Returns:
        List of Skill objects
    """
    if isinstance(directory, str):
        directory = Path(directory)
    
    if not directory.exists():
        logger.debug(f"Skills directory does not exist: {directory}")
        return []
    
    if not directory.is_dir():
        logger.warning(f"Skills path is not a directory: {directory}")
        return []
    
    skills = []
    
    # Scan subdirectories for SKILL.md
    for skill_dir in directory.iterdir():
        if not skill_dir.is_dir():
            continue
        
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue
        
        try:
            skill = load_skill_from_file(skill_file, source)
            if skill:
                skills.append(skill)
        except Exception as e:
            logger.warning(f"Failed to load skill from {skill_dir.name}: {e}")
    
    return skills


def load_skill_entries_from_dir(
    directory: Path | str,
    source: str = "workspace"
) -> list[SkillEntry]:
    """
    Load skill entries (with metadata) from directory.
    
    Args:
        directory: Directory to scan for skills
        source: Source identifier
    
    Returns:
        List of SkillEntry objects
    """
    if isinstance(directory, str):
        directory = Path(directory)
    
    if not directory.exists():
        return []
    
    entries = []
    
    for skill_dir in directory.iterdir():
        if not skill_dir.is_dir():
            continue
        
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue
        
        try:
            entry = load_skill_entry_from_file(skill_file, source)
            if entry:
                entries.append(entry)
        except Exception as e:
            logger.warning(f"Failed to load skill entry from {skill_dir.name}: {e}")
    
    return entries


def load_skill_from_file(
    file_path: Path,
    source: str = "workspace"
) -> Skill | None:
    """
    Load skill from SKILL.md file.
    
    Args:
        file_path: Path to SKILL.md file
        source: Source identifier
    
    Returns:
        Skill object or None
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.error(f"Failed to read {file_path}: {e}")
        return None
    
    # Parse frontmatter
    frontmatter, body = parse_frontmatter(content)
    
    # Get name from frontmatter or directory name
    name = frontmatter.get("name")
    if not name or not isinstance(name, str):
        name = file_path.parent.name
    
    # Get description from frontmatter or extract from body
    description = frontmatter.get("description", "")
    if not isinstance(description, str):
        description = ""
    
    if not description and body:
        description = extract_description_from_body(body)
    
    return Skill(
        name=name.strip(),
        description=description.strip(),
        location=str(file_path),
        source=source,
    )


def load_skill_entry_from_file(
    file_path: Path,
    source: str = "workspace"
) -> SkillEntry | None:
    """
    Load skill entry (with metadata) from SKILL.md file.
    
    Args:
        file_path: Path to SKILL.md file
        source: Source identifier
    
    Returns:
        SkillEntry object or None
    """
    skill = load_skill_from_file(file_path, source)
    if not skill:
        return None
    
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.error(f"Failed to read {file_path}: {e}")
        return None
    
    frontmatter, _ = parse_frontmatter(content)
    metadata = parse_openclaw_metadata(frontmatter)
    invocation = parse_invocation_policy(frontmatter)
    
    return SkillEntry(
        skill=skill,
        frontmatter=frontmatter,
        metadata=metadata,
        invocation=invocation
    )


def format_skills_for_prompt(skills: list[Skill]) -> str:
    """
    Format skills for system prompt (matches pi-coding-agent formatSkillsForPrompt).
    
    Returns formatted string like:
    - skill-name: Description (location: /path/to/SKILL.md)
    - another-skill: Description (location: /path/to/SKILL.md)
    
    Args:
        skills: List of skills
    
    Returns:
        Formatted skills string
    """
    if not skills:
        return ""
    
    lines = []
    for skill in skills:
        line = f"- {skill.name}: {skill.description}"
        if skill.location:
            line += f" (location: {skill.location})"
        lines.append(line)
    
    return "\n".join(lines)

"""
Skill discovery from directories.

Discovers skills by finding .md and SKILL.md files, respecting
ignore files (.gitignore, .ignore, .fdignore).
"""
from __future__ import annotations

import logging
from pathlib import Path

from .frontmatter import parse_skill_frontmatter
from .types import Skill, LoadSkillsResult

logger = logging.getLogger(__name__)


def load_skills_from_dir(
    dir_path: Path,
    include_root_files: bool = True,
    source: str = "workspace"
) -> LoadSkillsResult:
    """
    Discover skills from a directory.
    
    Discovery rules (matches pi-coding-agent):
    - Direct .md files in the root (if include_root_files=True)
    - Recursive SKILL.md under subdirectories
    - Respects .gitignore, .ignore, .fdignore
    - Skips node_modules
    
    Args:
        dir_path: Directory to search
        include_root_files: Include root-level .md files
        source: Source identifier (bundled, managed, workspace, etc.)
        
    Returns:
        LoadSkillsResult with discovered skills and errors
    """
    skills = []
    errors = []
    
    if not dir_path.exists() or not dir_path.is_dir():
        return LoadSkillsResult(skills=skills, errors=[f"Directory not found: {dir_path}"])
    
    # Load ignore patterns
    ignore_patterns = _load_ignore_patterns(dir_path)
    
    try:
        # Find root-level .md files
        if include_root_files:
            for md_file in dir_path.glob("*.md"):
                if _should_ignore(md_file, dir_path, ignore_patterns):
                    continue
                
                skill = _load_skill_file(md_file, source)
                if skill:
                    skills.append(skill)
                else:
                    errors.append(f"Failed to parse skill: {md_file}")
        
        # Find SKILL.md files in subdirectories
        for skill_md in dir_path.rglob("SKILL.md"):
            if _should_ignore(skill_md, dir_path, ignore_patterns):
                continue
            
            skill = _load_skill_file(skill_md, source)
            if skill:
                skills.append(skill)
            else:
                errors.append(f"Failed to parse skill: {skill_md}")
    
    except Exception as e:
        logger.error(f"Error discovering skills from {dir_path}: {e}", exc_info=True)
        errors.append(f"Discovery error: {e}")
    
    return LoadSkillsResult(skills=skills, errors=errors)


def _load_skill_file(file_path: Path, source: str) -> Skill | None:
    """Load a single skill file"""
    try:
        content = file_path.read_text(encoding='utf-8')
        skill = parse_skill_frontmatter(content, str(file_path))
        
        if skill:
            skill.source = source
            logger.debug(f"Loaded skill: {skill.name} from {file_path}")
        
        return skill
    
    except Exception as e:
        logger.warning(f"Failed to load skill from {file_path}: {e}")
        return None


def _load_ignore_patterns(dir_path: Path) -> set[str]:
    """
    Load ignore patterns from .gitignore, .ignore, .fdignore
    
    Returns:
        Set of ignore patterns
    """
    patterns = {"node_modules", ".git", "__pycache__", "*.pyc"}
    
    ignore_files = [".gitignore", ".ignore", ".fdignore"]
    
    for ignore_file in ignore_files:
        ignore_path = dir_path / ignore_file
        if ignore_path.exists():
            try:
                content = ignore_path.read_text()
                for line in content.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        patterns.add(line)
            except Exception:
                pass
    
    return patterns


def _should_ignore(file_path: Path, root: Path, patterns: set[str]) -> bool:
    """
    Check if file should be ignored based on patterns.
    
    Args:
        file_path: File to check
        root: Root directory
        patterns: Ignore patterns
        
    Returns:
        True if file should be ignored
    """
    try:
        relative = file_path.relative_to(root)
        parts = relative.parts
        
        # Check each part against patterns
        for part in parts:
            if part in patterns:
                return True
            
            # Check wildcard patterns
            for pattern in patterns:
                if '*' in pattern:
                    # Simple wildcard matching
                    pattern_parts = pattern.split('*')
                    if all(p in part for p in pattern_parts if p):
                        return True
        
        # Check full path patterns
        relative_str = str(relative)
        for pattern in patterns:
            if pattern in relative_str:
                return True
        
        return False
    
    except ValueError:
        return False


__all__ = [
    "load_skills_from_dir",
]

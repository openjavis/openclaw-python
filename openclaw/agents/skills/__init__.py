"""
Skills system for OpenClaw

Matches TypeScript src/agents/skills/
"""
from .loader import load_skills_from_dir
from .types import OpenClawSkillMetadata, Skill, SkillEntry, SkillRequires, SkillSnapshot
from .workspace import (
    build_workspace_skill_snapshot,
    build_workspace_skills_prompt,
    load_workspace_skill_entries,
)

# Alias matching the public API name used by tests and callers
load_skill_entries = load_workspace_skill_entries

__all__ = [
    "Skill",
    "SkillEntry",
    "SkillRequires",
    "SkillSnapshot",
    "OpenClawSkillMetadata",
    "load_skills_from_dir",
    "load_skill_entries",
    "load_workspace_skill_entries",
    "build_workspace_skills_prompt",
    "build_workspace_skill_snapshot",
]

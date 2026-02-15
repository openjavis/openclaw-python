"""
Format skills for inclusion in system prompt.

Generates the <available_skills> section for agent system prompts.
"""
from __future__ import annotations

import logging
from typing import Any

from .types import SkillEntry

logger = logging.getLogger(__name__)


def format_skills_for_prompt(
    skill_entries: list[SkillEntry],
    read_tool_name: str = "read"
) -> str:
    """
    Format skills for system prompt.
    
    Generates XML-formatted skills section matching pi-coding-agent format:
    
    <available_skills>
      <skill>
        <name>github</name>
        <description>GitHub operations via gh CLI</description>
        <location>/path/to/SKILL.md</location>
      </skill>
      ...
    </available_skills>
    
    Args:
        skill_entries: List of skill entries to format
        read_tool_name: Name of the read tool (for instructions)
        
    Returns:
        Formatted skills XML string
    """
    if not skill_entries:
        return ""
    
    # Build skill entries
    skill_items = []
    for entry in skill_entries:
        skill = entry.skill
        
        # Skip skills that are disabled for model invocation
        if skill.disable_model_invocation:
            continue
        
        skill_item = f"""  <skill>
    <name>{_escape_xml(skill.name)}</name>
    <description>{_escape_xml(skill.description)}</description>
    <location>{_escape_xml(skill.file_path)}</location>
  </skill>"""
        skill_items.append(skill_item)
    
    if not skill_items:
        return ""
    
    skills_xml = "\n".join(skill_items)
    
    return f"""<available_skills>
{skills_xml}
</available_skills>"""


def build_skills_section_instructions(read_tool_name: str = "read") -> str:
    """
    Build instructions for using skills in system prompt.
    
    Args:
        read_tool_name: Name of the read tool
        
    Returns:
        Skills section instructions
    """
    return f"""## Skills (mandatory)

Before replying: scan <available_skills> <description> entries.
- If exactly one skill clearly applies: read its SKILL.md at <location> with `{read_tool_name}`, then follow it.
- If multiple could apply: choose the most specific one, then read/follow it.
- If none clearly apply: do not read any SKILL.md.

Skills provide specialized guidance for specific tasks (e.g., GitHub operations, weather queries, tmux control).
When a skill applies, reading and following its instructions is mandatory - this ensures consistent, high-quality responses."""


def _escape_xml(text: str) -> str:
    """
    Escape XML special characters.
    
    Args:
        text: Text to escape
        
    Returns:
        XML-escaped text
    """
    if not text:
        return ""
    
    return (text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;"))


__all__ = [
    "format_skills_for_prompt",
    "build_skills_section_instructions",
]

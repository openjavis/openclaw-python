"""Skills serialization (matches TypeScript agents/skills/serialize.ts)

Serializes skills into format suitable for system prompt injection.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def serialize_skill_for_prompt(
    skill_name: str,
    skill_content: str,
    max_chars: int = 10000,
) -> str:
    """
    Serialize a skill's SKILL.md content for injection into system prompt.
    
    Args:
        skill_name: Skill name
        skill_content: Full SKILL.md content
        max_chars: Maximum characters (truncate if exceeded)
    
    Returns:
        Formatted string for system prompt
    """
    if len(skill_content) > max_chars:
        # Truncate: 70% head + 20% tail
        head_size = int(max_chars * 0.7)
        tail_size = int(max_chars * 0.2)
        
        head = skill_content[:head_size]
        tail = skill_content[-tail_size:]
        
        skill_content = f"{head}\n\n... (truncated {len(skill_content) - max_chars} chars) ...\n\n{tail}"
    
    return f"## Skill: {skill_name}\n\n{skill_content}"


def serialize_skills_snapshot(
    skills: list[dict[str, Any]],
    max_total_chars: int = 50000,
) -> str:
    """
    Serialize all eligible skills into a single prompt section.
    
    Args:
        skills: List of skill dicts with name, content, description
        max_total_chars: Maximum total characters
    
    Returns:
        Combined skills section for system prompt
    """
    if not skills:
        return ""
    
    sections = []
    remaining_chars = max_total_chars
    
    for skill in skills:
        name = skill.get("name", "unknown")
        content = skill.get("content", "")
        description = skill.get("description", "")
        
        # Calculate per-skill budget
        per_skill_budget = remaining_chars // max(1, len(skills) - len(sections))
        
        if content:
            serialized = serialize_skill_for_prompt(name, content, per_skill_budget)
        else:
            serialized = f"## Skill: {name}\n\n{description}"
        
        sections.append(serialized)
        remaining_chars -= len(serialized)
        
        if remaining_chars <= 0:
            break
    
    return "\n\n---\n\n".join(sections)


def serialize_skill_list_summary(
    skills: list[dict[str, Any]],
) -> str:
    """
    Create a brief summary of available skills.
    
    Args:
        skills: List of skill dicts
    
    Returns:
        Brief summary string
    """
    if not skills:
        return "No skills available."
    
    lines = [f"Available skills ({len(skills)}):"]
    for skill in skills:
        name = skill.get("name", "unknown")
        desc = skill.get("description", "")[:80]
        lines.append(f"  - **{name}**: {desc}")
    
    return "\n".join(lines)

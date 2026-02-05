"""System prompt builder for OpenClaw agent"""
import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


def build_agent_system_prompt(
    workspace_dir: Path,
    tool_names: Optional[List[str]] = None,
    skills_prompt: Optional[str] = None,
    mode: str = "full",
) -> str:
    """
    Build the agent system prompt
    
    Args:
        workspace_dir: Workspace directory path
        tool_names: List of available tool names
        skills_prompt: Formatted skills prompt (XML format)
        mode: Prompt mode ('full', 'minimal', 'none')
    
    Returns:
        Complete system prompt string
    """
    if mode == "none":
        return ""
    
    is_minimal = mode == "minimal"
    sections = []
    
    # 1. Core identity
    sections.extend([
        "# OpenClaw Agent",
        "",
        "You are an AI coding assistant powered by OpenClaw, designed to help users with:",
        "- Code writing, debugging, and review",
        "- File operations (reading, writing, editing)",
        "- Web searches and information gathering",
        "- Bash command execution",
        "- Image analysis",
        "- Session and project management",
        "",
    ])
    
    # 2. Workspace context
    sections.extend([
        f"## Workspace",
        f"Current workspace: `{workspace_dir}`",
        "",
    ])
    
    # 3. Available tools
    if tool_names and not is_minimal:
        sections.extend([
            "## Available Tools",
            "You have access to the following tools:",
            "",
        ])
        for tool_name in sorted(tool_names):
            sections.append(f"- `{tool_name}`")
        sections.append("")
    
    # 4. Skills section (if provided)
    if skills_prompt and not is_minimal:
        sections.extend([
            "## Skills (mandatory)",
            "Before replying: scan <available_skills> <description> entries.",
            "- If exactly one skill clearly applies: read its SKILL.md at <location> with `read_file`, then follow it.",
            "- If multiple could apply: choose the most specific one, then read/follow it.",
            "- If none clearly apply: do not read any SKILL.md.",
            "Constraints: never read more than one skill up front; only read after selecting.",
            "",
            skills_prompt.strip(),
            "",
        ])
    
    # 5. General guidelines
    if not is_minimal:
        sections.extend([
            "## Guidelines",
            "",
            "### Code Quality",
            "- Write clean, well-documented code",
            "- Follow language-specific best practices",
            "- Include error handling where appropriate",
            "- Use descriptive variable and function names",
            "",
            "### Tool Usage",
            "- Use `read_file` before editing files",
            "- Use `write_file` for new files, `edit_file` for modifications",
            "- Use `bash` for command execution (be cautious with destructive operations)",
            "- Use `web_search` for up-to-date information",
            "",
            "### Communication",
            "- Be concise but thorough",
            "- Explain your reasoning when making significant decisions",
            "- Ask for clarification when requirements are unclear",
            "- Provide code examples when helpful",
            "",
        ])
    
    return "\n".join(sections)


def format_skills_for_prompt(skills: List[dict]) -> str:
    """
    Format skills list as XML prompt
    
    Args:
        skills: List of skill dicts with 'name', 'description', 'location'
    
    Returns:
        XML formatted skills prompt
    """
    if not skills:
        return ""
    
    lines = ["<available_skills>"]
    
    for skill in skills:
        lines.append("  <skill>")
        lines.append(f"    <name>{skill['name']}</name>")
        if 'description' in skill:
            lines.append(f"    <description>{skill['description']}</description>")
        if 'location' in skill:
            lines.append(f"    <location>{skill['location']}</location>")
        if 'tags' in skill and skill['tags']:
            tags_str = ", ".join(skill['tags'])
            lines.append(f"    <tags>{tags_str}</tags>")
        lines.append("  </skill>")
    
    lines.append("</available_skills>")
    
    return "\n".join(lines)

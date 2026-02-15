"""Populate workspace files with user information collected during onboarding."""

from pathlib import Path
from typing import Optional


def populate_user_md(workspace_dir: Path, user_info: dict) -> None:
    """Populate USER.md with collected information.
    
    Args:
        workspace_dir: Path to workspace directory
        user_info: Dictionary containing user information
    """
    user_md = workspace_dir / "USER.md"
    
    content = "# USER.md - About Your Human\n\n"
    
    if "name" in user_info:
        content += f"- **Name:** {user_info['name']}\n"
        content += f"- **What to call them:** {user_info.get('what_to_call_them', user_info['name'])}\n"
    else:
        content += "- **Name:** [To be filled]\n"
        content += "- **What to call them:** [To be filled]\n"
    
    content += f"- **Pronouns:** {user_info.get('pronouns', '[optional]')}\n"
    content += f"- **Timezone:** {user_info.get('timezone', '[your timezone]')}\n"
    content += "\n## Notes\n\n"
    content += user_info.get('notes', '[Add any notes about preferences, communication style, etc.]')
    
    user_md.write_text(content, encoding="utf-8")


def populate_soul_md(workspace_dir: Path, vibe: str) -> None:
    """Update SOUL.md with user's preferred vibe.
    
    Args:
        workspace_dir: Path to workspace directory
        vibe: Preferred communication style
    """
    soul_md = workspace_dir / "SOUL.md"
    
    # Read existing template
    if soul_md.exists():
        content = soul_md.read_text(encoding="utf-8")
    else:
        content = "# SOUL.md - Your Personality\n\n"
    
    # Add vibe preference section
    vibe_section = f"\n\n## User Preference\n\nPreferred communication style: **{vibe}**\n\n"
    
    if vibe == "professional":
        vibe_section += "- Be formal and precise\n"
        vibe_section += "- Focus on facts and efficiency\n"
        vibe_section += "- Minimize casual language\n"
        vibe_section += "- Prioritize accuracy and professionalism\n"
    elif vibe == "friendly":
        vibe_section += "- Be warm and conversational\n"
        vibe_section += "- Use natural, accessible language\n"
        vibe_section += "- Build rapport through dialogue\n"
        vibe_section += "- Show personality and empathy\n"
    elif vibe == "concise":
        vibe_section += "- Be brief and direct\n"
        vibe_section += "- Prioritize clarity over completeness\n"
        vibe_section += "- Avoid unnecessary elaboration\n"
        vibe_section += "- Get straight to the point\n"
    else:
        vibe_section += "- Communication style to be customized\n"
    
    content += vibe_section
    soul_md.write_text(content, encoding="utf-8")


def populate_identity_md(workspace_dir: Path, agent_info: Optional[dict] = None) -> None:
    """Create or update IDENTITY.md with agent information.
    
    Args:
        workspace_dir: Path to workspace directory
        agent_info: Optional dictionary containing agent identity info
    """
    identity_md = workspace_dir / "IDENTITY.md"
    
    content = "# IDENTITY.md - Who Am I?\n\n"
    
    if agent_info:
        content += f"- **Name:** {agent_info.get('name', '[To be filled in first conversation]')}\n"
        content += f"- **Creature:** {agent_info.get('creature', '[To be decided]')}\n"
        content += f"- **Vibe:** {agent_info.get('vibe', '[To be decided]')}\n"
        content += f"- **Emoji:** {agent_info.get('emoji', '[To be chosen]')}\n"
    else:
        content += "- **Name:** [To be filled in first conversation]\n"
        content += "- **Creature:** [To be decided]\n"
        content += "- **Vibe:** [To be decided]\n"
        content += "- **Emoji:** [To be chosen]\n"
    
    content += "\n## About\n\n"
    content += "[This will be filled during your first conversation with the agent]\n"
    
    identity_md.write_text(content, encoding="utf-8")

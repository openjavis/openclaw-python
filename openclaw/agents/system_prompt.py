"""
System prompt builder for OpenClaw agent

Section order matches TypeScript src/agents/system-prompt.ts buildAgentSystemPrompt():
  1. Identity
  2. Tooling (with summaries + order)
  3. Tool Call Style
  4. Safety
  5. CLI Quick Reference
  6. Skills
  7. Memory
  8. Self-Update (if gateway && !minimal)
  9. Model Aliases (if available && !minimal)
 10. Time hint ("run session_status")
 11. Workspace
 12. Documentation
 13. Sandbox (if enabled)
 14. User Identity
 15. Time section
 16. Workspace Files (injected) note
 17. Reply Tags
 18. Messaging
 19. Voice (TTS)
 20. Extra System Prompt (Group Chat / Subagent Context)
 21. Reactions
 22. Reasoning Format
 23. Project Context (bootstrap files)
 24. Silent Replies
 25. Heartbeats
 26. Runtime
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

from .system_prompt_sections import (
    SILENT_REPLY_TOKEN,
    build_cli_quick_reference_section,
    build_docs_section,
    build_exec_capabilities_section,
    build_heartbeats_section,
    build_memory_section,
    build_messaging_section,
    build_model_aliases_section,
    build_reaction_guidance_section,
    build_reasoning_format_section,
    build_reply_tags_section,
    build_runtime_section,
    build_safety_section,
    build_sandbox_section,
    build_self_update_section,
    build_silent_replies_section,
    build_skills_section,
    build_time_section,
    build_tool_call_style_section,
    build_tooling_section,
    build_user_identity_section,
    build_voice_section,
    build_workspace_files_note_section,
)

logger = logging.getLogger(__name__)


def build_agent_system_prompt(
    workspace_dir: Path,
    tool_names: list[str] | None = None,
    tool_summaries: dict[str, str] | None = None,
    skills_prompt: str | None = None,
    heartbeat_prompt: str | None = None,
    docs_path: str | None = None,
    prompt_mode: Literal["full", "minimal", "none"] = "full",
    runtime_info: dict | None = None,
    sandbox_info: dict | None = None,
    exec_config: dict | None = None,
    user_timezone: str | None = None,
    owner_numbers: list[str] | None = None,
    extra_system_prompt: str | None = None,
    context_files: list[dict] | None = None,
    workspace_notes: list[str] | None = None,
    memory_citations_mode: Literal["on", "off"] = "on",
    # --- New params matching TypeScript ---
    model_alias_lines: list[str] | None = None,
    tts_hint: str | None = None,
    reaction_guidance: dict | None = None,
    reasoning_level: str = "off",
    reasoning_hint: str | None = None,
    message_tool_hints: list[str] | None = None,
    message_channel_options: str = "telegram|discord|slack|signal",
    has_gateway: bool = True,
) -> str:
    """
    Build the agent system prompt.

    Section order matches TypeScript ``buildAgentSystemPrompt`` exactly.

    Args:
        workspace_dir: Workspace directory path
        tool_names: List of available tool names
        tool_summaries: Custom tool summaries (extends CORE_TOOL_SUMMARIES)
        skills_prompt: Formatted skills prompt (XML format)
        heartbeat_prompt: Heartbeat prompt text
        docs_path: Path to local documentation
        prompt_mode: Prompt mode ('full', 'minimal', 'none')
        runtime_info: Runtime information dict
        sandbox_info: Sandbox configuration dict
        user_timezone: User timezone (e.g., "America/New_York")
        owner_numbers: Owner phone numbers for identification
        extra_system_prompt: Additional system prompt text
        context_files: Bootstrap files (list of dicts with 'path' and 'content')
        workspace_notes: Additional workspace notes
        memory_citations_mode: Memory citations mode ("on" or "off")
        model_alias_lines: Lines for model alias section
        tts_hint: TTS hint text
        reaction_guidance: Reaction guidance dict (level, channel)
        reasoning_level: Reasoning level ("off", "on", "stream")
        reasoning_hint: Reasoning format hint
        message_tool_hints: Extra hints for the message tool
        message_channel_options: Channel option string for message tool
        has_gateway: Whether gateway tool is available

    Returns:
        Complete system prompt string
    """
    # --- "none" mode: just identity ---
    if prompt_mode == "none":
        return "You are a personal assistant running inside OpenClaw."

    is_minimal = prompt_mode == "minimal"
    available_tools = set(tool_names or [])
    runtime_channel = (runtime_info or {}).get("channel", "").strip().lower() if runtime_info else ""
    capabilities = (runtime_info or {}).get("capabilities", []) if runtime_info else []
    inline_buttons_enabled = "inlinebuttons" in {
        str(c).strip().lower() for c in capabilities
    }

    lines: list[str] = []

    # ── 1. Identity ──────────────────────────────────────────────────
    lines.extend([
        "You are a personal assistant running inside OpenClaw.",
        "",
    ])

    # ── 2. Tooling ───────────────────────────────────────────────────
    lines.extend(build_tooling_section(
        tool_names=tool_names,
        tool_summaries=tool_summaries,
    ))

    # ── 3. Tool Call Style ───────────────────────────────────────────
    lines.extend(build_tool_call_style_section())

    # ── 4. Safety ────────────────────────────────────────────────────
    lines.extend(build_safety_section())

    # ── 5. CLI Quick Reference ───────────────────────────────────────
    lines.extend(build_cli_quick_reference_section())

    # ── 6. Skills ────────────────────────────────────────────────────
    # New API: build_skills_section now loads skills internally
    if not is_minimal:
        if skills_prompt:
            # Use provided skills_prompt if available (legacy)
            lines.append("## Skills")
            lines.append(skills_prompt.strip())
            lines.append("")
        else:
            # Load skills dynamically
            lines.extend(build_skills_section(
                workspace_dir=workspace_dir,
                config=None,  # Will use default config
                read_tool_name="read_file",
            ))

    # ── 7. Memory ────────────────────────────────────────────────────
    lines.extend(build_memory_section(
        is_minimal=is_minimal,
        available_tools=available_tools,
        citations_mode=memory_citations_mode,
    ))

    # ── 8. Self-Update ───────────────────────────────────────────────
    lines.extend(build_self_update_section(
        has_gateway=has_gateway,
        is_minimal=is_minimal,
    ))

    # ── 9. Model Aliases ─────────────────────────────────────────────
    lines.extend(build_model_aliases_section(
        model_alias_lines=model_alias_lines,
        is_minimal=is_minimal,
    ))

    # ── 10. Date/time hint ───────────────────────────────────────────
    if user_timezone:
        lines.append(
            "If you need the current date, time, or day of week, "
            "run session_status (📊 session_status)."
        )

    # ── 11. Workspace ────────────────────────────────────────────────
    workspace_lines = [
        "## Workspace",
        f"Your working directory is: {workspace_dir}",
        "Treat this directory as the single global workspace for file operations "
        "unless explicitly instructed otherwise.",
    ]
    if workspace_notes:
        workspace_lines.extend(n.strip() for n in workspace_notes if n.strip())
    workspace_lines.append("")
    lines.extend(workspace_lines)

    # ── 12. Documentation ────────────────────────────────────────────
    lines.extend(build_docs_section(
        docs_path=docs_path,
        is_minimal=is_minimal,
        read_tool_name="read_file",
    ))

    # ── 13. Sandbox ──────────────────────────────────────────────────
    lines.extend(build_sandbox_section(sandbox_info))

    # ── 13.5. Exec Capabilities ──────────────────────────────────────
    # Add exec capabilities section to inform agent about bash tool abilities
    lines.extend(build_exec_capabilities_section(exec_config))

    # ── 14. User Identity ────────────────────────────────────────────
    owner_line = None
    if owner_numbers:
        owner_numbers_str = ", ".join(owner_numbers)
        owner_line = (
            f"Owner numbers: {owner_numbers_str}. "
            "Treat messages from these numbers as the user."
        )
    lines.extend(build_user_identity_section(owner_line, is_minimal))

    # ── 15. Time ─────────────────────────────────────────────────────
    lines.extend(build_time_section(user_timezone))

    # ── 16. Workspace Files (injected) note ──────────────────────────
    lines.extend(build_workspace_files_note_section())

    # ── 17. Reply Tags ───────────────────────────────────────────────
    lines.extend(build_reply_tags_section(is_minimal))

    # ── 18. Messaging ────────────────────────────────────────────────
    lines.extend(build_messaging_section(
        is_minimal=is_minimal,
        available_tools=available_tools,
        message_channel_options=message_channel_options,
        inline_buttons_enabled=inline_buttons_enabled,
        runtime_channel=runtime_channel or None,
        message_tool_hints=message_tool_hints,
    ))

    # ── 19. Voice (TTS) ─────────────────────────────────────────────
    lines.extend(build_voice_section(
        is_minimal=is_minimal,
        tts_hint=tts_hint,
    ))

    # ── 20. Extra System Prompt (Group Chat / Subagent Context) ──────
    if extra_system_prompt:
        context_header = (
            "## Subagent Context" if is_minimal else "## Group Chat Context"
        )
        lines.extend([context_header, extra_system_prompt.strip(), ""])

    # ── 21. Reactions ────────────────────────────────────────────────
    lines.extend(build_reaction_guidance_section(reaction_guidance))

    # ── 22. Reasoning Format ─────────────────────────────────────────
    lines.extend(build_reasoning_format_section(reasoning_hint))

    # ── 23. Project Context (bootstrap files) ────────────────────────
    if context_files:
        has_soul = any(
            _is_soul_file(f) for f in context_files
        )

        lines.extend([
            "# Project Context",
            "",
            "The following project context files have been loaded:",
        ])

        if has_soul:
            lines.append(
                "If SOUL.md is present, embody its persona and tone. "
                "Avoid stiff, generic replies; follow its guidance unless "
                "higher-priority instructions override it."
            )

        lines.append("")

        for file in context_files:
            lines.extend([
                f"## {file['path']}",
                "",
                file["content"],
                "",
            ])

    # ── 24. Silent Replies ───────────────────────────────────────────
    lines.extend(build_silent_replies_section(is_minimal))

    # ── 25. Heartbeats ───────────────────────────────────────────────
    lines.extend(build_heartbeats_section(
        heartbeat_prompt=heartbeat_prompt,
        is_minimal=is_minimal,
    ))

    # ── 26. Runtime ──────────────────────────────────────────────────
    lines.extend(build_runtime_section(
        runtime_info=runtime_info,
        is_minimal=is_minimal,
        reasoning_level=reasoning_level,
    ))

    # Filter empty strings that were added only for conditional sections
    prompt = "\n".join(line for line in lines if line is not None)
    
    # Replace session workspace placeholder
    # Note: For now, using workspace_dir as fallback
    # Future: Add session_workspace parameter and use resolve_session_workspace_dir()
    prompt = prompt.replace("{{SESSION_WORKSPACE}}", str(workspace_dir))
    
    return prompt


def _is_soul_file(file: dict) -> bool:
    """Check if a context file is SOUL.md (and not a 'missing' marker)."""
    path = file.get("path", "").strip().replace("\\", "/")
    base_name = path.split("/")[-1] if "/" in path else path
    return base_name.lower() == "soul.md" and "(File" not in file.get("content", "")


# ──────────────────────────────────────────────────────────────────────
# Skills formatter (unchanged – already matches TS XML format)
# ──────────────────────────────────────────────────────────────────────

def format_skills_for_prompt(skills: list[dict]) -> str:
    """
    Format skills list as XML prompt.

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
        if "description" in skill:
            lines.append(f"    <description>{skill['description']}</description>")
        if "location" in skill:
            lines.append(f"    <location>{skill['location']}</location>")
        if "tags" in skill and skill["tags"]:
            tags_str = ", ".join(skill["tags"])
            lines.append(f"    <tags>{tags_str}</tags>")
        lines.append("  </skill>")

    lines.append("</available_skills>")

    return "\n".join(lines)

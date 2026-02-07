"""Tests for system prompt section builders"""

import pytest

from openclaw.agents.system_prompt_sections import (
    CORE_TOOL_SUMMARIES,
    SILENT_REPLY_TOKEN,
    TOOL_ORDER,
    build_cli_quick_reference_section,
    build_docs_section,
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


class TestSilentReplyToken:
    def test_token_value(self):
        assert SILENT_REPLY_TOKEN == "◻️"


class TestToolingSection:
    def test_with_tools(self):
        section = build_tooling_section(["read_file", "write_file", "bash"])
        assert any("## Tooling" in line for line in section)
        assert any("read_file" in line for line in section)
        assert any("TOOLS.md" in line for line in section)

    def test_empty_tools(self):
        assert build_tooling_section([]) == []

    def test_custom_summaries(self):
        section = build_tooling_section(
            ["custom_tool"], tool_summaries={"custom_tool": "Custom desc"}
        )
        assert any("Custom desc" in line for line in section)

    def test_respects_order(self):
        section = build_tooling_section(["bash", "read_file", "write_file"])
        text = "\n".join(section)
        assert text.find("read_file") < text.find("bash")


class TestToolCallStyleSection:
    def test_present(self):
        section = build_tool_call_style_section()
        assert any("## Tool Call Style" in line for line in section)
        assert any("narrate" in line.lower() for line in section)


class TestSafetySection:
    def test_present(self):
        section = build_safety_section()
        assert any("## Safety" in line for line in section)

    def test_key_constraints(self):
        text = "\n".join(build_safety_section()).lower()
        assert "no independent goals" in text
        assert "self-preservation" in text


class TestCLIQuickReferenceSection:
    def test_present(self):
        section = build_cli_quick_reference_section()
        assert any("## OpenClaw CLI Quick Reference" in line for line in section)
        assert any("openclaw gateway start" in line for line in section)


class TestSkillsSection:
    def test_with_prompt(self):
        section = build_skills_section("<skills/>", False, "read_file")
        assert any("## Skills" in line for line in section)

    def test_minimal_omits(self):
        assert build_skills_section("<skills/>", True, "read_file") == []

    def test_no_prompt(self):
        assert build_skills_section(None, False, "read_file") == []


class TestMemorySection:
    def test_with_tools(self):
        section = build_memory_section(False, {"memory_search", "memory_get"}, "on")
        assert any("## Memory Recall" in line for line in section)

    def test_minimal_omits(self):
        assert build_memory_section(True, {"memory_search"}, "on") == []

    def test_no_tools(self):
        assert build_memory_section(False, {"read_file"}, "on") == []

    def test_citations_off(self):
        section = build_memory_section(False, {"memory_search"}, "off")
        assert any("Citations are disabled" in line for line in section)


class TestSelfUpdateSection:
    def test_with_gateway(self):
        section = build_self_update_section(True, False)
        assert any("## OpenClaw Self-Update" in line for line in section)

    def test_no_gateway(self):
        assert build_self_update_section(False, False) == []

    def test_minimal_omits(self):
        assert build_self_update_section(True, True) == []


class TestModelAliasesSection:
    def test_with_aliases(self):
        section = build_model_aliases_section(["- opus: claude-opus-4"], False)
        assert any("## Model Aliases" in line for line in section)
        assert any("opus" in line for line in section)

    def test_minimal_omits(self):
        assert build_model_aliases_section(["- opus: claude"], True) == []

    def test_empty_omits(self):
        assert build_model_aliases_section(None, False) == []


class TestDocsSection:
    def test_with_path(self):
        section = build_docs_section("/docs", False)
        assert any("## Documentation" in line for line in section)

    def test_minimal_omits(self):
        assert build_docs_section("/docs", True) == []

    def test_no_path(self):
        assert build_docs_section(None, False) == []


class TestTimeSection:
    def test_with_timezone(self):
        section = build_time_section("America/New_York")
        assert any("## Current Date & Time" in line for line in section)
        assert any("America/New_York" in line for line in section)

    def test_no_timezone(self):
        assert build_time_section(None) == []


class TestWorkspaceFilesNote:
    def test_present(self):
        section = build_workspace_files_note_section()
        assert any("## Workspace Files (injected)" in line for line in section)


class TestReplyTagsSection:
    def test_present(self):
        section = build_reply_tags_section(False)
        assert any("## Reply Tags" in line for line in section)
        assert any("reply_to_current" in line for line in section)

    def test_minimal_omits(self):
        assert build_reply_tags_section(True) == []


class TestMessagingSection:
    def test_with_message_tool(self):
        section = build_messaging_section(False, {"message"})
        assert any("## Messaging" in line for line in section)
        assert any("message tool" in line for line in section)

    def test_silent_reply_instruction(self):
        section = build_messaging_section(False, {"message"})
        text = "\n".join(section)
        assert SILENT_REPLY_TOKEN in text

    def test_minimal_omits(self):
        assert build_messaging_section(True, {"message"}) == []


class TestVoiceSection:
    def test_with_hint(self):
        section = build_voice_section(False, "Use TTS for voice.")
        assert any("## Voice (TTS)" in line for line in section)

    def test_no_hint(self):
        assert build_voice_section(False, None) == []

    def test_minimal_omits(self):
        assert build_voice_section(True, "hint") == []


class TestRuntimeSection:
    def test_with_info(self):
        info = {"agent_id": "test", "host": "localhost", "model": "claude-opus-4"}
        section = build_runtime_section(info, reasoning_level="on")
        assert any("## Runtime" in line for line in section)
        assert any("Reasoning: on" in line for line in section)

    def test_no_info(self):
        assert build_runtime_section(None) == []


class TestHeartbeatsSection:
    def test_with_prompt(self):
        section = build_heartbeats_section("ping", False)
        assert any("## Heartbeats" in line for line in section)
        assert any("HEARTBEAT_OK" in line for line in section)

    def test_minimal_omits(self):
        assert build_heartbeats_section("ping", True) == []


class TestSandboxSection:
    def test_enabled(self):
        info = {"enabled": True, "workspace_dir": "/sandbox", "workspace_access": "rw"}
        section = build_sandbox_section(info)
        assert any("## Sandbox" in line for line in section)

    def test_disabled(self):
        assert build_sandbox_section({"enabled": False}) == []

    def test_elevated(self):
        info = {
            "enabled": True,
            "elevated": {"allowed": True, "default_level": "ask"},
        }
        section = build_sandbox_section(info)
        text = "\n".join(section)
        assert "Elevated exec is available" in text
        assert "ask" in text


class TestUserIdentitySection:
    def test_with_owner(self):
        section = build_user_identity_section("Owner: +123", False)
        assert any("## User Identity" in line for line in section)

    def test_minimal_omits(self):
        assert build_user_identity_section("Owner: +123", True) == []

    def test_no_owner(self):
        assert build_user_identity_section(None, False) == []


class TestSilentRepliesSection:
    def test_present(self):
        section = build_silent_replies_section(False)
        assert any("## Silent Replies" in line for line in section)
        assert any(SILENT_REPLY_TOKEN in line for line in section)

    def test_minimal_omits(self):
        assert build_silent_replies_section(True) == []


class TestReactionGuidanceSection:
    def test_minimal_mode(self):
        section = build_reaction_guidance_section({"level": "minimal", "channel": "telegram"})
        assert any("## Reactions" in line for line in section)
        text = "\n".join(section)
        assert "MINIMAL" in text

    def test_extensive_mode(self):
        section = build_reaction_guidance_section({"level": "extensive", "channel": "discord"})
        text = "\n".join(section)
        assert "EXTENSIVE" in text

    def test_none(self):
        assert build_reaction_guidance_section(None) == []


class TestReasoningFormatSection:
    def test_with_hint(self):
        section = build_reasoning_format_section("Use <thinking> tags.")
        assert any("## Reasoning Format" in line for line in section)

    def test_none(self):
        assert build_reasoning_format_section(None) == []


class TestCoreToolSummaries:
    def test_populated(self):
        assert len(CORE_TOOL_SUMMARIES) >= 28

    def test_essential_tools(self):
        for tool in [
            "read_file",
            "write_file",
            "edit_file",
            "bash",
            "web_search",
            "gateway",
            "agents_list",
            "session_status",
        ]:
            assert tool in CORE_TOOL_SUMMARIES
            assert len(CORE_TOOL_SUMMARIES[tool]) > 0

    def test_session_status_full_desc(self):
        assert "Reasoning" in CORE_TOOL_SUMMARIES["session_status"]

    def test_tool_order_has_gateway(self):
        assert "gateway" in TOOL_ORDER
        assert "agents_list" in TOOL_ORDER

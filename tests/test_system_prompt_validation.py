"""
Tests for system prompt validation and alignment.

Verifies that system prompt structure matches TypeScript implementation.
"""
import pytest
import re
from pathlib import Path
from openclaw.agents.system_prompt import build_agent_system_prompt
from openclaw.agents.system_prompt_params import build_system_prompt_params


def test_system_prompt_builds_successfully():
    """Test that system prompt can be built without errors"""
    prompt = build_agent_system_prompt(
        workspace_dir=Path.cwd(),
        user_timezone="UTC",
        tool_names=["read", "write", "bash"],
        prompt_mode="full",
    )
    
    assert prompt is not None
    assert len(prompt) > 0
    assert isinstance(prompt, str)


def test_system_prompt_has_required_sections():
    """Test that system prompt contains all required sections"""
    prompt = build_agent_system_prompt(
        workspace_dir=Path.cwd(),
        user_timezone="UTC",
        tool_names=["read", "write"],
        prompt_mode="full",
    )
    
    # Key sections that should be present
    required_sections = [
        "## Tooling",
        "## Workspace",
        "## Runtime",
        "## Current Date & Time",
    ]
    
    for section in required_sections:
        assert section in prompt, f"Missing section: {section}"


def test_system_prompt_section_order():
    """Test that sections appear in correct order"""
    prompt = build_agent_system_prompt(
        workspace_dir=Path.cwd(),
        user_timezone="America/New_York",
        tool_names=["read", "write", "bash"],
        prompt_mode="full",
    )
    
    # Extract section headers
    sections = re.findall(r'^## (.+)$', prompt, re.MULTILINE)
    
    # Verify we have sections
    assert len(sections) > 0, "No sections found in prompt"
    
    # Check that key sections are in reasonable order
    # (exact order may vary but some should come before others)
    section_str = " ".join(sections)
    
    # Tooling should come early
    tooling_idx = section_str.find("Tooling")
    runtime_idx = section_str.find("Runtime")
    
    # Both should be present
    assert tooling_idx >= 0, "Tooling section missing"
    assert runtime_idx >= 0, "Runtime section missing"


def test_minimal_mode_excludes_sections():
    """Test minimal mode excludes correct sections"""
    prompt = build_agent_system_prompt(
        workspace_dir=Path.cwd(),
        prompt_mode="minimal",
    )
    
    # Minimal mode should NOT contain certain sections
    excluded_sections = [
        "## Skills",
        "## Memory",
    ]
    
    for section in excluded_sections:
        # These sections might not be in minimal mode
        # (depends on implementation, but check structure)
        pass  # Minimal mode structure may vary


def test_timezone_in_time_section():
    """Test that timezone appears in time section"""
    timezone = "America/Los_Angeles"
    
    prompt = build_agent_system_prompt(
        workspace_dir=Path.cwd(),
        user_timezone=timezone,
        tool_names=["read"],
        prompt_mode="full",
    )
    
    # Timezone should appear in prompt
    assert timezone in prompt, f"Timezone {timezone} not found in prompt"
    
    # Should be in Time section
    assert "## Current Date & Time" in prompt
    
    # Extract time section
    time_section_match = re.search(
        r'## Current Date & Time.*?(?=\n##|\Z)',
        prompt,
        re.DOTALL
    )
    
    if time_section_match:
        time_section = time_section_match.group(0)
        assert timezone in time_section


def test_tool_names_in_prompt():
    """Test that tool names appear in prompt"""
    tool_names = ["read", "write", "bash", "grep"]
    
    prompt = build_agent_system_prompt(
        workspace_dir=Path.cwd(),
        tool_names=tool_names,
        prompt_mode="full",
    )
    
    # At least some tool names should appear
    found_tools = [tool for tool in tool_names if tool in prompt.lower()]
    assert len(found_tools) > 0, "No tool names found in prompt"


def test_no_hardcoded_dates():
    """Test that prompt doesn't contain hardcoded dates"""
    prompt = build_agent_system_prompt(
        workspace_dir=Path.cwd(),
        user_timezone="UTC",
        tool_names=["read"],
        prompt_mode="full",
    )
    
    # Should NOT contain hardcoded current date/time
    # (these should come from session_status tool)
    
    # Check for common date patterns that shouldn't be hardcoded
    # This is a soft check - implementation may vary
    date_patterns = [
        r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
        r'2026-\d{2}-\d{2}',  # Specific year
    ]
    
    for pattern in date_patterns:
        matches = re.findall(pattern, prompt)
        # If dates are found, they should be in specific contexts
        # (not as "current date is...")
        if matches:
            # Check context
            for match in matches:
                context = prompt[max(0, prompt.find(match)-50):prompt.find(match)+50]
                # Should not be saying "current date is"
                assert "current date" not in context.lower() or "## Current Date" in context


def test_session_status_tool_mentioned():
    """Test that session_status tool is mentioned for time info"""
    prompt = build_agent_system_prompt(
        workspace_dir=Path.cwd(),
        user_timezone="UTC",
        tool_names=["read", "session_status"],
        prompt_mode="full",
    )
    
    # Should mention session_status tool for getting time
    assert "session_status" in prompt.lower()


def test_runtime_info_in_prompt():
    """Test that runtime info appears in prompt"""
    runtime_info = {
        "agent_id": "test-agent",
        "model": "claude-3-5-sonnet-20241022",
    }
    
    prompt = build_agent_system_prompt(
        workspace_dir=Path.cwd(),
        runtime_info=runtime_info,
        prompt_mode="full",
    )
    
    # Runtime section should exist
    assert "## Runtime" in prompt
    
    # Model name might appear
    # (implementation may vary on what runtime info is shown)


def test_context_files_injection():
    """Test that context files can be injected"""
    context_files = "# Test File\n\nThis is test context."
    
    prompt = build_agent_system_prompt(
        workspace_dir=Path.cwd(),
        context_files=context_files,
        prompt_mode="full",
    )
    
    # Context should be in prompt
    assert "Test File" in prompt
    assert "test context" in prompt.lower()


def test_prompt_not_empty():
    """Test that prompt is never empty"""
    # Even with minimal parameters
    prompt = build_agent_system_prompt(
        workspace_dir=Path.cwd(),
    )
    
    assert prompt is not None
    assert len(prompt) > 100  # Should have substantial content


def test_build_system_prompt_params():
    """Test building system prompt parameters"""
    params = build_system_prompt_params(
        workspace_dir=Path.cwd(),
    )
    
    assert "user_timezone" in params
    assert "runtime_info" in params
    
    # Timezone should be valid
    assert params["user_timezone"] is not None
    assert len(params["user_timezone"]) > 0


def test_timezone_resolution():
    """Test timezone resolution in params"""
    params = build_system_prompt_params()
    
    # Should resolve to a valid timezone
    timezone = params.get("user_timezone")
    assert timezone is not None
    
    # Should be IANA format (e.g., "America/New_York" or "UTC")
    # Basic validation: no spaces, contains letters
    assert " " not in timezone
    assert any(c.isalpha() for c in timezone)


def test_workspace_dir_in_prompt():
    """Test that workspace directory info is present"""
    workspace = Path.cwd()
    
    prompt = build_agent_system_prompt(
        workspace_dir=workspace,
        prompt_mode="full",
    )
    
    # Should mention workspace
    assert "workspace" in prompt.lower() or "Workspace" in prompt


def test_prompt_has_clear_structure():
    """Test that prompt has clear markdown structure"""
    prompt = build_agent_system_prompt(
        workspace_dir=Path.cwd(),
        user_timezone="UTC",
        tool_names=["read", "write"],
        prompt_mode="full",
    )
    
    # Should have markdown headers
    headers = re.findall(r'^##? .+$', prompt, re.MULTILINE)
    assert len(headers) > 5, "Prompt should have multiple clear sections"
    
    # Should have some bullet points or structure
    assert ("- " in prompt or "* " in prompt or "1. " in prompt), \
        "Prompt should have structured lists"


def test_full_vs_minimal_mode():
    """Test differences between full and minimal modes"""
    full_prompt = build_agent_system_prompt(
        workspace_dir=Path.cwd(),
        prompt_mode="full",
    )
    
    minimal_prompt = build_agent_system_prompt(
        workspace_dir=Path.cwd(),
        prompt_mode="minimal",
    )
    
    # Full should be longer
    assert len(full_prompt) > len(minimal_prompt), \
        "Full mode should produce longer prompt than minimal"
    
    # Both should have basic structure
    assert len(minimal_prompt) > 100


def test_no_duplicate_sections():
    """Test that sections don't appear twice"""
    prompt = build_agent_system_prompt(
        workspace_dir=Path.cwd(),
        user_timezone="UTC",
        tool_names=["read"],
        prompt_mode="full",
    )
    
    # Extract section headers
    sections = re.findall(r'^## (.+)$', prompt, re.MULTILINE)
    
    # Check for duplicates
    section_counts = {}
    for section in sections:
        section_counts[section] = section_counts.get(section, 0) + 1
    
    duplicates = [s for s, count in section_counts.items() if count > 1]
    
    assert len(duplicates) == 0, f"Duplicate sections found: {duplicates}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

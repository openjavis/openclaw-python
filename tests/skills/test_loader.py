"""
Tests for skill loading and precedence.
"""
import tempfile
from pathlib import Path

import pytest

from openclaw.agents.skills import load_skill_entries, Skill, SkillEntry
from openclaw.agents.skills.discovery import load_skills_from_dir
from openclaw.agents.skills.frontmatter import parse_skill_frontmatter


def test_parse_simple_skill():
    """Test parsing a simple skill with frontmatter"""
    content = """---
name: test-skill
description: "A test skill"
---

# Test Skill

This is a test skill.
"""
    
    skill = parse_skill_frontmatter(content, "/test/SKILL.md")
    
    assert skill is not None
    assert skill.name == "test-skill"
    assert skill.description == "A test skill"
    assert "This is a test skill" in skill.content


def test_parse_skill_with_metadata():
    """Test parsing skill with OpenClaw metadata"""
    content = """---
name: advanced-skill
description: "Advanced skill"
metadata:
  openclaw:
    emoji: "🎯"
    always: true
    requires:
      bins: ["git"]
      env: ["API_KEY"]
---

# Advanced Skill
"""
    
    skill = parse_skill_frontmatter(content, "/test/SKILL.md")
    
    assert skill is not None
    assert skill.metadata is not None
    assert skill.metadata.emoji == "🎯"
    assert skill.metadata.always is True
    assert skill.metadata.requires is not None
    assert skill.metadata.requires.bins == ["git"]
    assert skill.metadata.requires.env == ["API_KEY"]


def test_skill_discovery():
    """Test skill discovery from directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Create a skill directory
        skill_dir = tmppath / "test-skill"
        skill_dir.mkdir()
        
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
name: test-skill
description: "Test skill"
---

# Test Skill
""")
        
        # Discover skills
        result = load_skills_from_dir(tmppath, include_root_files=False, source="test")
        
        assert len(result.skills) == 1
        assert result.skills[0].name == "test-skill"


def test_skill_precedence():
    """Test skill loading with precedence (later overrides earlier)"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Create bundled skill
        bundled_dir = tmppath / "bundled"
        bundled_dir.mkdir()
        (bundled_dir / "test").mkdir()
        (bundled_dir / "test" / "SKILL.md").write_text("""---
name: test
description: "Bundled version"
---

# Bundled
""")
        
        # Create workspace skill (should override)
        workspace_dir = tmppath / "workspace"
        workspace_dir.mkdir()
        workspace_skills = workspace_dir / ".openclaw" / "skills"
        workspace_skills.mkdir(parents=True)
        (workspace_skills / "test").mkdir()
        (workspace_skills / "test" / "SKILL.md").write_text("""---
name: test
description: "Workspace version"
---

# Workspace
""")
        
        # Load skills
        entries = load_skill_entries(
            workspace_dir=workspace_dir,
            config={'skills': {'enabled': True}},
            managed_skills_dir=None,
            bundled_skills_dir=bundled_dir
        )
        
        # Should have workspace version (highest priority)
        assert len(entries) == 1
        assert entries[0].skill.description == "Workspace version"
        assert entries[0].source == "workspace"


def test_skill_disabled_in_config():
    """Test that skills can be disabled via config"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Create a skill
        skill_dir = tmppath / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
name: test-skill
description: "Test skill"
---

# Test
""")
        
        # Config that disables the skill
        config = {
            'skills': {
                'enabled': True,
                'entries': {
                    'test-skill': {
                        'enabled': False
                    }
                }
            }
        }
        
        # Load skills
        entries = load_skill_entries(
            workspace_dir=tmppath,
            config=config,
            managed_skills_dir=None,
            bundled_skills_dir=None
        )
        
        # Should be empty (skill disabled)
        assert len(entries) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

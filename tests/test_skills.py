"""Skills tests"""

import tempfile
from pathlib import Path

import pytest

from openclaw.skills.loader import SkillLoader
from openclaw.skills.types import Skill, SkillMetadata


def test_skill_loader():
    """Test skill loader"""
    loader = SkillLoader()

    # Create a temporary skill
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_dir = Path(tmpdir) / "test-skill"
        skill_dir.mkdir()

        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("""---
name: test-skill
description: A test skill
version: 1.0.0
tags: [test]
---

# Test Skill

This is a test skill content.
""")

        skills = loader.load_from_directory(Path(tmpdir), "test")

        assert len(skills) == 1
        assert skills[0].name == "test-skill"
        assert skills[0].metadata.description == "A test skill"
        assert "test" in skills[0].metadata.tags


def test_skill_eligibility():
    """Test skill eligibility checking"""
    loader = SkillLoader()

    skill = Skill(
        name="test",
        content="Test content",
        metadata=SkillMetadata(name="test", requires_bins=["nonexistent-binary-12345"]),
        source="test",
        path="/tmp/test",
    )

    is_eligible, reason = loader.check_eligibility(skill)
    assert not is_eligible
    assert "nonexistent-binary-12345" in reason

"""
Tests for skill eligibility checking.
"""
import platform

import pytest

from openclaw.agents.skills.types import (
    Skill,
    SkillEntry,
    OpenClawSkillMetadata,
    SkillRequires,
    SkillEligibilityContext
)
from openclaw.agents.skills.eligibility import (
    should_include_skill,
    check_skill_requirements,
    build_eligibility_context
)


def test_build_eligibility_context():
    """Test building eligibility context from environment"""
    ctx = build_eligibility_context()
    
    assert ctx.platform in ["darwin", "linux", "win32"]
    assert isinstance(ctx.available_bins, set)
    assert isinstance(ctx.env_vars, dict)


def test_skill_always_included():
    """Test that skills marked with 'always' are always included"""
    skill = Skill(
        name="test",
        description="Test",
        file_path="/test",
        content="",
        metadata=OpenClawSkillMetadata(always=True)
    )
    
    entry = SkillEntry(skill=skill, source="test", source_dir="/test")
    
    ctx = SkillEligibilityContext(
        platform="darwin",
        available_bins=set(),
        env_vars={}
    )
    
    # Should be included even with no bins/env
    assert should_include_skill(entry, None, ctx)


def test_skill_os_requirement():
    """Test OS requirement checking"""
    skill = Skill(
        name="test",
        description="Test",
        file_path="/test",
        content="",
        metadata=OpenClawSkillMetadata(os=["linux"])
    )
    
    entry = SkillEntry(skill=skill, source="test", source_dir="/test")
    
    # Darwin context
    darwin_ctx = SkillEligibilityContext(
        platform="darwin",
        available_bins=set(),
        env_vars={}
    )
    
    # Linux context
    linux_ctx = SkillEligibilityContext(
        platform="linux",
        available_bins=set(),
        env_vars={}
    )
    
    # Should not include on darwin
    assert not should_include_skill(entry, None, darwin_ctx)
    
    # Should include on linux
    assert should_include_skill(entry, None, linux_ctx)


def test_skill_bin_requirement():
    """Test binary requirement checking"""
    requires = SkillRequires(bins=["git", "gh"])
    
    # Context with git but no gh
    ctx_missing = SkillEligibilityContext(
        platform="darwin",
        available_bins={"git"},
        env_vars={}
    )
    
    # Context with both
    ctx_has_both = SkillEligibilityContext(
        platform="darwin",
        available_bins={"git", "gh"},
        env_vars={}
    )
    
    # Should fail with missing bin
    assert not check_skill_requirements(requires, ctx_missing, None)
    
    # Should pass with both bins
    assert check_skill_requirements(requires, ctx_has_both, None)


def test_skill_any_bins_requirement():
    """Test any_bins requirement (at least one must exist)"""
    requires = SkillRequires(any_bins=["npm", "yarn", "pnpm"])
    
    # Context with none
    ctx_none = SkillEligibilityContext(
        platform="darwin",
        available_bins=set(),
        env_vars={}
    )
    
    # Context with one
    ctx_has_one = SkillEligibilityContext(
        platform="darwin",
        available_bins={"yarn"},
        env_vars={}
    )
    
    # Should fail with none
    assert not check_skill_requirements(requires, ctx_none, None)
    
    # Should pass with one
    assert check_skill_requirements(requires, ctx_has_one, None)


def test_skill_env_requirement():
    """Test environment variable requirement checking"""
    requires = SkillRequires(env=["OPENAI_API_KEY"])
    
    # Context without env
    ctx_no_env = SkillEligibilityContext(
        platform="darwin",
        available_bins=set(),
        env_vars={}
    )
    
    # Context with env
    ctx_has_env = SkillEligibilityContext(
        platform="darwin",
        available_bins=set(),
        env_vars={"OPENAI_API_KEY": "sk-xxx"}
    )
    
    # Should fail without env
    assert not check_skill_requirements(requires, ctx_no_env, None)
    
    # Should pass with env
    assert check_skill_requirements(requires, ctx_has_env, None)


def test_skill_config_requirement():
    """Test config path requirement checking"""
    requires = SkillRequires(config=["api.keys.openai"])
    
    ctx = SkillEligibilityContext(
        platform="darwin",
        available_bins=set(),
        env_vars={}
    )
    
    # Config without the path
    config_missing = {"api": {"keys": {}}}
    
    # Config with the path
    config_has = {"api": {"keys": {"openai": "sk-xxx"}}}
    
    # Should fail without config path
    assert not check_skill_requirements(requires, ctx, config_missing)
    
    # Should pass with config path
    assert check_skill_requirements(requires, ctx, config_has)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

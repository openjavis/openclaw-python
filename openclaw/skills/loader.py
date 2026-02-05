"""Skills loader"""

import logging
import os
import re
from pathlib import Path
from typing import Optional

import yaml

from .eligibility import SkillEligibilityChecker
from .types import Skill, SkillMetadata

logger = logging.getLogger(__name__)


class SkillLoader:
    """Loads skills from various sources"""

    def __init__(self, config: Optional[dict] = None):
        self.skills: dict[str, Skill] = {}
        self.config = config or {}
        self.eligibility_checker = SkillEligibilityChecker(self.config)

    def load_from_directory(self, directory: Path, source: str) -> list[Skill]:
        """Load skills from a directory"""
        skills = []

        if not directory.exists():
            logger.warning(f"Skill directory does not exist: {directory}")
            return skills

        # Find all SKILL.md files
        for skill_file in directory.rglob("SKILL.md"):
            try:
                skill = self._load_skill_file(skill_file, source)
                if skill:
                    skills.append(skill)
                    # Store with precedence (later sources override)
                    self.skills[skill.name] = skill
            except Exception as e:
                logger.error(f"Failed to load skill from {skill_file}: {e}")

        logger.info(f"Loaded {len(skills)} skills from {directory} ({source})")
        return skills

    def _load_skill_file(self, file_path: Path, source: str) -> Skill | None:
        """Load a single skill file"""
        try:
            content = file_path.read_text(encoding="utf-8")

            # Parse frontmatter
            metadata = self._parse_frontmatter(content)

            if not metadata:
                logger.warning(f"No valid metadata in {file_path}")
                return None

            # Extract skill content (remove frontmatter)
            skill_content = self._extract_content(content)

            skill_name = metadata.get("name") or file_path.parent.name

            return Skill(
                name=skill_name,
                content=skill_content,
                metadata=SkillMetadata(**metadata),
                source=source,
                path=str(file_path),
            )

        except Exception as e:
            logger.error(f"Error loading skill {file_path}: {e}", exc_info=True)
            return None

    def _parse_frontmatter(self, content: str) -> dict | None:
        """Parse YAML frontmatter from skill file"""
        # Match frontmatter between --- markers
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)

        if not match:
            return None

        frontmatter_text = match.group(1)

        try:
            return yaml.safe_load(frontmatter_text)
        except Exception as e:
            logger.error(f"Failed to parse frontmatter: {e}")
            return None

    def _extract_content(self, content: str) -> str:
        """Extract skill content (without frontmatter)"""
        # Remove frontmatter
        content = re.sub(r"^---\s*\n.*?\n---\s*\n", "", content, count=1, flags=re.DOTALL)
        return content.strip()

    def check_eligibility(self, skill: Skill) -> tuple[bool, str | None]:
        """Check if a skill is eligible to run (uses enhanced checker)"""
        return self.eligibility_checker.check(skill)

    def load_all_skills(self) -> dict[str, Skill]:
        """Load skills from all sources with precedence"""
        # Load order (lowest to highest precedence):
        # 1. Bundled skills
        # 2. Managed skills
        # 3. Workspace skills

        # Bundled skills
        bundled_dir = Path(__file__).parent.parent.parent / "skills"
        self.load_from_directory(bundled_dir, "bundled")

        # Managed skills
        managed_dir = Path.home() / ".openclaw" / "skills"
        self.load_from_directory(managed_dir, "managed")

        # Workspace skills (if available)
        # TODO: Get workspace from config
        workspace_dir = Path.home() / ".openclaw" / "workspace" / "skills"
        if workspace_dir.exists():
            self.load_from_directory(workspace_dir, "workspace")

        return self.skills

    def get_eligible_skills(self) -> dict[str, Skill]:
        """Get all eligible skills"""
        eligible = {}
        for name, skill in self.skills.items():
            is_eligible, reason = self.check_eligibility(skill)
            if is_eligible:
                eligible[name] = skill
            else:
                logger.debug(f"Skill {name} not eligible: {reason}")
        return eligible


# Global skill loader
_global_loader = SkillLoader()


def get_skill_loader() -> SkillLoader:
    """Get global skill loader"""
    return _global_loader

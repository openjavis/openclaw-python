"""Patch application tool for applying unified diffs"""

import logging
import re
from pathlib import Path
from typing import Any

from .base import AgentTool, ToolResult

logger = logging.getLogger(__name__)


class ApplyPatchTool(AgentTool):
    """Apply unified diff patches to files"""

    def __init__(self):
        super().__init__()
        self.name = "apply_patch"
        self.description = "Apply unified diff patches to files"

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "patch": {"type": "string", "description": "Unified diff patch content"},
                "target_file": {
                    "type": "string",
                    "description": "Target file path (optional if specified in patch)",
                },
                "reverse": {
                    "type": "boolean",
                    "description": "Apply patch in reverse",
                    "default": False,
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "Test patch without applying",
                    "default": False,
                },
            },
            "required": ["patch"],
        }

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        """Apply patch to file"""
        patch_content = params.get("patch", "")
        target_file = params.get("target_file")
        reverse = params.get("reverse", False)
        dry_run = params.get("dry_run", False)

        if not patch_content:
            return ToolResult(success=False, content="", error="patch content required")

        try:
            # Parse patch
            patches = self._parse_patch(patch_content)

            if not patches:
                return ToolResult(
                    success=False, content="", error="No valid patches found in input"
                )

            results = []
            for patch_info in patches:
                file_path = target_file or patch_info["file"]
                if not file_path:
                    results.append("Skipped: No target file specified")
                    continue

                result = await self._apply_single_patch(
                    file_path, patch_info["hunks"], reverse, dry_run
                )
                results.append(f"{file_path}: {result}")

            output = "\n".join(results)
            return ToolResult(
                success=True,
                content=output,
                metadata={"patches_applied": len(patches), "dry_run": dry_run},
            )

        except Exception as e:
            logger.error(f"Patch application error: {e}", exc_info=True)
            return ToolResult(success=False, content="", error=str(e))

    def _parse_patch(self, patch_content: str) -> list[dict]:
        """Parse unified diff format"""
        patches = []
        current_patch = None
        current_hunk = None

        lines = patch_content.split("\n")
        for line in lines:
            # File header
            if line.startswith("--- "):
                if current_patch:
                    patches.append(current_patch)
                current_patch = {"file": None, "hunks": []}

            elif line.startswith("+++ "):
                if current_patch:
                    # Extract filename
                    match = re.match(r"\+\+\+ (?:a/)?(.+?)(?:\s|$)", line)
                    if match:
                        current_patch["file"] = match.group(1)

            elif line.startswith("@@"):
                # Hunk header
                match = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
                if match and current_patch is not None:
                    old_start = int(match.group(1))
                    old_count = int(match.group(2)) if match.group(2) else 1
                    new_start = int(match.group(3))
                    new_count = int(match.group(4)) if match.group(4) else 1

                    current_hunk = {
                        "old_start": old_start,
                        "old_count": old_count,
                        "new_start": new_start,
                        "new_count": new_count,
                        "lines": [],
                    }
                    current_patch["hunks"].append(current_hunk)

            elif current_hunk is not None:
                # Hunk content
                if line.startswith("-") or line.startswith("+") or line.startswith(" "):
                    current_hunk["lines"].append(line)

        if current_patch:
            patches.append(current_patch)

        return patches

    async def _apply_single_patch(
        self, file_path: str, hunks: list[dict], reverse: bool, dry_run: bool
    ) -> str:
        """Apply hunks to a single file"""
        path = Path(file_path).expanduser()

        if not path.exists():
            return "FAILED: File does not exist"

        # Read current file
        with open(path, encoding="utf-8") as f:
            original_lines = f.readlines()

        # Apply each hunk
        modified_lines = original_lines.copy()
        offset = 0

        for hunk in hunks:
            old_start = hunk["old_start"] - 1  # Convert to 0-based
            hunk["new_start"] - 1

            # Extract operations from hunk
            removals = []
            additions = []

            for line in hunk["lines"]:
                if line.startswith("-"):
                    if not reverse:
                        removals.append(line[1:])
                    else:
                        additions.append(line[1:])
                elif line.startswith("+"):
                    if not reverse:
                        additions.append(line[1:])
                    else:
                        removals.append(line[1:])

            # Apply changes
            actual_start = old_start + offset

            # Verify context (basic check)
            if actual_start >= len(modified_lines):
                return f"FAILED: Hunk out of range (line {old_start + 1})"

            # Remove lines
            for _ in removals:
                if actual_start < len(modified_lines):
                    modified_lines.pop(actual_start)
                    offset -= 1

            # Add lines
            for i, line in enumerate(additions):
                if not line.endswith("\n"):
                    line += "\n"
                modified_lines.insert(actual_start + i, line)
                offset += 1

        if dry_run:
            return f"OK (dry-run): Would modify {len(hunks)} hunks"

        # Write modified file
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(modified_lines)

        return f"SUCCESS: Applied {len(hunks)} hunks"

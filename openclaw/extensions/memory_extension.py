"""
Memory Extension with Auto-Recall

Automatically searches and injects relevant memories before agent starts.
Matches openclaw/extensions/memory-lancedb behavior.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from openclaw.agents.tools.memory import MemorySearchTool
from openclaw.extensions.api import ExtensionAPI
from openclaw.extensions.types import ExtensionContext

logger = logging.getLogger(__name__)


class MemoryExtension:
    """
    Memory extension with auto-recall.
    
    Automatically searches workspace memory before agent turn
    and injects relevant results into context.
    
    Matches openclaw-ts memory-lancedb extension behavior:
    - Auto-recall: Searches memory based on user prompt
    - Auto-capture: Stores important exchanges (TODO)
    - Configurable: min_score, max_results, categories
    """
    
    def __init__(
        self,
        workspace_dir: str | Path,
        auto_recall: bool = True,
        auto_capture: bool = False,  # TODO: implement
        min_score: float = 0.3,
        max_results: int = 3,
        categories: list[str] | None = None,
    ):
        """
        Initialize memory extension.
        
        Args:
            workspace_dir: Workspace directory for memory storage
            auto_recall: Enable automatic memory recall (default: True)
            auto_capture: Enable automatic memory capture (default: False)
            min_score: Minimum similarity score (0.0-1.0, default: 0.3)
            max_results: Maximum number of memories to recall (default: 3)
            categories: Filter by categories, None = all (default: None)
        """
        self.workspace_dir = str(workspace_dir)
        self.auto_recall = auto_recall
        self.auto_capture = auto_capture
        self.min_score = min_score
        self.max_results = max_results
        self.categories = categories
        
        # Initialize memory tool
        self.memory_tool: MemorySearchTool | None = None
        if auto_recall:
            try:
                self.memory_tool = MemorySearchTool(self.workspace_dir)
                logger.info(f"Memory extension initialized: {self.workspace_dir}")
            except Exception as e:
                logger.warning(f"Failed to initialize memory tool: {e}")
    
    def register(self, api: ExtensionAPI) -> None:
        """Register extension with API"""
        
        # Register before_agent_start hook for auto-recall
        if self.auto_recall and self.memory_tool:
            @api.on("before_agent_start")
            async def auto_recall_handler(
                event: dict[str, Any],
                context: ExtensionContext
            ) -> dict[str, Any] | None:
                """
                Auto-recall handler: searches memory and prepends relevant results.
                
                Matches openclaw-ts behavior at:
                openclaw/extensions/memory-lancedb/index.ts:477-503
                """
                prompt = event.get("prompt", "")
                
                # Skip if prompt too short
                if not prompt or len(prompt) < 5:
                    return None
                
                try:
                    # Search memory
                    logger.debug(f"memory: searching for '{prompt[:50]}...'")
                    
                    result = await self.memory_tool.execute(
                        tool_call_id="memory-auto-recall",
                        params={
                            "query": prompt,
                            "max_results": self.max_results,
                            "min_score": self.min_score,
                        },
                        signal=asyncio.Event(),  # Dummy signal
                        on_update=None,
                    )
                    
                    # Extract memory results
                    if result and result.details and result.details.get("results"):
                        results = result.details["results"]
                        
                        if not results:
                            return None
                        
                        # Format as context (XML format, matching openclaw-ts)
                        memory_lines = []
                        for r in results:
                            category = r.get("category", "general")
                            text = r.get("text", "")
                            score = r.get("score", 0)
                            memory_lines.append(
                                f"- [{category}] {text} (relevance: {score:.2f})"
                            )
                        
                        memory_context = "\n".join(memory_lines)
                        
                        logger.info(
                            f"memory: injecting {len(results)} memories into context"
                        )
                        
                        return {
                            "prependContext": (
                                "<relevant-memories>\n"
                                "The following memories may be relevant to this conversation:\n"
                                f"{memory_context}\n"
                                "</relevant-memories>"
                            )
                        }
                
                except Exception as err:
                    logger.warning(f"memory: recall failed: {err}")
                    return None
                
                return None
        
        # TODO: Register agent_end hook for auto-capture
        if self.auto_capture:
            @api.on("agent_end")
            async def auto_capture_handler(
                event: dict[str, Any],
                context: ExtensionContext
            ) -> None:
                """
                Auto-capture handler: stores important exchanges.
                
                TODO: Implement memory capture logic
                """
                logger.debug("memory: auto-capture not yet implemented")


def create_memory_extension(
    workspace_dir: str | Path,
    config: dict[str, Any] | None = None,
) -> MemoryExtension:
    """
    Factory function to create memory extension with config.
    
    Args:
        workspace_dir: Workspace directory
        config: Configuration dict with keys:
            - auto_recall: bool (default: True)
            - auto_capture: bool (default: False)
            - min_score: float (default: 0.3)
            - max_results: int (default: 3)
            - categories: list[str] | None (default: None)
    
    Returns:
        Configured MemoryExtension instance
    """
    config = config or {}
    
    return MemoryExtension(
        workspace_dir=workspace_dir,
        auto_recall=config.get("auto_recall", True),
        auto_capture=config.get("auto_capture", False),
        min_score=config.get("min_score", 0.3),
        max_results=config.get("max_results", 3),
        categories=config.get("categories"),
    )

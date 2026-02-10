"""Unified browser tool - agent interface to browser controller

Consolidates functionality from:
- openclaw/agents/tools/browser.py
- openclaw/agents/tools/browser_control.py
"""
from __future__ import annotations

import logging
from typing import Any

from openclaw.agents.tools.base import AgentTool, ToolResult
from openclaw.browser.controller import BrowserController

logger = logging.getLogger(__name__)


class UnifiedBrowserTool(AgentTool):
    """
    Unified browser tool for web automation
    
    Provides comprehensive browser control:
    - Navigate to URLs
    - Click elements and fill forms
    - Take screenshots and PDFs
    - Extract text and data
    - Execute JavaScript
    - Multi-page management
    """
    
    def __init__(self, headless: bool = True):
        """
        Initialize browser tool
        
        Args:
            headless: Run in headless mode
        """
        super().__init__()
        self.name = "browser"
        self.description = (
            "Control a web browser for automation, testing, and data extraction. "
            "Can navigate, interact with elements, take screenshots, extract text, and execute JavaScript."
        )
        self.headless = headless
        self.controller: BrowserController | None = None
    
    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "start",
                        "stop",
                        "navigate",
                        "screenshot",
                        "click",
                        "type",
                        "evaluate",
                        "extract_text",
                        "pdf",
                        "wait",
                        "create_page",
                        "close_page",
                        "list_pages",
                        "page_info",
                    ],
                    "description": "Browser action to perform",
                },
                "url": {
                    "type": "string",
                    "description": "URL to navigate to (for navigate action)",
                },
                "selector": {
                    "type": "string",
                    "description": "CSS selector for element (for click/type/extract_text)",
                },
                "text": {
                    "type": "string",
                    "description": "Text to type (for type action)",
                },
                "code": {
                    "type": "string",
                    "description": "JavaScript code to evaluate (for evaluate action)",
                },
                "path": {
                    "type": "string",
                    "description": "File path for screenshot/PDF",
                },
                "page_id": {
                    "type": "string",
                    "description": "Page identifier (optional, uses default if not provided)",
                },
                "wait_ms": {
                    "type": "integer",
                    "description": "Wait time in milliseconds (for wait action)",
                },
                "full_page": {
                    "type": "boolean",
                    "description": "Capture full page (for screenshot)",
                    "default": False,
                },
                "wait_until": {
                    "type": "string",
                    "enum": ["load", "domcontentloaded", "networkidle"],
                    "description": "Wait until state (for navigate)",
                    "default": "load",
                },
            },
            "required": ["action"],
        }
    
    async def _ensure_controller(self) -> None:
        """Ensure browser controller is initialized"""
        if self.controller is None:
            self.controller = BrowserController(headless=self.headless)
    
    async def execute(self, params: dict[str, Any]) -> ToolResult:
        """Execute browser action"""
        action = params.get("action")
        
        if not action:
            return ToolResult(
                success=False,
                content="",
                error="action parameter required"
            )
        
        try:
            await self._ensure_controller()
            
            # Handle actions
            if action == "start":
                await self.controller.start()
                return ToolResult(
                    success=True,
                    content="Browser started"
                )
            
            elif action == "stop":
                await self.controller.stop()
                self.controller = None
                return ToolResult(
                    success=True,
                    content="Browser stopped"
                )
            
            elif action == "navigate":
                url = params.get("url")
                if not url:
                    return ToolResult(success=False, content="", error="url required")
                
                page_id = params.get("page_id")
                wait_until = params.get("wait_until", "load")
                
                result = await self.controller.navigate(url, page_id, wait_until)
                
                return ToolResult(
                    success=True,
                    content=f"Navigated to {result['url']}\nTitle: {result['title']}"
                )
            
            elif action == "screenshot":
                path = params.get("path")
                page_id = params.get("page_id")
                full_page = params.get("full_page", False)
                
                result_path = await self.controller.screenshot(path, page_id, full_page)
                
                return ToolResult(
                    success=True,
                    content=f"Screenshot saved to {result_path}"
                )
            
            elif action == "click":
                selector = params.get("selector")
                if not selector:
                    return ToolResult(success=False, content="", error="selector required")
                
                page_id = params.get("page_id")
                
                await self.controller.click(selector, page_id)
                
                return ToolResult(
                    success=True,
                    content=f"Clicked element: {selector}"
                )
            
            elif action == "type":
                selector = params.get("selector")
                text = params.get("text")
                
                if not selector or text is None:
                    return ToolResult(
                        success=False,
                        content="",
                        error="selector and text required"
                    )
                
                page_id = params.get("page_id")
                
                await self.controller.type_text(selector, text, page_id)
                
                return ToolResult(
                    success=True,
                    content=f"Typed text into {selector}"
                )
            
            elif action == "evaluate":
                code = params.get("code")
                if not code:
                    return ToolResult(success=False, content="", error="code required")
                
                page_id = params.get("page_id")
                
                result = await self.controller.evaluate(code, page_id)
                
                return ToolResult(
                    success=True,
                    content=str(result)
                )
            
            elif action == "extract_text":
                selector = params.get("selector")
                page_id = params.get("page_id")
                
                text = await self.controller.extract_text(selector, page_id)
                
                return ToolResult(
                    success=True,
                    content=text
                )
            
            elif action == "pdf":
                path = params.get("path")
                if not path:
                    return ToolResult(success=False, content="", error="path required")
                
                page_id = params.get("page_id")
                
                result_path = await self.controller.pdf(path, page_id)
                
                return ToolResult(
                    success=True,
                    content=f"PDF saved to {result_path}"
                )
            
            elif action == "wait":
                wait_ms = params.get("wait_ms")
                if not wait_ms:
                    return ToolResult(success=False, content="", error="wait_ms required")
                
                page_id = params.get("page_id")
                
                await self.controller.wait(wait_ms, page_id)
                
                return ToolResult(
                    success=True,
                    content=f"Waited {wait_ms}ms"
                )
            
            elif action == "create_page":
                page_id = params.get("page_id")
                
                page = await self.controller.create_page(page_id)
                
                return ToolResult(
                    success=True,
                    content=f"Created page: {page_id or 'auto-generated'}"
                )
            
            elif action == "close_page":
                page_id = params.get("page_id")
                if not page_id:
                    return ToolResult(success=False, content="", error="page_id required")
                
                await self.controller.close_page(page_id)
                
                return ToolResult(
                    success=True,
                    content=f"Closed page: {page_id}"
                )
            
            elif action == "list_pages":
                pages = self.controller.list_pages()
                
                return ToolResult(
                    success=True,
                    content=f"Pages: {', '.join(pages)}"
                )
            
            elif action == "page_info":
                page_id = params.get("page_id")
                
                info = await self.controller.get_page_info(page_id)
                
                content = (
                    f"URL: {info['url']}\n"
                    f"Title: {info['title']}\n"
                    f"Viewport: {info['viewport']}"
                )
                
                return ToolResult(
                    success=True,
                    content=content
                )
            
            else:
                return ToolResult(
                    success=False,
                    content="",
                    error=f"Unknown action: {action}"
                )
        
        except Exception as e:
            logger.error(f"Browser tool error: {e}", exc_info=True)
            return ToolResult(
                success=False,
                content="",
                error=str(e)
            )
    
    async def cleanup(self) -> None:
        """Cleanup browser resources"""
        if self.controller:
            await self.controller.stop()
            self.controller = None

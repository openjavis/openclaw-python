"""Browser control tool using Playwright

DEPRECATED: This module is deprecated in favor of openclaw.browser.tools.UnifiedBrowserTool
Please use: from openclaw.browser import UnifiedBrowserTool
"""

import asyncio
import logging
import warnings
from typing import Any

from .base import AgentTool, ToolResult

logger = logging.getLogger(__name__)

warnings.warn(
    "openclaw.agents.tools.browser_control is deprecated. "
    "Use openclaw.browser.tools.UnifiedBrowserTool instead.",
    DeprecationWarning,
    stacklevel=2
)


class BrowserTool(AgentTool):
    """
    Browser control tool for web automation.
    
    Provides capabilities:
    - Navigate to URLs
    - Click elements
    - Fill forms
    - Take screenshots
    - Extract text/data
    """
    
    def __init__(self, headless: bool = True):
        super().__init__()
        self.name = "browser"
        self.description = (
            "Control a web browser to navigate, interact, and extract data from web pages. "
            "Can navigate to URLs, click elements, fill forms, take screenshots."
        )
        self.headless = headless
        self._browser = None
        self._context = None
        self._page = None
    
    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["navigate", "click", "fill", "screenshot", "extract_text", "close"],
                    "description": "Browser action to perform",
                },
                "url": {
                    "type": "string",
                    "description": "URL to navigate to (for navigate action)",
                },
                "selector": {
                    "type": "string",
                    "description": "CSS selector for element (for click/fill/extract)",
                },
                "text": {
                    "type": "string",
                    "description": "Text to fill in element (for fill action)",
                },
                "path": {
                    "type": "string",
                    "description": "File path for screenshot (for screenshot action)",
                },
            },
            "required": ["action"],
        }
    
    async def _ensure_browser(self):
        """Ensure browser is initialized"""
        if self._browser is None:
            try:
                from playwright.async_api import async_playwright
            except ImportError:
                raise RuntimeError(
                    "Playwright not installed. Install with: pip install playwright && playwright install"
                )
            
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=self.headless)
            self._context = await self._browser.new_context()
            self._page = await self._context.new_page()
    
    async def execute(self, params: dict[str, Any]) -> ToolResult:
        """Execute browser action"""
        action = params.get("action")
        
        if action == "close":
            if self._browser:
                await self._browser.close()
                await self._playwright.stop()
                self._browser = None
                self._context = None
                self._page = None
            
            return ToolResult(
                success=True,
                content="Browser closed",
            )
        
        try:
            await self._ensure_browser()
            
            if action == "navigate":
                url = params.get("url")
                if not url:
                    return ToolResult(success=False, error="Missing url parameter")
                
                await self._page.goto(url)
                title = await self._page.title()
                
                return ToolResult(
                    success=True,
                    content=f"Navigated to {url}\nPage title: {title}",
                    metadata={"url": url, "title": title},
                )
            
            elif action == "click":
                selector = params.get("selector")
                if not selector:
                    return ToolResult(success=False, error="Missing selector parameter")
                
                await self._page.click(selector)
                
                return ToolResult(
                    success=True,
                    content=f"Clicked element: {selector}",
                )
            
            elif action == "fill":
                selector = params.get("selector")
                text = params.get("text", "")
                
                if not selector:
                    return ToolResult(success=False, error="Missing selector parameter")
                
                await self._page.fill(selector, text)
                
                return ToolResult(
                    success=True,
                    content=f"Filled element {selector} with text",
                )
            
            elif action == "screenshot":
                path = params.get("path", "screenshot.png")
                await self._page.screenshot(path=path)
                
                return ToolResult(
                    success=True,
                    content=f"Screenshot saved to {path}",
                    metadata={"path": path},
                )
            
            elif action == "extract_text":
                selector = params.get("selector", "body")
                element = await self._page.query_selector(selector)
                
                if not element:
                    return ToolResult(
                        success=False,
                        error=f"Element not found: {selector}",
                    )
                
                text = await element.inner_text()
                
                return ToolResult(
                    success=True,
                    content=text,
                    metadata={"selector": selector, "length": len(text)},
                )
            
            else:
                return ToolResult(
                    success=False,
                    error=f"Unknown action: {action}",
                )
        
        except Exception as e:
            logger.error(f"Browser tool error: {e}")
            return ToolResult(
                success=False,
                error=str(e),
            )

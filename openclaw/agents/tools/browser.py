"""Browser automation tool using Playwright

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
    "openclaw.agents.tools.browser is deprecated. "
    "Use openclaw.browser.tools.UnifiedBrowserTool instead.",
    DeprecationWarning,
    stacklevel=2
)


class BrowserTool(AgentTool):
    """Browser control and automation using Playwright"""

    def __init__(self):
        super().__init__()
        self.name = "browser"
        self.description = "Control a headless browser for web automation, screenshots, and testing"
        self._browser = None
        self._context = None
        self._pages: dict[str, Any] = {}

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "start",
                        "stop",
                        "open",
                        "navigate",
                        "screenshot",
                        "click",
                        "type",
                        "get_text",
                        "wait",
                        "extract",
                        "eval",
                        "pdf",
                        "close",
                    ],
                    "description": "Browser action to perform",
                },
                "url": {"type": "string", "description": "URL to navigate to (for open/navigate)"},
                "page_id": {
                    "type": "string",
                    "description": "Page identifier (optional, uses default if not provided)",
                },
                "selector": {
                    "type": "string",
                    "description": "CSS selector for element (for click/type)",
                },
                "text": {"type": "string", "description": "Text to type (for type action)"},
                "code": {
                    "type": "string",
                    "description": "JavaScript code to evaluate (for eval action)",
                },
                "path": {"type": "string", "description": "File path to save screenshot/PDF"},
                "wait": {
                    "type": "integer",
                    "description": "Wait time in milliseconds before action",
                    "default": 0,
                },
            },
            "required": ["action"],
        }

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        """Execute browser action"""
        action = params.get("action", "")

        if not action:
            return ToolResult(success=False, content="", error="action required")

        try:
            if action == "start":
                return await self._start_browser()
            elif action == "stop":
                return await self._stop_browser()
            elif action == "open":
                return await self._open_page(params)
            elif action == "navigate":
                return await self._navigate(params)
            elif action == "screenshot":
                return await self._screenshot(params)
            elif action == "click":
                return await self._click(params)
            elif action == "type":
                return await self._type(params)
            elif action == "get_text":
                return await self._get_text(params)
            elif action == "wait":
                return await self._wait_for_selector(params)
            elif action == "extract":
                return await self._extract(params)
            elif action == "eval":
                return await self._eval(params)
            elif action == "pdf":
                return await self._generate_pdf(params)
            elif action == "close":
                return await self._close_page(params)
            else:
                return ToolResult(success=False, content="", error=f"Unknown action: {action}")

        except Exception as e:
            logger.error(f"Browser tool error: {e}", exc_info=True)
            return ToolResult(success=False, content="", error=str(e))

    async def _start_browser(self) -> ToolResult:
        """Start browser"""
        try:
            from playwright.async_api import async_playwright

            if self._browser:
                return ToolResult(success=True, content="Browser already running")

            playwright = await async_playwright().start()
            self._browser = await playwright.chromium.launch(headless=True)
            self._context = await self._browser.new_context()

            return ToolResult(success=True, content="Browser started")

        except ImportError:
            return ToolResult(
                success=False,
                content="",
                error="Playwright not installed. Install with: pip install playwright && playwright install",
            )

    async def _stop_browser(self) -> ToolResult:
        """Stop browser"""
        if not self._browser:
            return ToolResult(success=True, content="Browser not running")

        await self._browser.close()
        self._browser = None
        self._context = None
        self._pages.clear()

        return ToolResult(success=True, content="Browser stopped")

    async def _open_page(self, params: dict[str, Any]) -> ToolResult:
        """Open new page"""
        url = params.get("url", "")
        page_id = params.get("page_id", "default")

        if not url:
            return ToolResult(success=False, content="", error="url required")

        if not self._browser:
            await self._start_browser()

        page = await self._context.new_page()
        await page.goto(url)
        self._pages[page_id] = page

        return ToolResult(
            success=True, content=f"Opened {url}", metadata={"page_id": page_id, "url": url}
        )

    async def _navigate(self, params: dict[str, Any]) -> ToolResult:
        """Navigate to URL"""
        url = params.get("url", "")
        page_id = params.get("page_id", "default")

        if not url:
            return ToolResult(success=False, content="", error="url required")

        page = self._pages.get(page_id)
        if not page:
            return ToolResult(success=False, content="", error=f"Page '{page_id}' not found")

        await page.goto(url)

        return ToolResult(success=True, content=f"Navigated to {url}")

    async def _screenshot(self, params: dict[str, Any]) -> ToolResult:
        """Take screenshot"""
        page_id = params.get("page_id", "default")
        path = params.get("path", "screenshot.png")

        page = self._pages.get(page_id)
        if not page:
            return ToolResult(success=False, content="", error=f"Page '{page_id}' not found")

        await page.screenshot(path=path)

        return ToolResult(
            success=True, content=f"Screenshot saved to {path}", metadata={"path": path}
        )

    async def _click(self, params: dict[str, Any]) -> ToolResult:
        """Click element"""
        page_id = params.get("page_id", "default")
        selector = params.get("selector", "")
        wait = params.get("wait", 0)

        if not selector:
            return ToolResult(success=False, content="", error="selector required")

        page = self._pages.get(page_id)
        if not page:
            return ToolResult(success=False, content="", error=f"Page '{page_id}' not found")

        if wait > 0:
            await asyncio.sleep(wait / 1000)

        await page.click(selector)

        return ToolResult(success=True, content=f"Clicked {selector}")

    async def _type(self, params: dict[str, Any]) -> ToolResult:
        """Type text into element"""
        page_id = params.get("page_id", "default")
        selector = params.get("selector", "")
        text = params.get("text", "")

        if not selector or not text:
            return ToolResult(success=False, content="", error="selector and text required")

        page = self._pages.get(page_id)
        if not page:
            return ToolResult(success=False, content="", error=f"Page '{page_id}' not found")

        await page.fill(selector, text)

        return ToolResult(success=True, content=f"Typed '{text}' into {selector}")

    async def _type_text(self, params: dict[str, Any]) -> ToolResult:
        """Alias for _type (backward compatibility)."""
        return await self._type(params)

    async def _eval(self, params: dict[str, Any]) -> ToolResult:
        """Evaluate JavaScript"""
        page_id = params.get("page_id", "default")
        code = params.get("code", "")

        if not code:
            return ToolResult(success=False, content="", error="code required")

        page = self._pages.get(page_id)
        if not page:
            return ToolResult(success=False, content="", error=f"Page '{page_id}' not found")

        result = await page.evaluate(code)

        return ToolResult(success=True, content=str(result), metadata={"result": result})

    async def _generate_pdf(self, params: dict[str, Any]) -> ToolResult:
        """Generate PDF"""
        page_id = params.get("page_id", "default")
        path = params.get("path", "page.pdf")

        page = self._pages.get(page_id)
        if not page:
            return ToolResult(success=False, content="", error=f"Page '{page_id}' not found")

        await page.pdf(path=path)

        return ToolResult(success=True, content=f"PDF saved to {path}", metadata={"path": path})

    async def _close_page(self, params: dict[str, Any]) -> ToolResult:
        """Close page"""
        page_id = params.get("page_id", "default")

        page = self._pages.get(page_id)
        if not page:
            return ToolResult(success=False, content="", error=f"Page '{page_id}' not found")

        await page.close()
        del self._pages[page_id]

        return ToolResult(success=True, content=f"Closed page '{page_id}'")

    async def _get_text(self, params: dict[str, Any]) -> ToolResult:
        """Get text content of an element"""
        page_id = params.get("page_id", "default")
        selector = params.get("selector", "")

        if not selector:
            return ToolResult(success=False, content="", error="selector required")

        page = self._pages.get(page_id)
        if not page:
            return ToolResult(success=False, content="", error=f"Page '{page_id}' not found")

        text = await page.inner_text(selector)
        return ToolResult(success=True, content=text or "")

    async def _wait_for_selector(self, params: dict[str, Any]) -> ToolResult:
        """Wait for a CSS selector to appear in the page"""
        page_id = params.get("page_id", "default")
        selector = params.get("selector", "")
        timeout = params.get("timeout", 30000)

        if not selector:
            return ToolResult(success=False, content="", error="selector required")

        page = self._pages.get(page_id)
        if not page:
            return ToolResult(success=False, content="", error=f"Page '{page_id}' not found")

        await page.wait_for_selector(selector, timeout=timeout)
        return ToolResult(success=True, content=f"Selector '{selector}' found")

    async def _extract(self, params: dict[str, Any]) -> ToolResult:
        """Extract data from page using a dict of {key: selector} mappings"""
        page_id = params.get("page_id", "default")
        selectors: dict[str, str] = params.get("selectors", {})

        page = self._pages.get(page_id)
        if not page:
            return ToolResult(success=False, content="", error=f"Page '{page_id}' not found")

        extracted: dict[str, Any] = {}
        for key, selector in selectors.items():
            try:
                elements = await page.query_selector_all(selector)
                if len(elements) == 1:
                    extracted[key] = await elements[0].inner_text()
                else:
                    extracted[key] = [await el.inner_text() for el in elements]
            except Exception as exc:
                extracted[key] = f"error: {exc}"

        import json as _json
        return ToolResult(success=True, content=_json.dumps(extracted))

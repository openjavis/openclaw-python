"""Browser controller core - unified Playwright-based browser management"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class BrowserController:
    """
    Unified browser controller using Playwright
    
    Consolidates functionality from both previous browser implementations.
    Provides page management, navigation, interaction, and data extraction.
    """
    
    def __init__(self, headless: bool = True, user_data_dir: Path | None = None):
        """
        Initialize browser controller
        
        Args:
            headless: Run in headless mode
            user_data_dir: Optional user data directory for profiles
        """
        self.headless = headless
        self.user_data_dir = user_data_dir
        
        # Browser instances
        self._playwright = None
        self._browser = None
        self._context = None
        self._pages: dict[str, Any] = {}  # page_id -> Page
        self._default_page = None
        
        # State
        self.running = False
    
    async def start(self) -> None:
        """Start browser instance"""
        if self.running:
            logger.warning("Browser already running")
            return
        
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError(
                "Playwright not installed. Install with: pip install playwright && playwright install"
            )
        
        logger.info("Starting browser...")
        
        # Start playwright
        self._playwright = await async_playwright().start()
        
        # Launch browser
        launch_options = {"headless": self.headless}
        
        if self.user_data_dir:
            # Use persistent context
            self._context = await self._playwright.chromium.launch_persistent_context(
                str(self.user_data_dir),
                **launch_options
            )
            # Get or create page
            if self._context.pages:
                self._default_page = self._context.pages[0]
            else:
                self._default_page = await self._context.new_page()
        else:
            # Use regular browser
            self._browser = await self._playwright.chromium.launch(**launch_options)
            self._context = await self._browser.new_context()
            self._default_page = await self._context.new_page()
        
        self._pages["default"] = self._default_page
        self.running = True
        
        logger.info("Browser started successfully")
    
    async def stop(self) -> None:
        """Stop browser instance"""
        if not self.running:
            return
        
        logger.info("Stopping browser...")
        
        try:
            # Close all pages
            for page in self._pages.values():
                if page and not page.is_closed():
                    await page.close()
            
            # Close context
            if self._context:
                await self._context.close()
            
            # Close browser
            if self._browser:
                await self._browser.close()
            
            # Stop playwright
            if self._playwright:
                await self._playwright.stop()
        
        except Exception as e:
            logger.error(f"Error stopping browser: {e}", exc_info=True)
        
        finally:
            self._pages.clear()
            self._default_page = None
            self._context = None
            self._browser = None
            self._playwright = None
            self.running = False
            
            logger.info("Browser stopped")
    
    async def _ensure_running(self) -> None:
        """Ensure browser is running"""
        if not self.running:
            await self.start()
    
    def _get_page(self, page_id: str | None = None):
        """Get page by ID or default page"""
        if page_id and page_id in self._pages:
            return self._pages[page_id]
        return self._default_page
    
    async def create_page(self, page_id: str | None = None):
        """Create new page"""
        await self._ensure_running()
        
        if page_id is None:
            page_id = f"page-{len(self._pages)}"
        
        if page_id in self._pages:
            logger.warning(f"Page {page_id} already exists")
            return self._pages[page_id]
        
        page = await self._context.new_page()
        self._pages[page_id] = page
        
        logger.info(f"Created page: {page_id}")
        
        return page
    
    async def navigate(self, url: str, page_id: str | None = None, wait_until: str = "load") -> dict[str, Any]:
        """
        Navigate to URL
        
        Args:
            url: URL to navigate to
            page_id: Optional page ID
            wait_until: Wait until state ('load', 'domcontentloaded', 'networkidle')
            
        Returns:
            Navigation result
        """
        await self._ensure_running()
        
        page = self._get_page(page_id)
        
        logger.info(f"Navigating to {url}")
        
        response = await page.goto(url, wait_until=wait_until)
        
        return {
            "url": page.url,
            "title": await page.title(),
            "status": response.status if response else None,
        }
    
    async def screenshot(self, path: str | None = None, page_id: str | None = None, full_page: bool = False) -> str:
        """
        Take screenshot
        
        Args:
            path: Optional path to save screenshot
            page_id: Optional page ID
            full_page: Capture full page
            
        Returns:
            Path to screenshot file
        """
        await self._ensure_running()
        
        page = self._get_page(page_id)
        
        if path is None:
            path = f"/tmp/screenshot-{asyncio.get_event_loop().time()}.png"
        
        await page.screenshot(path=path, full_page=full_page)
        
        logger.info(f"Screenshot saved to {path}")
        
        return path
    
    async def click(self, selector: str, page_id: str | None = None) -> None:
        """
        Click element
        
        Args:
            selector: CSS selector
            page_id: Optional page ID
        """
        await self._ensure_running()
        
        page = self._get_page(page_id)
        
        await page.click(selector)
        
        logger.info(f"Clicked element: {selector}")
    
    async def type_text(self, selector: str, text: str, page_id: str | None = None) -> None:
        """
        Type text into element
        
        Args:
            selector: CSS selector
            text: Text to type
            page_id: Optional page ID
        """
        await self._ensure_running()
        
        page = self._get_page(page_id)
        
        await page.fill(selector, text)
        
        logger.info(f"Typed text into {selector}")
    
    async def evaluate(self, code: str, page_id: str | None = None) -> Any:
        """
        Evaluate JavaScript code
        
        Args:
            code: JavaScript code to evaluate
            page_id: Optional page ID
            
        Returns:
            Result of evaluation
        """
        await self._ensure_running()
        
        page = self._get_page(page_id)
        
        result = await page.evaluate(code)
        
        return result
    
    async def extract_text(self, selector: str | None = None, page_id: str | None = None) -> str:
        """
        Extract text from page or element
        
        Args:
            selector: Optional CSS selector (extracts from whole page if None)
            page_id: Optional page ID
            
        Returns:
            Extracted text
        """
        await self._ensure_running()
        
        page = self._get_page(page_id)
        
        if selector:
            element = await page.query_selector(selector)
            if element:
                text = await element.inner_text()
            else:
                text = ""
        else:
            text = await page.inner_text("body")
        
        return text
    
    async def pdf(self, path: str, page_id: str | None = None) -> str:
        """
        Generate PDF of page
        
        Args:
            path: Path to save PDF
            page_id: Optional page ID
            
        Returns:
            Path to PDF file
        """
        await self._ensure_running()
        
        page = self._get_page(page_id)
        
        await page.pdf(path=path)
        
        logger.info(f"PDF saved to {path}")
        
        return path
    
    async def wait(self, ms: int, page_id: str | None = None) -> None:
        """
        Wait for specified milliseconds
        
        Args:
            ms: Milliseconds to wait
            page_id: Optional page ID
        """
        await self._ensure_running()
        
        page = self._get_page(page_id)
        
        await page.wait_for_timeout(ms)
    
    async def close_page(self, page_id: str) -> None:
        """
        Close specific page
        
        Args:
            page_id: Page ID to close
        """
        if page_id not in self._pages:
            raise ValueError(f"Page {page_id} not found")
        
        page = self._pages[page_id]
        
        if not page.is_closed():
            await page.close()
        
        del self._pages[page_id]
        
        logger.info(f"Closed page: {page_id}")
    
    async def get_page_info(self, page_id: str | None = None) -> dict[str, Any]:
        """
        Get page information
        
        Args:
            page_id: Optional page ID
            
        Returns:
            Page info dictionary
        """
        await self._ensure_running()
        
        page = self._get_page(page_id)
        
        return {
            "url": page.url,
            "title": await page.title(),
            "viewport": page.viewport_size,
        }
    
    def list_pages(self) -> list[str]:
        """List all page IDs"""
        return list(self._pages.keys())
    
    async def __aenter__(self):
        """Context manager entry"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.stop()

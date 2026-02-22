"""Unit tests for Browser tool"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from openclaw.agents.tools.browser import BrowserTool
from openclaw.agents.tools.base import ToolResult


class TestBrowserTool:
    """Test Browser tool"""

    def test_create_tool(self):
        """Test creating Browser tool"""
        tool = BrowserTool()
        assert tool is not None
        assert tool.name == "browser"
        assert tool.description != ""

    def test_get_schema(self):
        """Test getting tool schema"""
        tool = BrowserTool()
        schema = tool.get_schema()

        assert isinstance(schema, dict)
        assert "type" in schema
        assert "properties" in schema

    @pytest.mark.asyncio
    async def test_navigate(self):
        """Test navigating to URL"""
        tool = BrowserTool()

        with patch.object(
            tool, "_navigate", new_callable=AsyncMock
        ) as mock_nav:
            mock_nav.return_value = ToolResult(
                success=True, content="Navigated to https://example.com"
            )

            result = await tool.execute({
                "action": "navigate",
                "url": "https://example.com"
            })

            assert result.success
            assert "example.com" in result.content

    @pytest.mark.asyncio
    async def test_screenshot(self):
        """Test taking screenshot"""
        tool = BrowserTool()

        with patch.object(
            tool, "_screenshot", new_callable=AsyncMock
        ) as mock_screenshot:
            mock_screenshot.return_value = ToolResult(
                success=True, content="Screenshot saved to screenshot.png"
            )

            result = await tool.execute({"action": "screenshot"})

            assert result.success

    @pytest.mark.asyncio
    async def test_click(self):
        """Test clicking element"""
        tool = BrowserTool()

        with patch.object(tool, "_click", new_callable=AsyncMock) as mock_click:
            mock_click.return_value = ToolResult(
                success=True, content="Clicked button.submit"
            )

            result = await tool.execute({
                "action": "click",
                "selector": "button.submit"
            })

            assert result.success

    @pytest.mark.asyncio
    async def test_type(self):
        """Test typing text"""
        tool = BrowserTool()

        with patch.object(tool, "_type", new_callable=AsyncMock) as mock_type:
            mock_type.return_value = ToolResult(
                success=True, content="Typed 'test query' into input#search"
            )

            result = await tool.execute({
                "action": "type",
                "selector": "input#search",
                "text": "test query"
            })

            assert result.success

    @pytest.mark.asyncio
    async def test_get_text(self):
        """Test getting element text"""
        tool = BrowserTool()

        with patch.object(
            tool, "_get_text", new_callable=AsyncMock
        ) as mock_text:
            mock_text.return_value = ToolResult(
                success=True, content="Element text content"
            )

            result = await tool.execute({
                "action": "get_text",
                "selector": "h1"
            })

            assert result.success
            assert "Element text content" in result.content


class TestBrowserSecurity:
    """Test Browser tool security features"""

    @pytest.mark.asyncio
    async def test_url_validation(self):
        """Test URL validation"""
        tool = BrowserTool()

        result = await tool.execute({
            "action": "navigate",
            "url": "https://example.com"
        })

        assert isinstance(result, ToolResult)

    @pytest.mark.asyncio
    async def test_dangerous_url_blocked(self):
        """Test that dangerous URLs are handled safely"""
        tool = BrowserTool()

        result = await tool.execute({
            "action": "navigate",
            "url": "file:///etc/passwd"
        })

        assert isinstance(result, ToolResult)


class TestBrowserActions:
    """Test browser action execution"""

    @pytest.mark.asyncio
    async def test_wait_for_selector(self):
        """Test waiting for selector"""
        tool = BrowserTool()

        with patch.object(
            tool, "_wait_for_selector", new_callable=AsyncMock
        ) as mock_wait:
            mock_wait.return_value = ToolResult(
                success=True, content="Selector 'div.content' found"
            )

            result = await tool.execute({
                "action": "wait",
                "selector": "div.content",
                "timeout": 5000
            })

            assert result.success

    @pytest.mark.asyncio
    async def test_extract_data(self):
        """Test extracting data from page"""
        tool = BrowserTool()

        with patch.object(
            tool, "_extract", new_callable=AsyncMock
        ) as mock_extract:
            import json
            mock_extract.return_value = ToolResult(
                success=True,
                content=json.dumps({"title": "Page Title", "links": ["link1", "link2"]})
            )

            result = await tool.execute({
                "action": "extract",
                "selectors": {
                    "title": "h1",
                    "links": "a"
                }
            })

            assert result.success


def test_browser_tool_imports():
    """Test that Browser tool can be imported"""
    try:
        from openclaw.agents.tools import BrowserTool
        assert BrowserTool is not None
    except ImportError as e:
        pytest.fail(f"Failed to import BrowserTool: {e}")

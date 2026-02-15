"""Integration tests for browser automation"""
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

# Mark all tests in this file as requiring browser
pytestmark = pytest.mark.skipif(
    not pytest.config.getoption("--run-browser", default=False),
    reason="Browser tests require --run-browser flag"
)


@pytest.mark.asyncio
async def test_chrome_launch_and_close():
    """Test launching and closing Chrome browser"""
    from openclaw.browser.chrome_integration import ChromeBrowser
    
    browser = ChromeBrowser(headless=True)
    
    # Check Chrome is available
    chrome_available = await browser.check_chrome()
    if not chrome_available:
        pytest.skip("Chrome not installed")
    
    # Launch browser
    await browser.launch()
    assert browser.is_running()
    
    # Close browser
    await browser.close()
    assert not browser.is_running()


@pytest.mark.asyncio
async def test_cdp_connection():
    """Test CDP connection and commands"""
    from openclaw.browser.chrome_integration import ChromeBrowser
    from openclaw.browser.cdp_helpers import CDPHelper
    
    browser = ChromeBrowser(headless=True)
    
    try:
        await browser.launch()
        
        # Connect CDP
        ws_url = browser.get_ws_endpoint()
        cdp = CDPHelper(ws_url)
        await cdp.connect()
        
        # Execute simple command
        result = await cdp.execute_command("Browser.getVersion")
        assert "product" in result
        
        await cdp.disconnect()
        
    finally:
        await browser.close()


@pytest.mark.asyncio
async def test_screenshot_capture():
    """Test screenshot capture"""
    from openclaw.browser.chrome_integration import ChromeBrowser
    from openclaw.browser.cdp_helpers import CDPHelper
    from openclaw.browser.screenshot import capture_screenshot
    
    browser = ChromeBrowser(headless=True)
    
    with TemporaryDirectory() as tmpdir:
        try:
            await browser.launch("https://example.com")
            
            ws_url = browser.get_ws_endpoint()
            cdp = CDPHelper(ws_url)
            await cdp.connect()
            
            # Wait for page load
            import asyncio
            await asyncio.sleep(2)
            
            # Capture screenshot
            screenshot_data = await capture_screenshot(cdp, format="png")
            
            assert len(screenshot_data) > 0
            # PNG magic number
            assert screenshot_data[:4] == b'\x89PNG'
            
            await cdp.disconnect()
            
        finally:
            await browser.close()


@pytest.mark.asyncio
async def test_accessibility_tree():
    """Test accessibility tree extraction"""
    from openclaw.browser.chrome_integration import ChromeBrowser
    from openclaw.browser.cdp_helpers import CDPHelper
    from openclaw.browser.role_snapshots import get_accessibility_tree
    
    browser = ChromeBrowser(headless=True)
    
    try:
        await browser.launch("https://example.com")
        
        ws_url = browser.get_ws_endpoint()
        cdp = CDPHelper(ws_url)
        await cdp.connect()
        
        # Enable accessibility domain
        await cdp.enable_domain("Accessibility")
        
        # Wait for page load
        import asyncio
        await asyncio.sleep(2)
        
        # Get accessibility tree
        ax_tree = await get_accessibility_tree(cdp)
        
        assert len(ax_tree) > 0
        assert ax_tree.root is not None
        
        await cdp.disconnect()
        
    finally:
        await browser.close()


def test_browser_module_imports():
    """Test that browser modules can be imported"""
    try:
        from openclaw.browser import cdp_helpers
        from openclaw.browser import chrome_integration
        from openclaw.browser import screenshot
        from openclaw.browser import role_snapshots
        from openclaw.browser.playwright_ai import selector
        
        assert cdp_helpers is not None
        assert chrome_integration is not None
        assert screenshot is not None
        assert role_snapshots is not None
        assert selector is not None
        
    except ImportError as e:
        pytest.fail(f"Failed to import browser modules: {e}")

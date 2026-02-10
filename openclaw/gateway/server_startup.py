"""Gateway sidecar services startup

Coordinates startup of all sidecar services.
Matches TypeScript openclaw/src/gateway/server-startup.ts
"""
from __future__ import annotations

import logging
from pathlib import Path

from .server_browser import start_browser_control_server_if_enabled
from .server_canvas import start_canvas_host_server
from ..hooks.gmail_watcher import start_gmail_watcher
from ..plugins.services import start_plugin_services

logger = logging.getLogger(__name__)


async def start_gateway_sidecars(params: dict) -> dict:
    """
    Start all Gateway sidecar services
    
    Sidecars:
    1. Browser Control Server
    2. Gmail Watcher
    3. Plugin Services
    4. Canvas Host Server
    
    Args:
        params: Dict containing:
            - cfg: Gateway config
            - plugin_registry: Plugin registry
            - workspace_dir: Workspace directory
            - log_browser: Browser logger
            - log_hooks: Hooks logger
            
    Returns:
        Dict with sidecar info
    """
    cfg = params.get("cfg", {})
    plugin_registry = params.get("plugin_registry", {})
    workspace_dir = params.get("workspace_dir", Path.home())
    log_browser = params.get("log_browser", logger)
    log_hooks = params.get("log_hooks", logger)
    
    results = {
        "browser_control": None,
        "gmail_watcher": None,
        "plugin_services": None,
        "canvas_host": None,
    }
    
    # 1. Start Browser Control Server
    try:
        browser_control = await start_browser_control_server_if_enabled(cfg)
        results["browser_control"] = browser_control
        if browser_control:
            log_browser.info(f"Browser Control Server started on port {browser_control['port']}")
    except Exception as e:
        log_browser.error(f"Browser Control Server failed to start: {e}")
    
    # 2. Start Gmail Watcher
    try:
        gmail_result = await start_gmail_watcher(cfg)
        results["gmail_watcher"] = gmail_result
        if gmail_result.get("started"):
            log_hooks.info("Gmail watcher started")
        elif gmail_result.get("reason") not in ("hooks not enabled", "no gmail account configured"):
            log_hooks.warn(f"Gmail watcher not started: {gmail_result.get('reason')}")
    except Exception as e:
        log_hooks.error(f"Gmail watcher failed to start: {e}")
    
    # 3. Start Plugin Services
    if plugin_registry:
        try:
            plugin_services = await start_plugin_services(plugin_registry, workspace_dir)
            results["plugin_services"] = plugin_services
            logger.info("Plugin services started")
        except Exception as e:
            logger.error(f"Plugin services failed to start: {e}")
    
    # 4. Start Canvas Host Server
    try:
        canvas_host = await start_canvas_host_server(cfg)
        results["canvas_host"] = canvas_host
        if canvas_host:
            logger.info(f"Canvas Host Server started on port {canvas_host['port']}")
    except Exception as e:
        logger.error(f"Canvas Host Server failed to start: {e}")
    
    return results

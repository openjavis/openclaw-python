"""
Node host runner.

Connects to gateway and executes commands (system.run, browser.proxy, etc.)
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import websockets

logger = logging.getLogger(__name__)


async def run_node_host(
    gateway_url: str,
    node_id: str,
    capabilities: list[str],
    display_name: str | None = None
):
    """
    Run node host.
    
    Connects to gateway WebSocket and handles node.invoke.request events.
    
    Supported commands:
    - system.run - Shell execution
    - system.which - Resolve executable
    - system.execApprovals.get - Read approvals
    - system.execApprovals.set - Write approvals
    - browser.proxy - Browser operations
    
    Args:
        gateway_url: Gateway WebSocket URL
        node_id: Node identifier
        capabilities: Node capabilities
        display_name: Optional display name
    """
    logger.info(f"Starting node host: {node_id}")
    logger.info(f"Capabilities: {', '.join(capabilities)}")
    
    async with websockets.connect(gateway_url) as websocket:
        # Send connect message
        connect_msg = {
            "type": "connect",
            "role": "node",
            "nodeId": node_id,
            "capabilities": capabilities,
            "displayName": display_name or node_id
        }
        
        await websocket.send(json.dumps(connect_msg))
        logger.info(f"Connected to gateway: {gateway_url}")
        
        # Listen for commands
        async for message in websocket:
            try:
                data = json.loads(message)
                event_type = data.get("type")
                
                if event_type == "node.invoke.request":
                    await _handle_invoke_request(websocket, data)
            
            except Exception as e:
                logger.error(f"Error handling message: {e}", exc_info=True)


async def _handle_invoke_request(websocket: Any, request: dict):
    """Handle node invoke request"""
    invoke_id = request.get("invokeId")
    command = request.get("command")
    params = request.get("params", {})
    
    logger.info(f"Received command: {command} (invoke: {invoke_id})")
    
    # Dispatch to handler
    result = None
    error = None
    
    try:
        if command == "system.run":
            result = await _handle_system_run(params)
        elif command == "system.which":
            result = await _handle_system_which(params)
        elif command.startswith("system.execApprovals."):
            result = await _handle_exec_approvals(command, params)
        elif command == "browser.proxy":
            result = await _handle_browser_proxy(params)
        else:
            error = f"Unknown command: {command}"
    
    except Exception as e:
        logger.error(f"Error executing {command}: {e}", exc_info=True)
        error = str(e)
    
    # Send result
    response = {
        "type": "node.invoke.result",
        "invokeId": invoke_id,
        "result": result,
        "error": error
    }
    
    await websocket.send(json.dumps(response))


async def _handle_system_run(params: dict) -> dict:
    """Handle system.run command"""
    command = params.get("command")
    cwd = params.get("cwd")
    timeout = params.get("timeout", 30000) / 1000  # ms to seconds
    
    # Execute command
    proc = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd
    )
    
    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(),
            timeout=timeout
        )
        
        return {
            "exitCode": proc.returncode,
            "stdout": stdout.decode('utf-8', errors='replace'),
            "stderr": stderr.decode('utf-8', errors='replace'),
            "timedOut": False
        }
    
    except asyncio.TimeoutError:
        proc.kill()
        return {
            "exitCode": -1,
            "stdout": "",
            "stderr": "Command timed out",
            "timedOut": True
        }


async def _handle_system_which(params: dict) -> dict:
    """Handle system.which command"""
    import shutil
    
    bin_name = params.get("bin")
    path = shutil.which(bin_name)
    
    return {
        "path": path,
        "found": path is not None
    }


async def _handle_exec_approvals(command: str, params: dict) -> dict:
    """Handle exec approvals commands"""
    from openclaw.infra.exec_approvals import load_exec_approvals, save_exec_approvals
    
    if command == "system.execApprovals.get":
        approvals = load_exec_approvals()
        return {"approvals": vars(approvals)}
    
    elif command == "system.execApprovals.set":
        # Would implement setting logic
        return {"success": True}
    
    return {"error": "Unknown exec approvals command"}


async def _handle_browser_proxy(params: dict) -> dict:
    """Handle browser.proxy command"""
    # Would forward to browser control service
    return {"error": "Browser proxy not implemented"}


__all__ = [
    "run_node_host",
]

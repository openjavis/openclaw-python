"""Gateway RPC client for CLI commands (WebSocket-based)"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import websockets
from websockets.exceptions import WebSocketException

logger = logging.getLogger(__name__)


class GatewayRPCError(Exception):
    """Raised when RPC call fails"""
    pass


class GatewayRPCClient:
    """
    WebSocket RPC client for calling gateway methods.
    
    Matches TypeScript RPC protocol:
    - Request: {"jsonrpc": "2.0", "method": "...", "params": {...}, "id": 1}
    - Response: {"jsonrpc": "2.0", "result": {...}, "id": 1}
    - Error: {"jsonrpc": "2.0", "error": {"code": ..., "message": ...}, "id": 1}
    """
    
    def __init__(self, url: str = "ws://localhost:18789", auth_token: str | None = None, config: Any = None):
        if config:
            # Derive URL from config
            port = config.gateway.port if config.gateway else 18789
            self.url = f"ws://localhost:{port}"
            # Get auth token from config if available
            if config.gateway and hasattr(config.gateway, 'auth') and config.gateway.auth:
                self.auth_token = config.gateway.auth.get('token')
            else:
                self.auth_token = auth_token
        else:
            self.url = url
            self.auth_token = auth_token
        self._request_id = 0
    
    def _next_id(self) -> int:
        """Get next request ID"""
        self._request_id += 1
        return self._request_id
    
    async def call(self, method: str, params: dict[str, Any] | None = None) -> Any:
        """
        Call an RPC method on the gateway.
        
        Args:
            method: RPC method name (e.g., "logs.tail", "gateway.cost")
            params: Method parameters
        
        Returns:
            Method result
        
        Raises:
            GatewayRPCError: If RPC call fails
        """
        if params is None:
            params = {}
        
        try:
            # Prepare connection kwargs
            connect_kwargs = {}
            if self.auth_token:
                connect_kwargs["extra_headers"] = {
                    "Authorization": f"Bearer {self.auth_token}"
                }
            
            async with websockets.connect(self.url, **connect_kwargs) as ws:
                # Step 1: Send connect handshake (unless calling connect itself)
                if method != "connect" and method != "health":
                    connect_request = {
                        "jsonrpc": "2.0",
                        "method": "connect",
                        "params": {
                            "minProtocol": 1,
                            "maxProtocol": 1,
                            "client": {
                                "name": "openclaw-python-cli",
                                "version": "1.0.0",
                                "platform": "python"
                            }
                        },
                        "id": self._next_id(),
                    }
                    await ws.send(json.dumps(connect_request))
                    
                    # Wait for connect response
                    connect_response_data = await ws.recv()
                    connect_response = json.loads(connect_response_data)
                    
                    if "error" in connect_response:
                        error = connect_response["error"]
                        raise GatewayRPCError(
                            f"Connect failed: {error.get('code')}: {error.get('message')}"
                        )
                
                # Step 2: Send actual request
                request_id = self._next_id()
                request = {
                    "jsonrpc": "2.0",
                    "method": method,
                    "params": params,
                    "id": request_id,
                }
                await ws.send(json.dumps(request))
                
                # Wait for response (may receive multiple messages for streaming)
                final_result = None
                while True:
                    response_data = await ws.recv()
                    response = json.loads(response_data)
                    
                    # Check if it's an event frame (not a response)
                    if "event" in response and "id" not in response:
                        # This is an event, ignore and continue listening
                        continue
                    
                    # Check if it's the response to our request
                    if response.get("id") == request_id:
                        # Check for error
                        if "error" in response:
                            error = response["error"]
                            raise GatewayRPCError(
                                f"RPC error {error.get('code')}: {error.get('message')}"
                            )
                        
                        # Got the final result
                        final_result = response.get("result")
                        break
                
                return final_result
        
        except WebSocketException as e:
            raise GatewayRPCError(f"WebSocket error: {e}") from e
        except json.JSONDecodeError as e:
            raise GatewayRPCError(f"Invalid JSON response: {e}") from e
        except Exception as e:
            raise GatewayRPCError(f"RPC call failed: {e}") from e
    
    async def call_agent_turn(
        self,
        message: str,
        session_id: str,
        agent_id: str | None = None,
        thinking: str | None = None,
        timeout: int = 600,
    ) -> dict[str, Any]:
        """
        Call agent.turn to run a single agent turn.
        
        Args:
            message: User message
            session_id: Session ID
            agent_id: Optional agent ID
            thinking: Thinking level (off|low|medium|high)
            timeout: Timeout in seconds
        
        Returns:
            Agent response with events
        """
        params = {
            "message": message,
            "sessionId": session_id,
        }
        if agent_id:
            params["agentId"] = agent_id
        if thinking:
            params["thinking"] = thinking
        
        return await self.call("agent", params)
    
    async def get_gateway_cost(self) -> dict[str, Any]:
        """
        Get gateway token usage and cost.
        
        Returns:
            Cost statistics (tokens, cost, sessions)
        """
        return await self.call("gateway.cost", {})
    
    async def tail_logs(
        self,
        limit: int = 200,
        max_bytes: int = 250000,
    ) -> list[str]:
        """
        Tail gateway logs.
        
        Args:
            limit: Max lines to return
            max_bytes: Max bytes to read
        
        Returns:
            List of log lines
        """
        result = await self.call("logs.tail", {
            "limit": limit,
            "maxBytes": max_bytes,
        })
        return result.get("lines", [])
    
    async def send_message(
        self,
        channel: str,
        target: str,
        text: str,
        reply_to: str | None = None,
    ) -> str:
        """
        Send a message via channel.
        
        Args:
            channel: Channel ID (telegram, discord, etc.)
            target: Target user/chat ID
            text: Message text
            reply_to: Optional message ID to reply to
        
        Returns:
            Message ID
        """
        params = {
            "channel": channel,
            "target": target,
            "text": text,
        }
        if reply_to:
            params["replyTo"] = reply_to
        
        result = await self.call("message.send", params)
        return result.get("messageId")


def get_gateway_url() -> str:
    """Get gateway URL from config"""
    from ..config.loader import load_config
    
    config = load_config()
    port = config.gateway.port if config.gateway else 18789
    return f"ws://localhost:{port}"


def get_auth_token() -> str | None:
    """Get auth token from config"""
    from ..config.loader import load_config
    
    config = load_config()
    if config.gateway and config.gateway.auth:
        return config.gateway.auth.token
    return None


async def create_client() -> GatewayRPCClient:
    """Create configured RPC client"""
    url = get_gateway_url()
    token = get_auth_token()
    return GatewayRPCClient(url, token)

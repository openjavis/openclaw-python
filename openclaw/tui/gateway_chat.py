"""Gateway WebSocket client for the TUI.

Mirrors TypeScript openclaw/src/tui/gateway-chat.ts.

Protocol sequence:
1. Connect to ws://localhost:{port}
2. Receive connect.challenge (nonce)
3. Send connect request with auth token
4. Use chat.send / chat.history / chat.abort RPC methods
5. Process streaming events: started, delta, final, error, aborted
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from typing import Any, Callable

logger = logging.getLogger(__name__)

DEFAULT_GATEWAY_PORT = 18789
RECONNECT_DELAY_MS = 2000
MAX_RECONNECT_ATTEMPTS = 10


class GatewayChatEvent:
    """Represents a chat streaming event from the gateway."""

    __slots__ = ("type", "run_id", "session_key", "message", "text", "error")

    def __init__(
        self,
        type: str,
        run_id: str = "",
        session_key: str = "",
        message: dict | None = None,
        text: str = "",
        error: str = "",
    ) -> None:
        self.type = type          # "started" | "delta" | "final" | "error" | "aborted"
        self.run_id = run_id
        self.session_key = session_key
        self.message = message
        self.text = text
        self.error = error


class GatewayChat:
    """Manages the WebSocket connection to the gateway and chat RPCs.

    Matches TypeScript GatewayChat in src/tui/gateway-chat.ts.
    """

    def __init__(
        self,
        port: int = DEFAULT_GATEWAY_PORT,
        auth_token: str | None = None,
        on_event: Callable[[GatewayChatEvent], None] | None = None,
    ) -> None:
        self._port = port
        self._auth_token = auth_token or os.environ.get("OPENCLAW_TOKEN", "")
        self._on_event = on_event
        self._ws = None
        self._connected = False
        self._request_id_counter = 0
        self._pending: dict[str, asyncio.Future] = {}
        self._recv_task: asyncio.Task | None = None

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Establish authenticated WebSocket connection to the gateway."""
        try:
            import websockets  # type: ignore[import]
        except ImportError:
            try:
                import aiohttp
                await self._connect_aiohttp()
                return
            except Exception as exc:
                raise RuntimeError(f"No WebSocket library available: {exc}")

        url = f"ws://localhost:{self._port}"
        logger.debug(f"Connecting to gateway: {url}")
        self._ws = await websockets.connect(url)

        # Receive challenge
        raw = await self._ws.recv()
        challenge_msg = json.loads(raw)
        if challenge_msg.get("event") == "connect.challenge":
            nonce = challenge_msg.get("nonce", "")
            await self._authenticate(nonce)

        self._connected = True
        self._recv_task = asyncio.create_task(self._receive_loop())
        logger.info("Gateway connection established")

    async def _connect_aiohttp(self) -> None:
        import aiohttp
        session = aiohttp.ClientSession()
        url = f"ws://localhost:{self._port}"
        self._ws = await session.ws_connect(url)
        # Challenge
        msg = await self._ws.receive()
        if msg.type == aiohttp.WSMsgType.TEXT:
            data = json.loads(msg.data)
            if data.get("event") == "connect.challenge":
                await self._authenticate(data.get("nonce", ""))
        self._connected = True
        self._recv_task = asyncio.create_task(self._receive_loop_aiohttp())

    async def _authenticate(self, nonce: str) -> None:
        payload = {
            "type": "connect",
            "token": self._auth_token,
            "nonce": nonce,
        }
        await self._send_raw(json.dumps(payload))

    async def disconnect(self) -> None:
        """Close the connection."""
        self._connected = False
        if self._recv_task:
            self._recv_task.cancel()
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # RPC methods
    # ------------------------------------------------------------------

    async def chat_send(
        self,
        session_key: str,
        message: str,
        idempotency_key: str | None = None,
    ) -> str:
        """Send chat.send RPC. Returns run_id."""
        ikey = idempotency_key or str(uuid.uuid4())
        result = await self._rpc("chat.send", {
            "sessionKey": session_key,
            "message": message,
            "idempotencyKey": ikey,
        })
        return result.get("runId", ikey)

    async def chat_history(
        self,
        session_key: str,
        limit: int = 200,
    ) -> list[dict]:
        """Fetch chat history."""
        result = await self._rpc("chat.history", {
            "sessionKey": session_key,
            "limit": limit,
        })
        return result.get("messages", [])

    async def chat_abort(self, session_key: str, run_id: str | None = None) -> bool:
        """Abort current run."""
        params: dict[str, Any] = {"sessionKey": session_key}
        if run_id:
            params["runId"] = run_id
        result = await self._rpc("chat.abort", params)
        return result.get("aborted", False)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _next_request_id(self) -> str:
        self._request_id_counter += 1
        return f"tui-{self._request_id_counter}"

    async def _rpc(self, method: str, params: dict) -> dict:
        if not self._connected:
            await self.connect()
        req_id = self._next_request_id()
        payload = json.dumps({
            "type": "request",
            "id": req_id,
            "method": method,
            "params": params,
        })
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending[req_id] = future
        await self._send_raw(payload)
        try:
            return await asyncio.wait_for(future, timeout=30.0)
        except asyncio.TimeoutError:
            self._pending.pop(req_id, None)
            raise TimeoutError(f"RPC {method} timed out")

    async def _send_raw(self, text: str) -> None:
        if self._ws is None:
            raise RuntimeError("Not connected")
        try:
            if hasattr(self._ws, "send"):
                await self._ws.send(text)
            elif hasattr(self._ws, "send_str"):
                await self._ws.send_str(text)
        except Exception as exc:
            logger.warning(f"Failed to send: {exc}")

    async def _receive_loop(self) -> None:
        """WebSocket receive loop (websockets library)."""
        try:
            async for raw in self._ws:
                self._handle_raw(raw)
        except Exception as exc:
            logger.debug(f"Receive loop ended: {exc}")
            self._connected = False

    async def _receive_loop_aiohttp(self) -> None:
        """WebSocket receive loop (aiohttp)."""
        import aiohttp
        try:
            async for msg in self._ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    self._handle_raw(msg.data)
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    break
        except Exception as exc:
            logger.debug(f"Receive loop (aiohttp) ended: {exc}")
            self._connected = False

    def _handle_raw(self, raw: str) -> None:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return

        msg_type = data.get("type")

        # RPC response
        if msg_type == "response":
            req_id = data.get("id")
            future = self._pending.pop(req_id, None)
            if future and not future.done():
                if "error" in data:
                    future.set_exception(RuntimeError(data["error"]))
                else:
                    future.set_result(data.get("result", {}))
            return

        # Streaming event (chat.delta, chat.final, etc.)
        if msg_type == "event":
            event_name = data.get("event", "")
            payload = data.get("payload", {})
            if event_name.startswith("chat"):
                self._dispatch_chat_event(event_name, payload)

    def _dispatch_chat_event(self, event_name: str, payload: dict) -> None:
        state = payload.get("state", event_name.split(".")[-1] if "." in event_name else event_name)
        evt = GatewayChatEvent(
            type=state,
            run_id=payload.get("runId", ""),
            session_key=payload.get("sessionKey", ""),
            message=payload.get("message"),
            text=payload.get("message", {}).get("content", [{}])[0].get("text", "") if payload.get("message") else "",
            error=payload.get("errorMessage", ""),
        )
        if self._on_event:
            try:
                self._on_event(evt)
            except Exception as exc:
                logger.warning(f"on_event handler error: {exc}")

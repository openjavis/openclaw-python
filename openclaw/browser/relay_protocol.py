"""
Chrome extension relay protocol definitions.

Defines message types and structures for communication between:
- Chrome extension
- Relay server
- CDP clients
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


@dataclass
class ForwardCDPCommand:
    """Message from extension forwarding a CDP command"""
    type: Literal["forwardCDPCommand"] = "forwardCDPCommand"
    id: int | None = None
    method: str | None = None
    params: dict | None = None


@dataclass
class ForwardCDPEvent:
    """Message from extension forwarding a CDP event"""
    type: Literal["forwardCDPEvent"] = "forwardCDPEvent"
    method: str | None = None
    params: dict | None = None


@dataclass
class Pong:
    """Heartbeat response from extension"""
    type: Literal["pong"] = "pong"


@dataclass
class CDPCommand:
    """CDP command from client to extension"""
    id: int
    method: str
    params: dict | None = None


@dataclass
class CDPResponse:
    """CDP response from extension to client"""
    id: int
    result: dict | None = None
    error: dict | None = None


@dataclass
class CDPEvent:
    """CDP event from extension to clients"""
    method: str
    params: dict | None = None


@dataclass
class RelayStatus:
    """Relay server status"""
    connected: bool
    extension_connected: bool
    cdp_clients_count: int
    relay_port: int | None = None


__all__ = [
    "ForwardCDPCommand",
    "ForwardCDPEvent",
    "Pong",
    "CDPCommand",
    "CDPResponse",
    "CDPEvent",
    "RelayStatus",
]

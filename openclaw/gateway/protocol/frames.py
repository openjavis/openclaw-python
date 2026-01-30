"""Protocol frame definitions for Gateway WebSocket communication"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class ErrorShape(BaseModel):
    """Error response structure"""

    code: str
    message: str
    details: dict[str, Any] | None = None


class RequestFrame(BaseModel):
    """Client request frame"""

    type: Literal["req"] = "req"
    id: str = Field(..., description="Unique request ID")
    method: str = Field(..., description="Method name (e.g., 'connect', 'agent', 'chat.send')")
    params: dict[str, Any] | None = Field(default=None, description="Method parameters")


class ResponseFrame(BaseModel):
    """Server response frame"""

    type: Literal["res"] = "res"
    id: str = Field(..., description="Request ID this response corresponds to")
    ok: bool = Field(..., description="Success indicator")
    payload: Any | None = Field(default=None, description="Response data")
    error: ErrorShape | None = Field(default=None, description="Error information if ok=False")


class EventFrame(BaseModel):
    """Server event frame (broadcast)"""

    type: Literal["event"] = "event"
    event: str = Field(..., description="Event name (e.g., 'agent', 'chat', 'presence')")
    payload: Any | None = Field(default=None, description="Event data")
    seq: int | None = Field(default=None, description="Sequence number for ordering")
    stateVersion: dict[str, Any] | None = Field(
        default=None, description="State version information"
    )


# Handshake specific frames
class ConnectRequest(BaseModel):
    """Connection handshake request"""

    minProtocol: int = Field(default=1, description="Minimum supported protocol version")
    maxProtocol: int = Field(default=1, description="Maximum supported protocol version")
    client: dict[str, Any] = Field(..., description="Client information")
    role: str = Field(default="client", description="Client role (client/node)")
    scopes: list[str] | None = Field(default=None, description="Requested scopes")
    auth: dict[str, Any] | None = Field(default=None, description="Authentication credentials")


class HelloResponse(BaseModel):
    """Connection handshake response"""

    protocol: int = Field(..., description="Negotiated protocol version")
    server: dict[str, Any] = Field(..., description="Server information")
    features: dict[str, bool] = Field(default_factory=dict, description="Enabled features")
    snapshot: dict[str, Any] | None = Field(default=None, description="Initial state snapshot")
    policy: dict[str, Any] | None = Field(default=None, description="Access policy")
    auth: dict[str, Any] | None = Field(default=None, description="Auth tokens (device token)")

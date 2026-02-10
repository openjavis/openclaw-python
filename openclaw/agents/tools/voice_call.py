"""Voice call tool using Twilio/Telnyx"""

import logging
from typing import Any

from .base import AgentTool, ToolResult

logger = logging.getLogger(__name__)


class VoiceCallTool(AgentTool):
    """Voice call functionality using telephony providers"""

    def __init__(self):
        super().__init__()
        self.name = "voice_call"
        self.description = "Make and receive voice calls using Twilio or other providers"
        self._provider = None
        self._client = None

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["call", "hangup", "status", "list_calls"],
                    "description": "Voice call action",
                },
                "to": {"type": "string", "description": "Phone number to call (E.164 format)"},
                "from": {"type": "string", "description": "Caller phone number"},
                "message": {"type": "string", "description": "Message to speak (TTS)"},
                "call_id": {"type": "string", "description": "Call identifier (for hangup/status)"},
            },
            "required": ["action"],
        }

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        """Execute voice call action"""
        action = params.get("action", "")

        if not action:
            return ToolResult(success=False, content="", error="action required")

        try:
            if action == "call":
                return await self._make_call(params)
            elif action == "hangup":
                return await self._hangup(params)
            elif action == "status":
                return await self._call_status(params)
            elif action == "list_calls":
                return await self._list_calls(params)
            else:
                return ToolResult(success=False, content="", error=f"Unknown action: {action}")

        except Exception as e:
            logger.error(f"Voice call tool error: {e}", exc_info=True)
            return ToolResult(success=False, content="", error=str(e))

    async def _make_call(self, params: dict[str, Any]) -> ToolResult:
        """Make outbound call"""
        to_number = params.get("to", "")
        from_number = params.get("from", "")
        message = params.get("message", "")

        if not all([to_number, from_number]):
            return ToolResult(success=False, content="", error="to and from phone numbers required")

        try:
            # Try Twilio
            import os

            from twilio.rest import Client

            account_sid = os.getenv("TWILIO_ACCOUNT_SID")
            auth_token = os.getenv("TWILIO_AUTH_TOKEN")

            if not account_sid or not auth_token:
                return ToolResult(
                    success=False,
                    content="",
                    error="TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN not set",
                )

            client = Client(account_sid, auth_token)

            # Make call with TTS message
            call = client.calls.create(
                to=to_number,
                from_=from_number,
                twiml=f"<Response><Say>{message}</Say></Response>" if message else None,
                url="http://demo.twilio.com/docs/voice.xml",  # Default if no message
            )

            return ToolResult(
                success=True,
                content=f"Call initiated to {to_number}",
                metadata={"call_sid": call.sid, "status": call.status},
            )

        except ImportError:
            return ToolResult(
                success=False,
                content="",
                error="twilio package not installed. Install with: pip install twilio",
            )
        except Exception as e:
            return ToolResult(success=False, content="", error=str(e))

    async def _hangup(self, params: dict[str, Any]) -> ToolResult:
        """Hang up call"""
        call_id = params.get("call_id", "")

        if not call_id:
            return ToolResult(success=False, content="", error="call_id required")

        try:
            import os
            from twilio.rest import Client
            
            account_sid = os.getenv("TWILIO_ACCOUNT_SID")
            auth_token = os.getenv("TWILIO_AUTH_TOKEN")
            
            if not account_sid or not auth_token:
                return ToolResult(success=False, content="", error="Twilio credentials not set")
            
            client = Client(account_sid, auth_token)
            call = client.calls(call_id).update(status="completed")
            
            return ToolResult(
                success=True,
                content=f"Call {call_id} ended",
                metadata={"call_sid": call.sid, "status": call.status},
            )
        except ImportError:
            return ToolResult(success=False, content="", error="twilio not installed")
        except Exception as e:
            logger.error(f"Hangup error: {e}", exc_info=True)
            return ToolResult(success=False, content="", error=str(e))

    async def _call_status(self, params: dict[str, Any]) -> ToolResult:
        """Get call status"""
        call_id = params.get("call_id", "")

        if not call_id:
            return ToolResult(success=False, content="", error="call_id required")

        try:
            import os
            from twilio.rest import Client
            
            account_sid = os.getenv("TWILIO_ACCOUNT_SID")
            auth_token = os.getenv("TWILIO_AUTH_TOKEN")
            
            if not account_sid or not auth_token:
                return ToolResult(success=False, content="", error="Twilio credentials not set")
            
            client = Client(account_sid, auth_token)
            call = client.calls(call_id).fetch()
            
            return ToolResult(
                success=True,
                content=f"Call status: {call.status}",
                metadata={
                    "call_sid": call.sid,
                    "status": call.status,
                    "duration": call.duration,
                    "from": call.from_,
                    "to": call.to,
                },
            )
        except ImportError:
            return ToolResult(success=False, content="", error="twilio not installed")
        except Exception as e:
            logger.error(f"Status error: {e}", exc_info=True)
            return ToolResult(success=False, content="", error=str(e))

    async def _list_calls(self, params: dict[str, Any]) -> ToolResult:
        """List recent calls"""
        try:
            import os
            from twilio.rest import Client
            
            account_sid = os.getenv("TWILIO_ACCOUNT_SID")
            auth_token = os.getenv("TWILIO_AUTH_TOKEN")
            
            if not account_sid or not auth_token:
                return ToolResult(success=False, content="", error="Twilio credentials not set")
            
            client = Client(account_sid, auth_token)
            limit = params.get("limit", 20)
            calls = client.calls.list(limit=limit)
            
            call_list = [{
                "sid": c.sid,
                "from": c.from_,
                "to": c.to,
                "status": c.status,
                "duration": c.duration,
            } for c in calls]
            
            return ToolResult(
                success=True,
                content=f"Found {len(call_list)} calls",
                metadata={"calls": call_list},
            )
        except ImportError:
            return ToolResult(success=False, content="", error="twilio not installed")
        except Exception as e:
            logger.error(f"List calls error: {e}", exc_info=True)
            return ToolResult(success=False, content="", error=str(e))


# Note: Full voice call implementation requires:
# 1. Twilio/Telnyx account and credentials
# 2. Webhook endpoint for incoming calls
# 3. Real-time audio streaming for STT/TTS
# 4. WebRTC support for browser-based calls
# 5. Call state management

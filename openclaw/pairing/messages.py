"""Pairing message formatting"""
from __future__ import annotations


def format_pairing_request_message(
    code: str,
    channel: str,
    id_label: str = "ID",
) -> str:
    """
    Format pairing request message
    
    Args:
        code: Pairing code
        channel: Channel name
        id_label: Label for ID (e.g., "user ID", "phone number")
        
    Returns:
        Formatted message
    """
    return f"""🔐 **Authorization Required**

Your {id_label} is not authorized to send direct messages.

To request access, provide this pairing code to the bot owner:

**Pairing Code:** `{code}`

The owner can approve your request with:
```
openclaw pairing approve {channel} {code}
```

This code expires in 1 hour."""


def format_approval_notification(sender_id: str, channel: str) -> str:
    """
    Format approval notification message
    
    Args:
        sender_id: Sender ID that was approved
        channel: Channel name
        
    Returns:
        Formatted message
    """
    return f"""✅ **Access Approved**

Your account has been authorized to send direct messages.

You can now chat with the bot freely!

Channel: {channel}
Your ID: {sender_id}"""


def format_denial_message(sender_id: str) -> str:
    """
    Format denial message
    
    Args:
        sender_id: Sender ID
        
    Returns:
        Formatted message
    """
    return f"""❌ **Access Denied**

Your pairing request has been denied.

If you believe this is an error, please contact the bot owner."""


def format_pairing_list_message(requests: list, channel: str) -> str:
    """
    Format pairing request list message
    
    Args:
        requests: List of pairing requests
        channel: Channel name
        
    Returns:
        Formatted message
    """
    if not requests:
        return f"No pending pairing requests for **{channel}**."
    
    message = f"📋 **Pending Pairing Requests for {channel}**\n\n"
    
    for i, req in enumerate(requests, 1):
        message += f"{i}. **Code:** `{req.code}`\n"
        message += f"   ID: `{req.id}`\n"
        message += f"   Created: {req.created_at}\n"
        
        if req.meta:
            message += f"   Meta: {req.meta}\n"
        
        message += "\n"
    
    message += f"\nApprove with: `openclaw pairing approve {channel} <code>`"
    
    return message

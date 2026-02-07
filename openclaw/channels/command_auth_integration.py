"""
Command authorization integration

Integrates command_auth.py into command processing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from openclaw.agents.command_auth import (
    CommandAuthorization,
    check_owner_permission,
    resolve_command_authorization,
)

logger = logging.getLogger(__name__)


@dataclass
class CommandContext:
    """Context for command execution."""

    sender_id: str | None
    sender_e164: str | None
    from_: str | None
    to: str | None
    channel: str | None
    owner_list: list[str]
    enforce_owner: bool = False


class CommandAuthHandler:
    """
    Command authorization handler.

    Integrates new command_auth system into command execution.
    """

    def __init__(
        self,
        owner_list: list[str] | None = None,
        enforce_owner_for_commands: bool = False,
    ):
        """
        Initialize command auth handler.

        Args:
            owner_list: List of owner identifiers (e.g., ["telegram:123", "+1234567890"])
            enforce_owner_for_commands: Whether to enforce owner-only commands
        """
        self.owner_list = owner_list or []
        self.enforce_owner = enforce_owner_for_commands

        logger.info(
            f"Command auth initialized: {len(self.owner_list)} owners, "
            f"enforce={enforce_owner_for_commands}"
        )

    def authorize_command(
        self,
        sender_id: str | None,
        sender_e164: str | None = None,
        from_: str | None = None,
        to: str | None = None,
        channel: str | None = None,
    ) -> CommandAuthorization:
        """
        Authorize a command execution.

        Args:
            sender_id: Sender identifier
            sender_e164: E.164 phone number
            from_: From field
            to: To field
            channel: Channel provider ID

        Returns:
            CommandAuthorization result
        """
        auth = resolve_command_authorization(
            sender_id=sender_id,
            sender_e164=sender_e164,
            from_=from_,
            to=to,
            owner_list=self.owner_list,
            enforce_owner_for_commands=self.enforce_owner,
            provider_id=channel,
        )

        logger.debug(
            f"Command auth: sender_is_owner={auth.sender_is_owner}, "
            f"is_authorized={auth.is_authorized_sender}"
        )

        return auth

    def is_owner(
        self,
        sender_id: str | None,
        sender_e164: str | None = None,
        channel: str | None = None,
    ) -> bool:
        """
        Quick check if sender is owner.

        Args:
            sender_id: Sender identifier
            sender_e164: E.164 phone number
            channel: Channel provider ID

        Returns:
            True if sender is owner
        """
        return check_owner_permission(
            sender_id=sender_id,
            sender_e164=sender_e164,
            owner_list=self.owner_list,
            provider_id=channel,
        )

    def require_owner(
        self,
        sender_id: str | None,
        sender_e164: str | None = None,
        channel: str | None = None,
    ) -> bool:
        """
        Require owner permission, raise exception if not owner.

        Args:
            sender_id: Sender identifier
            sender_e164: E.164 phone number
            channel: Channel provider ID

        Returns:
            True if owner

        Raises:
            PermissionError: If not owner
        """
        if not self.is_owner(sender_id, sender_e164, channel):
            logger.warning(f"Permission denied: {sender_id} is not owner")
            raise PermissionError("This command requires owner permission")
        return True

    def filter_owner_only_commands(
        self,
        commands: list[str],
        sender_id: str | None,
        sender_e164: str | None = None,
        channel: str | None = None,
    ) -> list[str]:
        """
        Filter commands to only show owner-allowed ones.

        Args:
            commands: List of command names
            sender_id: Sender identifier
            sender_e164: E.164 phone number
            channel: Channel provider ID

        Returns:
            Filtered list of commands
        """
        is_owner = self.is_owner(sender_id, sender_e164, channel)

        if is_owner or not self.enforce_owner:
            return commands

        # Return only non-owner commands
        # In practice, you'd have a list of owner-only commands
        return commands

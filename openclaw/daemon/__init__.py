"""Daemon service management for OpenClaw.

Allows OpenClaw to run as a system service.
"""

from __future__ import annotations

from .launchd import generate_launchd_plist
from .service import DaemonService, install_service, uninstall_service
from .systemd import generate_systemd_unit

__all__ = [
    "DaemonService",
    "install_service",
    "uninstall_service",
    "generate_systemd_unit",
    "generate_launchd_plist",
]

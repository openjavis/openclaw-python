"""Systemd unit file generation."""

from __future__ import annotations


def generate_systemd_unit(
    service_name: str, working_dir: str, python_path: str, user: str = "openclaw"
) -> str:
    """Generate systemd unit file content.

    Args:
        service_name: Service name
        working_dir: Working directory
        python_path: Python interpreter path
        user: User to run service as

    Returns:
        Systemd unit file content
    """
    return f"""[Unit]
Description=OpenClaw AI Agent Service
After=network.target

[Service]
Type=simple
User={user}
WorkingDirectory={working_dir}
ExecStart={python_path} -m openclaw.cli gateway start
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""

"""Launchd plist file generation."""

from __future__ import annotations


def generate_launchd_plist(
    service_name: str,
    working_dir: str,
    python_path: str
) -> str:
    """Generate launchd plist file content.
    
    Args:
        service_name: Service name
        working_dir: Working directory
        python_path: Python interpreter path
    
    Returns:
        Launchd plist content
    """
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.openclaw.{service_name}</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>-m</string>
        <string>openclaw.cli</string>
        <string>start</string>
        <string>--port</string>
        <string>18789</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>{working_dir}</string>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <true/>
    
    <key>StandardOutPath</key>
    <string>/Users/Shared/.openclaw/logs/gateway.out.log</string>
    
    <key>StandardErrorPath</key>
    <string>/Users/Shared/.openclaw/logs/gateway.err.log</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>
"""

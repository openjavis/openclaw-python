"""Safe launchd configuration - Manual start only."""

from __future__ import annotations


def generate_launchd_plist_safe(
    service_name: str,
    working_dir: str,
    python_path: str
) -> str:
    """Generate safe launchd plist (manual start, no auto-restart).
    
    This configuration:
    - Does NOT auto-start on boot (RunAtLoad = false)
    - Does NOT auto-restart on crash (KeepAlive = false)
    - Requires manual start with: launchctl start com.openclaw.openclaw
    
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
    
    <!-- Safe mode: No auto-start on boot -->
    <key>RunAtLoad</key>
    <false/>
    
    <!-- Safe mode: No auto-restart on crash -->
    <key>KeepAlive</key>
    <false/>
    
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

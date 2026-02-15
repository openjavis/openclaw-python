"""Service management."""

from __future__ import annotations

import sys
import platform
from pathlib import Path
from typing import Optional


class DaemonService:
    """Daemon service manager."""
    
    def __init__(self, service_name: str = "openclaw"):
        """Initialize service manager.
        
        Args:
            service_name: Service name
        """
        self.service_name = service_name
        self.platform = platform.system()
    
    def is_installed(self) -> bool:
        """Check if service is installed.
        
        Returns:
            True if installed
        """
        if self.platform == "Linux":
            return self._is_systemd_installed()
        elif self.platform == "Darwin":
            return self._is_launchd_installed()
        return False
    
    def is_running(self) -> bool:
        """Check if service is running.
        
        Returns:
            True if running
        """
        if not self.is_installed():
            return False
        
        if self.platform == "Linux":
            return self._is_systemd_running()
        elif self.platform == "Darwin":
            return self._is_launchd_running()
        return False
    
    def _is_systemd_installed(self) -> bool:
        """Check if systemd service is installed."""
        service_file = Path(f"/etc/systemd/system/{self.service_name}.service")
        return service_file.exists()
    
    def _is_launchd_installed(self) -> bool:
        """Check if launchd service is installed."""
        plist_file = Path(f"~/Library/LaunchAgents/com.openclaw.{self.service_name}.plist").expanduser()
        return plist_file.exists()
    
    def _is_systemd_running(self) -> bool:
        """Check if systemd service is running."""
        import subprocess
        try:
            result = subprocess.run(
                ["systemctl", "is-active", self.service_name],
                capture_output=True,
                text=True
            )
            return result.stdout.strip() == "active"
        except Exception:
            return False
    
    def _is_launchd_running(self) -> bool:
        """Check if launchd service is running."""
        import subprocess
        try:
            result = subprocess.run(
                ["launchctl", "list"],
                capture_output=True,
                text=True
            )
            return f"com.openclaw.{self.service_name}" in result.stdout
        except Exception:
            return False
    
    def install(self, working_dir: Optional[Path] = None, python_path: Optional[Path] = None) -> bool:
        """Install service.
        
        Args:
            working_dir: Working directory (default: current directory)
            python_path: Python interpreter path (default: current interpreter)
        
        Returns:
            True if successful
        """
        return install_service(self.service_name, working_dir, python_path)
    
    def uninstall(self) -> bool:
        """Uninstall service.
        
        Returns:
            True if successful
        """
        return uninstall_service(self.service_name)
    
    def start(self) -> bool:
        """Start service.
        
        Returns:
            True if successful
        """
        if not self.is_installed():
            raise RuntimeError("Service not installed")
        
        if self.platform == "Linux":
            return self._start_systemd()
        elif self.platform == "Darwin":
            return self._start_launchd()
        return False
    
    def stop(self) -> bool:
        """Stop service.
        
        Returns:
            True if successful
        """
        if not self.is_installed():
            return True  # Already stopped
        
        if self.platform == "Linux":
            return self._stop_systemd()
        elif self.platform == "Darwin":
            return self._stop_launchd()
        return False
    
    def restart(self) -> bool:
        """Restart service.
        
        Returns:
            True if successful
        """
        if not self.is_installed():
            raise RuntimeError("Service not installed")
        
        if self.platform == "Linux":
            return self._restart_systemd()
        elif self.platform == "Darwin":
            return self._restart_launchd()
        return False
    
    def _start_systemd(self) -> bool:
        """Start systemd service."""
        import subprocess
        try:
            subprocess.run(
                ["systemctl", "start", self.service_name],
                check=True,
                capture_output=True
            )
            return True
        except Exception:
            return False
    
    def _stop_systemd(self) -> bool:
        """Stop systemd service."""
        import subprocess
        try:
            subprocess.run(
                ["systemctl", "stop", self.service_name],
                check=True,
                capture_output=True
            )
            return True
        except Exception:
            return False
    
    def _restart_systemd(self) -> bool:
        """Restart systemd service."""
        import subprocess
        try:
            subprocess.run(
                ["systemctl", "restart", self.service_name],
                check=True,
                capture_output=True
            )
            return True
        except Exception:
            return False
    
    def _start_launchd(self) -> bool:
        """Start launchd service."""
        import subprocess
        plist_file = Path(f"~/Library/LaunchAgents/com.openclaw.{self.service_name}.plist").expanduser()
        try:
            subprocess.run(
                ["launchctl", "start", f"com.openclaw.{self.service_name}"],
                check=True,
                capture_output=True
            )
            return True
        except Exception:
            return False
    
    def _stop_launchd(self) -> bool:
        """Stop launchd service."""
        import subprocess
        try:
            subprocess.run(
                ["launchctl", "stop", f"com.openclaw.{self.service_name}"],
                check=True,
                capture_output=True
            )
            return True
        except Exception:
            return False
    
    def _restart_launchd(self) -> bool:
        """Restart launchd service."""
        # Launchd doesn't have a direct restart, so stop and start
        self._stop_launchd()
        import time
        time.sleep(1)
        return self._start_launchd()


def install_service(
    service_name: str = "openclaw",
    working_dir: Optional[Path] = None,
    python_path: Optional[Path] = None
) -> bool:
    """Install OpenClaw as system service.
    
    Args:
        service_name: Service name
        working_dir: Working directory
        python_path: Python interpreter path
    
    Returns:
        True if successful
    """
    working_dir = working_dir or Path.cwd()
    python_path = python_path or Path(sys.executable)
    
    system = platform.system()
    
    if system == "Linux":
        return _install_systemd(service_name, working_dir, python_path)
    elif system == "Darwin":
        return _install_launchd(service_name, working_dir, python_path)
    else:
        print(f"Unsupported platform: {system}")
        return False


def uninstall_service(service_name: str = "openclaw") -> bool:
    """Uninstall OpenClaw system service.
    
    Args:
        service_name: Service name
    
    Returns:
        True if successful
    """
    system = platform.system()
    
    if system == "Linux":
        return _uninstall_systemd(service_name)
    elif system == "Darwin":
        return _uninstall_launchd(service_name)
    else:
        return False


def _install_systemd(service_name: str, working_dir: Path, python_path: Path) -> bool:
    """Install systemd service."""
    from .systemd import generate_systemd_unit
    
    unit_content = generate_systemd_unit(
        service_name=service_name,
        working_dir=str(working_dir),
        python_path=str(python_path)
    )
    
    service_file = Path(f"/etc/systemd/system/{service_name}.service")
    
    try:
        # Would need sudo to write to /etc/systemd/system/
        print(f"To install, run:")
        print(f"  sudo tee {service_file} << 'EOF'")
        print(unit_content)
        print("EOF")
        print(f"  sudo systemctl daemon-reload")
        print(f"  sudo systemctl enable {service_name}")
        print(f"  sudo systemctl start {service_name}")
        return True
    except Exception:
        return False


def _uninstall_systemd(service_name: str) -> bool:
    """Uninstall systemd service."""
    print(f"To uninstall, run:")
    print(f"  sudo systemctl stop {service_name}")
    print(f"  sudo systemctl disable {service_name}")
    print(f"  sudo rm /etc/systemd/system/{service_name}.service")
    print(f"  sudo systemctl daemon-reload")
    return True


def _install_launchd(service_name: str, working_dir: Path, python_path: Path) -> bool:
    """Install launchd service."""
    from .launchd import generate_launchd_plist
    
    plist_content = generate_launchd_plist(
        service_name=service_name,
        working_dir=str(working_dir),
        python_path=str(python_path)
    )
    
    plist_file = Path(f"~/Library/LaunchAgents/com.openclaw.{service_name}.plist").expanduser()
    
    print(f"To install, save the following to {plist_file}:")
    print(plist_content)
    print(f"\nThen run:")
    print(f"  launchctl load {plist_file}")
    return True


def _uninstall_launchd(service_name: str) -> bool:
    """Uninstall launchd service."""
    plist_file = Path(f"~/Library/LaunchAgents/com.openclaw.{service_name}.plist").expanduser()
    print(f"To uninstall, run:")
    print(f"  launchctl unload {plist_file}")
    print(f"  rm {plist_file}")
    return True


def get_service_manager(service_name: str = "openclaw") -> DaemonService:
    """Get service manager instance.
    
    Args:
        service_name: Service name
        
    Returns:
        DaemonService instance
    """
    return DaemonService(service_name)

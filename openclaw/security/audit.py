"""
Security audit system.

Checks configuration, credentials, permissions, and exec approvals.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)


@dataclass
class AuditIssue:
    """Security audit issue"""
    severity: Literal["critical", "high", "medium", "low"]
    category: str
    message: str
    file_path: str | None = None
    auto_fixable: bool = False


@dataclass
class AuditReport:
    """Security audit report"""
    issues: list[AuditIssue] = field(default_factory=list)
    passed: int = 0
    failed: int = 0
    
    def add_issue(self, issue: AuditIssue):
        """Add audit issue"""
        self.issues.append(issue)
        self.failed += 1
    
    def add_pass(self):
        """Add passing check"""
        self.passed += 1


class SecurityAuditor:
    """
    Security auditor for OpenClaw.
    
    Checks:
    - Configuration security
    - Credential exposure
    - File permissions
    - Network security
    - Exec approvals
    """
    
    def __init__(self, workspace: Path):
        self.workspace = workspace
    
    async def run_audit(self, deep: bool = False) -> AuditReport:
        """
        Run security audit.
        
        Args:
            deep: Run deep scan
            
        Returns:
            Audit report
        """
        report = AuditReport()
        
        # Check config security
        issues = await self._check_config_security()
        for issue in issues:
            report.add_issue(issue)
        
        # Check credential exposure
        issues = await self._check_credential_exposure()
        for issue in issues:
            report.add_issue(issue)
        
        # Check exec approvals
        issues = await self._check_exec_approvals()
        for issue in issues:
            report.add_issue(issue)
        
        logger.info(f"Audit complete: {report.passed} passed, {report.failed} failed")
        
        return report
    
    async def fix_issues(self, report: AuditReport) -> int:
        """
        Auto-fix issues.
        
        Args:
            report: Audit report
            
        Returns:
            Number of issues fixed
        """
        fixed = 0
        
        for issue in report.issues:
            if issue.auto_fixable:
                try:
                    await self._fix_issue(issue)
                    fixed += 1
                except Exception as e:
                    logger.error(f"Failed to fix issue: {e}")
        
        return fixed
    
    async def _check_config_security(self) -> list[AuditIssue]:
        """Check configuration security"""
        issues = []
        
        config_path = self.workspace / ".openclaw" / "config.json"
        if config_path.exists():
            # Check file permissions
            mode = config_path.stat().st_mode
            if mode & 0o044:  # World/group readable
                issues.append(AuditIssue(
                    severity="medium",
                    category="permissions",
                    message="Config file is world/group readable",
                    file_path=str(config_path),
                    auto_fixable=True
                ))
        
        return issues
    
    async def _check_credential_exposure(self) -> list[AuditIssue]:
        """Check for exposed credentials"""
        issues = []
        
        # Check .env files
        env_file = self.workspace / ".env"
        if env_file.exists():
            # Check if in .gitignore
            gitignore = self.workspace / ".gitignore"
            if gitignore.exists():
                content = gitignore.read_text()
                if ".env" not in content:
                    issues.append(AuditIssue(
                        severity="high",
                        category="credentials",
                        message=".env file not in .gitignore",
                        file_path=str(env_file),
                        auto_fixable=True
                    ))
        
        return issues
    
    async def _check_exec_approvals(self) -> list[AuditIssue]:
        """Check exec approvals configuration"""
        issues = []
        
        from openclaw.infra.exec_approvals import load_exec_approvals
        
        try:
            approvals = load_exec_approvals()
            
            # Check for overly permissive settings
            if approvals.defaults and approvals.defaults.security == "full":
                issues.append(AuditIssue(
                    severity="critical",
                    category="exec-approvals",
                    message="Default exec security is 'full' (allows all commands)",
                    auto_fixable=False
                ))
        
        except Exception:
            pass
        
        return issues
    
    async def _fix_issue(self, issue: AuditIssue):
        """Fix a single issue"""
        if issue.category == "permissions" and issue.file_path:
            # Fix file permissions
            path = Path(issue.file_path)
            path.chmod(0o600)
            logger.info(f"Fixed permissions for {path}")
        
        elif issue.category == "credentials" and ".env" in issue.message:
            # Add .env to .gitignore
            gitignore = self.workspace / ".gitignore"
            with open(gitignore, 'a') as f:
                f.write("\n.env\n")
            logger.info("Added .env to .gitignore")


__all__ = [
    "AuditIssue",
    "AuditReport",
    "SecurityAuditor",
]

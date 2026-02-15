"""
Cron tool for scheduling tasks
"""
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from openclaw.agents.tools.base import AgentTool, ToolResult

logger = logging.getLogger(__name__)


class CronTool(AgentTool):
    """
    Tool for managing scheduled tasks (cron jobs)
    
    Allows agents to:
    - Schedule recurring tasks
    - Manage existing jobs
    - View scheduled tasks
    """
    
    name = "cron"
    description = """Schedule recurring tasks and manage cron jobs.
    
Actions:
- status: Get cron service status
- list: List all jobs (set includeDisabled=true to include disabled jobs)
- add: Add new job (requires job config with schedule, payload, etc)
- update: Update existing job (requires jobId and patch object)
- remove: Remove job (requires jobId)
- run: Trigger job immediately (requires jobId)
    """
    
    def __init__(self, cron_service=None, channel_registry=None, session_manager=None):
        """
        Initialize CronTool
        
        Args:
            cron_service: CronService instance for managing jobs
            channel_registry: ChannelRegistry for job delivery
            session_manager: SessionManager for agent turn execution
        """
        self._cron_service = cron_service
        self._channel_registry = channel_registry
        self._session_manager = session_manager
        
        # Store current chat context for auto-filling delivery info
        self._current_chat_info = None
        
        logger.info("CronTool initialized")
    
    @property
    def requires_confirmation(self) -> bool:
        """Cron operations don't require confirmation by default"""
        return False
    
    @property
    def can_stream(self) -> bool:
        """Cron tool does not support streaming"""
        return False
    
    @property
    def category(self) -> str:
        return "system"
    
    @property
    def tags(self) -> list[str]:
        return ["scheduling", "automation", "cron", "tasks"]
    
    def set_cron_service(self, service):
        """Set cron service instance"""
        self._cron_service = service
        logger.debug("CronService set")
    
    def set_channel_registry(self, registry):
        """Set channel registry for delivery"""
        self._channel_registry = registry
        logger.debug("ChannelRegistry set")
    
    def set_session_manager(self, manager):
        """Set session manager for agent turns"""
        self._session_manager = manager
        logger.debug("SessionManager set")
    
    def set_chat_context(self, channel: str, chat_id: str) -> None:
        """
        Set current chat context for auto-filling delivery info
        
        Args:
            channel: Channel name (e.g., "telegram")
            chat_id: Chat/user ID
        """
        self._current_chat_info = {"channel": channel, "chat_id": chat_id}
    
    def get_schema(self) -> dict[str, Any]:
        """Return JSON Schema for tool parameters (not the full tool definition)"""
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["status", "list", "add", "update", "remove", "run"],
                    "description": "Action to perform"
                },
                "includeDisabled": {
                    "type": "boolean",
                    "description": "Include disabled jobs in list (default: false)"
                },
                "job": {
                    "type": "object",
                    "description": "Job configuration for 'add' action",
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "enabled": {"type": "boolean", "default": True},
                        "schedule": {
                            "type": "object",
                            "description": "Schedule configuration",
                            "properties": {
                                "type": {
                                    "type": "string",
                                    "enum": ["at", "every", "cron"]
                                },
                                "timestamp": {"type": "string", "description": "For 'at' type: ISO timestamp"},
                                "interval_ms": {"type": "number", "description": "For 'every' type: interval in ms"},
                                "anchor": {"type": "string", "description": "For 'every' type: anchor timestamp"},
                                "expression": {"type": "string", "description": "For 'cron' type: cron expression"},
                                "timezone": {"type": "string", "description": "For 'cron' type: timezone"}
                            },
                            "required": ["type"]
                        },
                        "sessionTarget": {
                            "type": "string",
                            "enum": ["main", "isolated"],
                            "default": "main",
                            "description": "Session context for job execution"
                        },
                        "payload": {
                            "type": "object",
                            "description": "Job payload",
                            "properties": {
                                "kind": {
                                    "type": "string",
                                    "enum": ["systemEvent", "agentTurn"]
                                },
                                "text": {"type": "string", "description": "For systemEvent: message text"},
                                "prompt": {"type": "string", "description": "For agentTurn: prompt"},
                                "model": {"type": "string", "description": "For agentTurn: model override"}
                            },
                            "required": ["kind"]
                        },
                        "delivery": {
                            "type": "object",
                            "description": "Delivery configuration (optional, auto-filled from context)",
                            "properties": {
                                "channel": {"type": "string"},
                                "target": {"type": "string"},
                                "best_effort": {"type": "boolean"}
                            }
                        }
                    },
                    "required": ["name", "schedule", "payload"]
                },
                "jobId": {
                    "type": "string",
                    "description": "Job ID for update/remove/run actions"
                },
                "patch": {
                    "type": "object",
                    "description": "Patch object for 'update' action"
                }
            },
            "required": ["action"]
        }
    
    async def execute(self, args: dict[str, Any]) -> ToolResult:
        """Execute cron action"""
        if not self._cron_service:
            return ToolResult(
                success=False,
                output="",
                error="Cron service not available"
            )
        
        action = args.get("action")
        
        try:
            if action == "status":
                return await self._action_status()
            elif action == "list":
                return await self._action_list(args.get("includeDisabled", False))
            elif action == "add":
                return await self._action_add(args.get("job", {}))
            elif action == "update":
                return await self._action_update(args.get("jobId"), args.get("patch", {}))
            elif action == "remove":
                return await self._action_remove(args.get("jobId"))
            elif action == "run":
                return await self._action_run(args.get("jobId"))
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Unknown action: {action}"
                )
        except Exception as e:
            logger.error(f"Cron tool error: {e}", exc_info=True)
            return ToolResult(
                success=False,
                output="",
                error=str(e)
            )
    
    async def _action_status(self) -> ToolResult:
        """Get cron service status"""
        jobs = self._cron_service.list_jobs()
        
        enabled_count = sum(1 for j in jobs if j.get("enabled", True))
        disabled_count = len(jobs) - enabled_count
        
        output = f"✅ Cron service running\n"
        output += f"📊 Jobs: {len(jobs)} total ({enabled_count} enabled, {disabled_count} disabled)"
        
        return ToolResult(success=True, output=output)
    
    async def _action_list(self, include_disabled: bool = False) -> ToolResult:
        """List all cron jobs"""
        jobs = self._cron_service.list_jobs()
        
        if not include_disabled:
            jobs = [j for j in jobs if j.get("enabled", True)]
        
        if not jobs:
            return ToolResult(
                success=True,
                output="📭 No scheduled jobs" + (" (excluding disabled)" if not include_disabled else "")
            )
        
        output = f"📅 Scheduled Jobs ({len(jobs)}):\n\n"
        
        for job in jobs:
            job_id = job.get("id", "unknown")
            name = job.get("name", "Unnamed")
            enabled = job.get("enabled", True)
            schedule = job.get("schedule", {})
            
            status = "✅" if enabled else "⏸️"
            output += f"{status} **{name}**\n"
            output += f"   ID: `{job_id}`\n"
            output += f"   Schedule: {self._format_schedule(schedule)}\n"
            
            # Add session target info
            session_target = job.get("session_target", "main")
            if session_target == "isolated":
                output += f"   Type: 🤖 Isolated Agent\n"
            else:
                output += f"   Type: 📨 System Event\n"
            
            # Add delivery info if present
            delivery = job.get("delivery")
            if delivery:
                channel = delivery.get("channel")
                target = delivery.get("target")
                if channel:
                    output += f"   Delivery: {channel}"
                    if target:
                        output += f" → {target}"
                    output += "\n"
            
            output += "\n"
        
        return ToolResult(success=True, output=output.strip())
    
    async def _action_add(self, job_config: dict[str, Any]) -> ToolResult:
        """Add new cron job"""
        from ...cron.types import (
            AgentTurnPayload,
            AtSchedule,
            CronDelivery,
            CronJob,
            CronSchedule,
            EverySchedule,
            SystemEventPayload,
        )
        
        # Generate job ID
        job_id = f"cron-{uuid.uuid4().hex[:8]}"
        
        # Parse schedule
        schedule_config = job_config.get("schedule", {})
        schedule_type = schedule_config.get("type", "at")
        
        if schedule_type == "at":
            schedule = AtSchedule(
                timestamp=schedule_config.get("timestamp", ""),
                type="at"
            )
        elif schedule_type == "every":
            schedule = EverySchedule(
                interval_ms=schedule_config.get("interval_ms", 0),
                type="every",
                anchor=schedule_config.get("anchor")
            )
        elif schedule_type == "cron":
            schedule = CronSchedule(
                expression=schedule_config.get("expression", ""),
                type="cron",
                timezone=schedule_config.get("timezone", "UTC")
            )
        else:
            return ToolResult(
                success=False,
                output="",
                error=f"Unknown schedule type: {schedule_type}"
            )
        
        # Parse payload
        payload_config = job_config.get("payload", {})
        payload_kind = payload_config.get("kind", "systemEvent")
        
        if payload_kind == "systemEvent":
            payload = SystemEventPayload(
                text=payload_config.get("text", ""),
                kind="systemEvent"
            )
        elif payload_kind == "agentTurn":
            payload = AgentTurnPayload(
                prompt=payload_config.get("prompt", ""),
                kind="agentTurn",
                model=payload_config.get("model")
            )
        else:
            return ToolResult(
                success=False,
                output="",
                error=f"Unknown payload kind: {payload_kind}"
            )
        
        # Parse delivery (optional)
        delivery = None
        if "delivery" in job_config:
            delivery_config = job_config["delivery"]
            
            # Auto-fill channel and target from current context if not provided
            channel = delivery_config.get("channel")
            target = delivery_config.get("target")
            
            if not channel and self._current_chat_info:
                channel = self._current_chat_info.get("channel")
                logger.info(f"Auto-filled channel from context: {channel}")
            
            if not target and self._current_chat_info:
                target = self._current_chat_info.get("chat_id")
                logger.info(f"Auto-filled target from context: {target}")
            
            if channel:
                delivery = CronDelivery(
                    channel=channel,
                    target=target,
                    best_effort=delivery_config.get("best_effort", False)
                )
        
        # Create job
        job = CronJob(
            id=job_id,
            name=job_config.get("name", "Unnamed Job"),
            description=job_config.get("description"),
            enabled=job_config.get("enabled", True),
            schedule=schedule,
            session_target=job_config.get("sessionTarget", "main"),
            payload=payload,
            delivery=delivery,
        )
        
        # Add to service
        success = self._cron_service.add_job(job)
        
        if success:
            output = f"✅ Created cron job: **{job.name}**\n"
            output += f"   ID: `{job_id}`\n"
            output += f"   Schedule: {self._format_schedule(job_config.get('schedule', {}))}\n"
            output += f"   Type: {'🤖 Isolated Agent' if job.session_target == 'isolated' else '📨 System Event'}"
            
            if delivery:
                output += f"\n   Delivery: {delivery.channel}"
                if delivery.target:
                    output += f" → {delivery.target}"
            
            return ToolResult(success=True, output=output)
        else:
            return ToolResult(
                success=False,
                output="",
                error="Failed to add job"
            )
    
    async def _action_update(self, job_id: str | None, patch: dict[str, Any]) -> ToolResult:
        """Update existing job - aligned with openclaw-ts"""
        if not job_id:
            return ToolResult(
                success=False,
                output="",
                error="jobId is required for update action"
            )
        
        # Get existing job
        jobs = self._cron_service.list_jobs()
        job_data = next((j for j in jobs if j.get("id") == job_id), None)
        
        if not job_data:
            return ToolResult(
                success=False,
                output="",
                error=f"Job not found: {job_id}"
            )
        
        # Import CronJob type
        from openclaw.cron.types import CronJob
        
        # Apply patch updates
        updated = False
        if "name" in patch and patch["name"]:
            job_data["name"] = patch["name"]
            updated = True
        
        if "cronExpression" in patch and patch["cronExpression"]:
            if job_data.get("schedule", {}).get("type") == "cron":
                job_data["schedule"]["expression"] = patch["cronExpression"]
                updated = True
        
        if "timezone" in patch and patch["timezone"]:
            if job_data.get("schedule", {}).get("type") == "cron":
                job_data["schedule"]["timezone"] = patch["timezone"]
                updated = True
        
        if not updated:
            return ToolResult(
                success=False,
                output="",
                error="No valid update fields provided (name, cronExpression, timezone)"
            )
        
        # Create updated job object
        try:
            updated_job = CronJob(**job_data)
            success = self._cron_service.update_job(updated_job)
            
            if success:
                output = f"✅ Updated job: **{updated_job.name}**\n   ID: `{job_id}`"
                return ToolResult(success=True, output=output)
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Failed to update job: {job_id}"
                )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Failed to update job: {str(e)}"
            )
    
    async def _action_remove(self, job_id: str | None) -> ToolResult:
        """Remove cron job"""
        if not job_id:
            return ToolResult(
                success=False,
                output="",
                error="jobId is required for remove action"
            )
        
        # Get job info before removing (for confirmation message)
        jobs = self._cron_service.list_jobs()
        job = next((j for j in jobs if j.get("id") == job_id), None)
        
        if not job:
            return ToolResult(
                success=False,
                output="",
                error=f"Job not found: {job_id}"
            )
        
        # Remove job
        success = self._cron_service.remove_job(job_id)
        
        if success:
            job_name = job.get("name", job_id)
            output = f"✅ Removed job: **{job_name}**\n   ID: `{job_id}`"
            return ToolResult(success=True, output=output)
        else:
            return ToolResult(
                success=False,
                output="",
                error=f"Failed to remove job: {job_id}"
            )
    
    async def _action_run(self, job_id: str | None) -> ToolResult:
        """Run job immediately - aligned with openclaw-ts"""
        if not job_id:
            return ToolResult(
                success=False,
                output="",
                error="jobId is required for run action"
            )
        
        # Get job info
        jobs = self._cron_service.list_jobs()
        job = next((j for j in jobs if j.get("id") == job_id), None)
        
        if not job:
            return ToolResult(
                success=False,
                output="",
                error=f"Job not found: {job_id}"
            )
        
        try:
            # Execute job immediately
            result = await self._cron_service.run_job_now(job_id)
            
            job_name = job.get("name", job_id)
            if result.get("success"):
                output = f"✅ Executed job: **{job_name}**\n   ID: `{job_id}`\n   Result: {result.get('message', 'Success')}"
                return ToolResult(success=True, output=output)
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Job execution failed: {result.get('error', 'Unknown error')}"
                )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Failed to run job: {str(e)}"
            )
    
    def _format_schedule(self, schedule: dict[str, Any]) -> str:
        """Format schedule for display"""
        schedule_type = schedule.get("type", "")
        
        if schedule_type == "at":
            timestamp = schedule.get("timestamp", "")
            return f"One-time at {timestamp}"
        elif schedule_type == "every":
            interval_ms = schedule.get("interval_ms", 0)
            interval_hours = interval_ms / (1000 * 60 * 60)
            return f"Every {interval_hours:.1f} hours"
        elif schedule_type == "cron":
            expression = schedule.get("expression", "")
            tz = schedule.get("timezone", "UTC")
            return f"Cron: {expression} ({tz})"
        else:
            return "Unknown schedule"

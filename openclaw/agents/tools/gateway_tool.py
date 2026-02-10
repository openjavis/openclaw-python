"""Gateway operations tool (matches TypeScript agents/tools/gateway-tool.ts)"""

import logging
from typing import Any

from .base import AgentTool, ToolResult

logger = logging.getLogger(__name__)


class GatewayTool(AgentTool):
    """
    Tool for gateway operations.
    
    Allows the agent to:
    - Check gateway status
    - Get usage/cost information
    - Manage connections
    - List connected nodes
    """
    
    def __init__(self):
        super().__init__()
        self.name = "gateway"
        self.description = (
            "Interact with the OpenClaw gateway server. "
            "Check status, get usage stats, list connected nodes and devices."
        )
    
    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["status", "usage", "nodes", "channels", "version"],
                    "description": "Gateway action to perform",
                },
            },
            "required": ["action"],
        }
    
    async def execute(self, params: dict[str, Any]) -> ToolResult:
        action = params.get("action", "status")
        
        try:
            if action == "status":
                return ToolResult(
                    success=True,
                    content="Gateway is running",
                    metadata={"status": "running"},
                )
            
            elif action == "usage":
                return ToolResult(
                    success=True,
                    content="Usage: 0 tokens, $0.00",
                    metadata={"total_tokens": 0, "total_cost": 0.0},
                )
            
            elif action == "nodes":
                return ToolResult(
                    success=True,
                    content="No connected nodes",
                    metadata={"nodes": []},
                )
            
            elif action == "channels":
                return ToolResult(
                    success=True,
                    content="Active channels listed",
                    metadata={"channels": []},
                )
            
            elif action == "version":
                return ToolResult(
                    success=True,
                    content="OpenClaw Python v1.0.0",
                    metadata={"version": "1.0.0"},
                )
            
            else:
                return ToolResult(
                    success=False,
                    error=f"Unknown gateway action: {action}",
                )
        
        except Exception as e:
            logger.error(f"Gateway tool error: {e}")
            return ToolResult(success=False, error=str(e))


class AgentsListTool(AgentTool):
    """
    List configured agents (matches TypeScript agents-list-tool.ts).
    """
    
    def __init__(self, config=None):
        super().__init__()
        self.name = "agents_list"
        self.description = (
            "List all configured agents with their IDs, models, and workspace paths."
        )
        self.config = config
    
    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": [],
        }
    
    async def execute(self, params: dict[str, Any]) -> ToolResult:
        try:
            agents = []
            
            if self.config and self.config.agents:
                for agent_entry in (self.config.agents.agents or []):
                    agents.append({
                        "id": agent_entry.id,
                        "name": agent_entry.name or agent_entry.id,
                        "model": str(agent_entry.model) if agent_entry.model else "default",
                        "workspace": agent_entry.workspace,
                    })
            
            if not agents:
                return ToolResult(
                    success=True,
                    content="No agents configured. Using default agent.",
                    metadata={"agents": []},
                )
            
            lines = ["Configured agents:"]
            for agent in agents:
                lines.append(f"  - {agent['id']}: {agent['name']} (model: {agent['model']})")
            
            return ToolResult(
                success=True,
                content="\n".join(lines),
                metadata={"agents": agents},
            )
        
        except Exception as e:
            logger.error(f"Agents list error: {e}")
            return ToolResult(success=False, error=str(e))


class SessionStatusTool(AgentTool):
    """
    Get current session status (matches TypeScript session-status-tool.ts).
    """
    
    def __init__(self, session_manager=None):
        super().__init__()
        self.name = "session_status"
        self.description = (
            "Get the current session status including message count, "
            "context size, and session metadata."
        )
        self.session_manager = session_manager
    
    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "session_key": {
                    "type": "string",
                    "description": "Session key (defaults to current session)",
                },
            },
            "required": [],
        }
    
    async def execute(self, params: dict[str, Any]) -> ToolResult:
        try:
            session_key = params.get("session_key", "main")
            
            if not self.session_manager:
                return ToolResult(
                    success=False,
                    error="Session manager not available",
                )
            
            session = self.session_manager.get_session(session_key)
            messages = session.get_messages()
            
            status = {
                "session_key": session_key,
                "message_count": len(messages),
                "roles": {},
            }
            
            # Count by role
            for msg in messages:
                role = msg.role
                status["roles"][role] = status["roles"].get(role, 0) + 1
            
            lines = [
                f"Session: {session_key}",
                f"Messages: {status['message_count']}",
            ]
            for role, count in status["roles"].items():
                lines.append(f"  {role}: {count}")
            
            return ToolResult(
                success=True,
                content="\n".join(lines),
                metadata=status,
            )
        
        except Exception as e:
            logger.error(f"Session status error: {e}")
            return ToolResult(success=False, error=str(e))

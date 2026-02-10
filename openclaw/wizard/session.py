"""Wizard session management - matches TypeScript implementation"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
import uuid
from datetime import datetime


class WizardStepType(Enum):
    """Types of wizard steps"""
    NOTE = "note"
    SELECT = "select"
    MULTISELECT = "multiselect"
    TEXT = "text"
    CONFIRM = "confirm"
    PROGRESS = "progress"
    ACTION = "action"


@dataclass
class WizardStep:
    """A single step in the wizard"""
    id: str
    type: WizardStepType
    title: str
    message: Optional[str] = None
    options: Optional[list[dict]] = None
    default: Optional[Any] = None
    placeholder: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert step to dictionary for RPC"""
        result = {
            "id": self.id,
            "type": self.type.value,
            "title": self.title
        }
        if self.message:
            result["message"] = self.message
        if self.options:
            result["options"] = self.options
        if self.default is not None:
            result["default"] = self.default
        if self.placeholder:
            result["placeholder"] = self.placeholder
        return result


class WizardSession:
    """Wizard session with step management"""
    
    def __init__(self, mode: str = "local", workspace: Optional[str] = None):
        self.session_id = str(uuid.uuid4())
        self.mode = mode
        self.workspace = workspace
        self.current_step = 0
        self.steps: list[WizardStep] = []
        self.answers: dict[str, Any] = {}
        self.done = False
        self.error: Optional[str] = None
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        
        # Initialize steps based on mode
        self._initialize_steps()
    
    def _initialize_steps(self):
        """Initialize wizard steps based on mode"""
        # Risk acknowledgement (always show unless accepted)
        self.steps.append(WizardStep(
            id="risk_warning",
            type=WizardStepType.CONFIRM,
            title="Security Risk Acknowledgement",
            message=(
                "OpenClaw runs AI agents that can execute code, access files, "
                "and make network requests. Only use with API keys you trust and "
                "in environments you control. Do you understand and accept these risks?"
            ),
            default=False
        ))
        
        # Mode selection (if not specified)
        if not self.mode or self.mode == "select":
            self.steps.append(WizardStep(
                id="mode_select",
                type=WizardStepType.SELECT,
                title="Setup Mode",
                message="Choose your setup experience",
                options=[
                    {"id": "quickstart", "label": "QuickStart - Fastest setup with defaults"},
                    {"id": "advanced", "label": "Advanced - Full configuration options"}
                ],
                default="quickstart"
            ))
        
        # Agent identity
        self.steps.append(WizardStep(
            id="agent_name",
            type=WizardStepType.TEXT,
            title="Agent Identity",
            message="What should we call your agent?",
            default="OpenClaw",
            placeholder="Enter agent name"
        ))
        
        # Provider selection
        self.steps.append(WizardStep(
            id="provider_select",
            type=WizardStepType.SELECT,
            title="LLM Provider",
            message="Choose your AI provider",
            options=[
                {"id": "google", "label": "Google Gemini (RECOMMENDED)"},
                {"id": "anthropic", "label": "Anthropic Claude"},
                {"id": "openai", "label": "OpenAI GPT"},
                {"id": "groq", "label": "Groq"},
                {"id": "ollama", "label": "Ollama (Local)"}
            ],
            default="google"
        ))
        
        # Gateway port
        self.steps.append(WizardStep(
            id="gateway_port",
            type=WizardStepType.TEXT,
            title="Gateway Port",
            message="WebSocket port for gateway",
            default="18789",
            placeholder="18789"
        ))
        
        # Channel configuration
        self.steps.append(WizardStep(
            id="telegram_enable",
            type=WizardStepType.CONFIRM,
            title="Enable Telegram",
            message="Configure Telegram bot?",
            default=True
        ))
        
        # Completion
        self.steps.append(WizardStep(
            id="complete",
            type=WizardStepType.NOTE,
            title="Setup Complete",
            message="Your OpenClaw assistant is ready!"
        ))
    
    def get_current_step(self) -> Optional[WizardStep]:
        """Get the current step"""
        if 0 <= self.current_step < len(self.steps):
            return self.steps[self.current_step]
        return None
    
    def advance(self, answer: Optional[Any] = None) -> bool:
        """Advance to next step with optional answer"""
        current = self.get_current_step()
        if current and answer is not None:
            self.answers[current.id] = answer
        
        self.current_step += 1
        self.updated_at = datetime.now()
        
        if self.current_step >= len(self.steps):
            self.done = True
            return True
        
        return False
    
    def get_answer(self, step_id: str) -> Optional[Any]:
        """Get answer for a specific step"""
        return self.answers.get(step_id)
    
    def to_dict(self) -> dict:
        """Convert session to dictionary for RPC"""
        current_step = self.get_current_step()
        return {
            "sessionId": self.session_id,
            "mode": self.mode,
            "done": self.done,
            "step": current_step.to_dict() if current_step else None,
            "error": self.error,
            "progress": {
                "current": self.current_step,
                "total": len(self.steps)
            }
        }

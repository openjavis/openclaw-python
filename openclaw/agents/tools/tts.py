"""Text-to-Speech tool"""

import logging
from pathlib import Path
from typing import Any

from .base import AgentTool, ToolResult

logger = logging.getLogger(__name__)


class TTSTool(AgentTool):
    """Convert text to speech using OpenAI or ElevenLabs"""

    def __init__(self):
        super().__init__()
        self.name = "tts"
        self.description = "Convert text to speech and save as audio file"

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to convert to speech"},
                "output_path": {
                    "type": "string",
                    "description": "Output file path",
                    "default": "output.mp3",
                },
                "provider": {
                    "type": "string",
                    "enum": ["openai", "elevenlabs"],
                    "description": "TTS provider",
                    "default": "openai",
                },
                "voice": {"type": "string", "description": "Voice ID or name", "default": "alloy"},
                "model": {
                    "type": "string",
                    "description": "Model to use (provider-specific)",
                    "default": "tts-1",
                },
            },
            "required": ["text"],
        }

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        """Convert text to speech"""
        text = params.get("text", "")
        output_path = params.get("output_path", "output.mp3")
        provider = params.get("provider", "openai")
        voice = params.get("voice", "alloy")
        model = params.get("model", "tts-1")

        if not text:
            return ToolResult(success=False, content="", error="text required")

        try:
            if provider == "openai":
                return await self._openai_tts(text, output_path, voice, model)
            elif provider == "elevenlabs":
                return await self._elevenlabs_tts(text, output_path, voice)
            else:
                return ToolResult(success=False, content="", error=f"Unknown provider: {provider}")

        except Exception as e:
            logger.error(f"TTS error: {e}", exc_info=True)
            return ToolResult(success=False, content="", error=str(e))

    async def _openai_tts(self, text: str, output_path: str, voice: str, model: str) -> ToolResult:
        """Generate speech using OpenAI TTS"""
        try:
            import os

            from openai import AsyncOpenAI

            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return ToolResult(success=False, content="", error="OPENAI_API_KEY not set")

            client = AsyncOpenAI(api_key=api_key)

            response = await client.audio.speech.create(model=model, voice=voice, input=text)

            # Save to file
            output_file = Path(output_path).expanduser()
            output_file.parent.mkdir(parents=True, exist_ok=True)

            response.stream_to_file(str(output_file))

            return ToolResult(
                success=True,
                content=f"Speech saved to {output_path}",
                metadata={
                    "output_path": str(output_file),
                    "provider": "openai",
                    "voice": voice,
                    "model": model,
                },
            )

        except ImportError:
            return ToolResult(success=False, content="", error="openai package not installed")
        except Exception as e:
            return ToolResult(success=False, content="", error=str(e))

    async def _elevenlabs_tts(self, text: str, output_path: str, voice: str) -> ToolResult:
        """Generate speech using ElevenLabs"""
        try:
            import os

            from elevenlabs import save
            from elevenlabs.client import ElevenLabs

            api_key = os.getenv("ELEVENLABS_API_KEY")
            if not api_key:
                return ToolResult(success=False, content="", error="ELEVENLABS_API_KEY not set")

            client = ElevenLabs(api_key=api_key)

            # Generate speech
            audio = client.generate(text=text, voice=voice, model="eleven_monolingual_v1")

            # Save to file
            output_file = Path(output_path).expanduser()
            output_file.parent.mkdir(parents=True, exist_ok=True)

            save(audio, str(output_file))

            return ToolResult(
                success=True,
                content=f"Speech saved to {output_path}",
                metadata={
                    "output_path": str(output_file),
                    "provider": "elevenlabs",
                    "voice": voice,
                },
            )

        except ImportError:
            return ToolResult(
                success=False,
                content="",
                error="elevenlabs package not installed. Install with: pip install elevenlabs",
            )
        except Exception as e:
            return ToolResult(success=False, content="", error=str(e))

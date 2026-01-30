"""Image analysis tool with vision models"""

import base64
import logging
from pathlib import Path
from typing import Any

import httpx

from .base import AgentTool, ToolResult

logger = logging.getLogger(__name__)


class ImageTool(AgentTool):
    """Analyze images using vision models (Claude/GPT-4)"""

    def __init__(self):
        super().__init__()
        self.name = "image"
        self.description = (
            "Analyze images using vision models. Supports file paths, URLs, and data URLs."
        )

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "image": {"type": "string", "description": "Image file path, URL, or data URL"},
                "prompt": {
                    "type": "string",
                    "description": "Question or instruction about the image",
                },
                "model": {
                    "type": "string",
                    "description": "Model to use (claude-3-5-sonnet, gpt-4-vision)",
                    "default": "claude-3-5-sonnet",
                },
            },
            "required": ["image", "prompt"],
        }

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        """Analyze image"""
        image_input = params.get("image", "")
        prompt = params.get("prompt", "")
        model = params.get("model", "claude-3-5-sonnet")

        if not image_input or not prompt:
            return ToolResult(success=False, content="", error="Both image and prompt are required")

        try:
            # Get image data
            image_data, media_type = await self._get_image_data(image_input)

            if not image_data:
                return ToolResult(success=False, content="", error="Failed to load image")

            # Analyze with appropriate model
            if "claude" in model.lower():
                result = await self._analyze_with_claude(image_data, media_type, prompt)
            elif "gpt" in model.lower() or "openai" in model.lower():
                result = await self._analyze_with_openai(image_data, media_type, prompt)
            else:
                return ToolResult(success=False, content="", error=f"Unsupported model: {model}")

            return result

        except Exception as e:
            logger.error(f"Image analysis error: {e}", exc_info=True)
            return ToolResult(success=False, content="", error=str(e))

    async def _get_image_data(self, image_input: str) -> tuple[str, str]:
        """Get base64 image data and media type"""

        # Data URL
        if image_input.startswith("data:"):
            parts = image_input.split(",", 1)
            if len(parts) == 2:
                media_type = parts[0].split(":")[1].split(";")[0]
                return parts[1], media_type

        # HTTP URL
        if image_input.startswith("http://") or image_input.startswith("https://"):
            async with httpx.AsyncClient() as client:
                response = await client.get(image_input)
                response.raise_for_status()
                media_type = response.headers.get("content-type", "image/jpeg")
                image_data = base64.b64encode(response.content).decode("utf-8")
                return image_data, media_type

        # File path
        path = Path(image_input).expanduser()
        if path.exists() and path.is_file():
            # Determine media type from extension
            ext = path.suffix.lower()
            media_type_map = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".gif": "image/gif",
                ".webp": "image/webp",
            }
            media_type = media_type_map.get(ext, "image/jpeg")

            with open(path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
            return image_data, media_type

        return "", ""

    async def _analyze_with_claude(
        self, image_data: str, media_type: str, prompt: str
    ) -> ToolResult:
        """Analyze image using Claude"""
        try:
            import os

            from anthropic import AsyncAnthropic

            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                return ToolResult(success=False, content="", error="ANTHROPIC_API_KEY not set")

            client = AsyncAnthropic(api_key=api_key)

            response = await client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_data,
                                },
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
            )

            # Extract text from response
            text_content = ""
            for block in response.content:
                if block.type == "text":
                    text_content += block.text

            return ToolResult(
                success=True,
                content=text_content,
                metadata={
                    "model": response.model,
                    "usage": {
                        "input_tokens": response.usage.input_tokens,
                        "output_tokens": response.usage.output_tokens,
                    },
                },
            )

        except ImportError:
            return ToolResult(success=False, content="", error="anthropic package not installed")
        except Exception as e:
            return ToolResult(success=False, content="", error=str(e))

    async def _analyze_with_openai(
        self, image_data: str, media_type: str, prompt: str
    ) -> ToolResult:
        """Analyze image using OpenAI"""
        try:
            import os

            from openai import AsyncOpenAI

            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return ToolResult(success=False, content="", error="OPENAI_API_KEY not set")

            client = AsyncOpenAI(api_key=api_key)

            response = await client.chat.completions.create(
                model="gpt-4-vision-preview",
                max_tokens=4096,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:{media_type};base64,{image_data}"},
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
            )

            content = response.choices[0].message.content

            return ToolResult(
                success=True,
                content=content,
                metadata={
                    "model": response.model,
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                    },
                },
            )

        except ImportError:
            return ToolResult(success=False, content="", error="openai package not installed")
        except Exception as e:
            return ToolResult(success=False, content="", error=str(e))

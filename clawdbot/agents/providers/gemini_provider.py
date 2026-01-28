"""
Google Gemini provider implementation
"""
import os
import logging
from typing import AsyncIterator, Optional, Any
import google.generativeai as genai

from .base import LLMProvider, LLMResponse, LLMMessage

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """
    Google Gemini provider
    
    Supports:
    - gemini-pro
    - gemini-pro-vision
    - gemini-ultra
    - gemini-3-pro-preview
    - gemini-3-flash-preview
    
    Example:
        provider = GeminiProvider("gemini-pro", api_key="...")
        async for response in provider.stream(messages):
            print(response.content)
    """
    
    @property
    def provider_name(self) -> str:
        return "gemini"
    
    def get_client(self) -> Any:
        """Initialize Gemini client"""
        if self._client is None:
            api_key = self.api_key or os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY not provided")
            
            genai.configure(api_key=api_key)
            self._client = genai.GenerativeModel(self.model)
        
        return self._client
    
    def _convert_messages(self, messages: list[LLMMessage]) -> list[dict]:
        """Convert messages to Gemini format"""
        gemini_messages = []
        
        for msg in messages:
            # Gemini uses 'user' and 'model' roles
            role = "model" if msg.role == "assistant" else "user"
            
            # Handle system messages by prepending to first user message
            if msg.role == "system":
                continue  # Will handle separately
            
            gemini_messages.append({
                "role": role,
                "parts": [{"text": msg.content}]
            })
        
        return gemini_messages
    
    def _format_tools_for_gemini(self, tools: Optional[list[dict]]) -> Optional[list[dict]]:
        """
        Format tools for Gemini function calling
        
        Gemini uses a similar but slightly different format
        """
        if not tools:
            return None
        
        gemini_tools = []
        for tool in tools:
            # Extract function definition
            if "function" in tool:
                func = tool["function"]
                gemini_tools.append({
                    "name": func["name"],
                    "description": func.get("description", ""),
                    "parameters": func.get("parameters", {})
                })
        
        return gemini_tools if gemini_tools else None
    
    async def stream(
        self,
        messages: list[LLMMessage],
        tools: Optional[list[dict]] = None,
        max_tokens: int = 4096,
        **kwargs
    ) -> AsyncIterator[LLMResponse]:
        """Stream responses from Gemini"""
        client = self.get_client()
        
        # Convert messages
        gemini_messages = self._convert_messages(messages)
        
        # Extract system message if present
        system_instruction = None
        system_msgs = [m for m in messages if m.role == "system"]
        if system_msgs:
            system_instruction = system_msgs[0].content
        
        # Format tools
        gemini_tools = self._format_tools_for_gemini(tools)
        
        try:
            # Create generation config
            generation_config = {
                "max_output_tokens": max_tokens,
                "temperature": kwargs.get("temperature", 0.7),
            }
            
            # Start chat
            chat = client.start_chat(history=gemini_messages[:-1] if len(gemini_messages) > 1 else [])
            
            # Send message and stream response
            last_message = gemini_messages[-1]["parts"][0]["text"] if gemini_messages else ""
            
            response_stream = await chat.send_message_async(
                last_message,
                generation_config=generation_config,
                stream=True
            )
            
            # Stream chunks
            async for chunk in response_stream:
                if chunk.text:
                    yield LLMResponse(
                        type="text_delta",
                        content=chunk.text
                    )
                
                # Handle function calls
                if hasattr(chunk, 'function_call') and chunk.function_call:
                    func_call = chunk.function_call
                    yield LLMResponse(
                        type="tool_call",
                        content=None,
                        tool_calls=[{
                            "id": f"call_{func_call.name}",
                            "name": func_call.name,
                            "arguments": dict(func_call.args)
                        }]
                    )
            
            # Final response
            yield LLMResponse(
                type="done",
                content=None,
                finish_reason="stop"
            )
            
        except Exception as e:
            logger.error(f"Gemini streaming error: {e}")
            yield LLMResponse(
                type="error",
                content=str(e)
            )

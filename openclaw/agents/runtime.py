"""
Enhanced Agent runtime with multi-provider support
"""

import asyncio
import logging
from collections.abc import AsyncIterator

from ..events import Event, EventType
from .auth import AuthProfile, ProfileStore, RotationManager
from .compaction import CompactionManager, CompactionStrategy, TokenAnalyzer
from .context import ContextManager
from .errors import classify_error, format_error_message, is_retryable_error
from .failover import FailoverReason, FallbackChain, FallbackManager
from .formatting import FormatMode, ToolFormatter
from .providers import (
    AnthropicProvider,
    BedrockProvider,
    GeminiProvider,
    LLMMessage,
    LLMProvider,
    OllamaProvider,
    OpenAIProvider,
)
from .queuing import QueueManager
from .session import Session
from .thinking import ThinkingExtractor, ThinkingMode
from .tools.base import AgentTool

logger = logging.getLogger(__name__)

# Backwards compatibility: AgentEvent is now an alias to Event
AgentEvent = Event


class MultiProviderRuntime:
    """
    Enhanced Agent runtime with support for multiple LLM providers

    Supported providers:
    - anthropic: Claude models
    - openai: GPT models
    - gemini: Google Gemini
    - bedrock: AWS Bedrock
    - ollama: Local models
    - openai-compatible: Any OpenAI-compatible API

    Model format: "provider/model" or just "model" (defaults to anthropic)

    Examples:
        # Anthropic
        runtime = MultiProviderRuntime("anthropic/claude-opus-4-5")

        # OpenAI
        runtime = MultiProviderRuntime("openai/gpt-4")

        # Google Gemini
        runtime = MultiProviderRuntime("gemini/gemini-pro")

        # AWS Bedrock
        runtime = MultiProviderRuntime("bedrock/anthropic.claude-3-sonnet")

        # Ollama (local)
        runtime = MultiProviderRuntime("ollama/llama3")

        # OpenAI-compatible (custom base URL)
        runtime = MultiProviderRuntime(
            "lmstudio/model-name",
            base_url="http://localhost:1234/v1"
        )
    """

    def __init__(
        self,
        model: str = "anthropic/claude-opus-4-5-20250514",
        api_key: str | None = None,
        base_url: str | None = None,
        max_retries: int = 3,
        enable_context_management: bool = True,
        # New advanced features
        thinking_mode: ThinkingMode = ThinkingMode.OFF,
        fallback_models: list[str] | None = None,
        auth_profiles: list[AuthProfile] | None = None,
        enable_queuing: bool = False,
        tool_format: FormatMode = FormatMode.MARKDOWN,
        compaction_strategy: CompactionStrategy = CompactionStrategy.KEEP_IMPORTANT,
        **kwargs,
    ):
        self.model_str = model
        self.api_key = api_key
        self.base_url = base_url
        self.max_retries = max_retries
        self.enable_context_management = enable_context_management
        self.extra_params = kwargs

        # Parse provider and model
        self.provider_name, self.model_name = self._parse_model(model)

        # Initialize provider
        self.provider = self._create_provider()

        # Initialize context manager
        if enable_context_management:
            self.context_manager = ContextManager(self.model_name)
        else:
            self.context_manager = None

        # Initialize new advanced features
        self.thinking_mode = thinking_mode
        self.thinking_extractor = ThinkingExtractor() if thinking_mode != ThinkingMode.OFF else None

        # Failover management
        self.fallback_chain = None
        self.fallback_manager = None
        if fallback_models:
            self.fallback_chain = FallbackChain(primary=model, fallbacks=fallback_models)
            self.fallback_manager = FallbackManager(self.fallback_chain)

        # Auth rotation
        self.auth_rotation = None
        if auth_profiles:
            store = ProfileStore()
            for profile in auth_profiles:
                store.add_profile(profile)
            self.auth_rotation = RotationManager(store)

        # Queuing
        self.queue_manager = QueueManager() if enable_queuing else None

        # Tool formatting
        self.tool_formatter = ToolFormatter(tool_format)

        # Advanced compaction
        self.compaction_strategy = compaction_strategy
        if self.context_manager:
            self.token_analyzer = TokenAnalyzer(self.model_name)
            self.compaction_manager = CompactionManager(self.token_analyzer, compaction_strategy)
        else:
            self.token_analyzer = None
            self.compaction_manager = None

        # Observer pattern: event listeners (e.g., Gateway)
        self.event_listeners: list = []

    def _parse_model(self, model: str) -> tuple[str, str]:
        """
        Parse model string into provider and model name

        Examples:
            "anthropic/claude-opus" -> ("anthropic", "claude-opus")
            "gemini/gemini-pro" -> ("gemini", "gemini-pro")
            "claude-opus" -> ("anthropic", "claude-opus")  # default
        """
        if "/" in model:
            parts = model.split("/", 1)
            return parts[0], parts[1]
        else:
            # Default to anthropic
            return "anthropic", model

    def add_event_listener(self, listener):
        """
        Register an event listener (observer pattern)

        The listener will be called for every AgentEvent produced during run_turn.
        This allows components like Gateway to observe agent events without direct coupling.

        Args:
            listener: Callable that accepts AgentEvent. Can be sync or async.

        Example:
            async def on_agent_event(event: AgentEvent):
                print(f"Agent event: {event.type}")

            agent_runtime.add_event_listener(on_agent_event)
        """
        self.event_listeners.append(listener)
        logger.debug(f"Registered event listener: {listener}")

    def remove_event_listener(self, listener):
        """Remove an event listener"""
        if listener in self.event_listeners:
            self.event_listeners.remove(listener)
            logger.debug(f"Removed event listener: {listener}")

    async def _notify_observers(self, event: Event):
        """Notify all registered observers of an event"""
        for listener in self.event_listeners:
            try:
                if asyncio.iscoroutinefunction(listener):
                    await listener(event)
                else:
                    listener(event)
            except Exception as e:
                logger.error(f"Observer notification failed: {e}", exc_info=True)

    def _create_provider(self) -> LLMProvider:
        """Create appropriate provider based on provider name"""
        provider_name = self.provider_name.lower()

        # Common parameters
        kwargs = {
            "model": self.model_name,
            "api_key": self.api_key,
            "base_url": self.base_url,
            **self.extra_params,
        }

        # Create provider
        if provider_name == "anthropic":
            return AnthropicProvider(**kwargs)

        elif provider_name == "openai":
            return OpenAIProvider(**kwargs)

        elif provider_name in ("gemini", "google", "google-gemini"):
            return GeminiProvider(**kwargs)

        elif provider_name in ("bedrock", "aws-bedrock"):
            return BedrockProvider(**kwargs)

        elif provider_name == "ollama":
            return OllamaProvider(**kwargs)

        elif provider_name in ("lmstudio", "openai-compatible", "custom"):
            # OpenAI-compatible with custom base URL
            return OpenAIProvider(**kwargs)

        else:
            # Unknown provider, try OpenAI-compatible
            logger.warning(f"Unknown provider '{provider_name}', trying OpenAI-compatible mode")
            return OpenAIProvider(**kwargs)

    async def run_turn(
        self,
        session: Session,
        message: str,
        tools: list[AgentTool] | None = None,
        max_tokens: int = 4096,
        images: list[str] | None = None,
        system_prompt: str | None = None,
    ) -> AsyncIterator[AgentEvent]:
        """
        Run an agent turn with the configured provider

        Features:
        - Multi-provider support
        - Thinking mode extraction
        - Model fallback chains
        - Auth profile rotation
        - Session queuing
        - Advanced context compaction
        - Tool result formatting

        Args:
            session: Session to use
            message: User message
            tools: Optional list of tools
            max_tokens: Maximum tokens to generate
            images: Optional list of image URLs
            system_prompt: Optional system prompt (injected at session start)

        Yields:
            AgentEvent objects
        """
        if tools is None:
            tools = []

        # Wrap in queue if enabled
        if self.queue_manager:

            async def queued_execution():
                async for event in self._run_turn_internal(session, message, tools, max_tokens, images, system_prompt):
                    yield event

            # This is a generator, need to handle differently
            async for event in self._run_turn_internal(session, message, tools, max_tokens, images, system_prompt):
                yield event
        else:
            async for event in self._run_turn_internal(session, message, tools, max_tokens, images, system_prompt):
                yield event

    async def _run_turn_internal(
        self,
        session: Session,
        message: str,
        tools: list[AgentTool],
        max_tokens: int,
        images: list[str] | None = None,
        system_prompt: str | None = None,
    ) -> AsyncIterator[AgentEvent]:
        """Internal run turn implementation"""
        # Inject system prompt at the start of the session (only if no messages yet)
        if system_prompt and len(session.messages) == 0:
            session.add_system_message(system_prompt)
            logger.info(f"✨ System prompt injected ({len(system_prompt)} chars)")
        
        # Add user message (with images if provided)
        if images:
            # Store images in session metadata for this message
            session.add_user_message(message)
            # Add images metadata to the last message
            if session.messages:
                last_msg = session.messages[-1]
                if not hasattr(last_msg, 'images'):
                    last_msg.images = images
                else:
                    last_msg.images = images
        else:
            session.add_user_message(message)

        # Check context window and compact if needed
        if self.compaction_manager and self.enable_context_management:
            messages_for_api = session.get_messages_for_api()
            current_tokens = self.token_analyzer.estimate_messages_tokens(messages_for_api)
            window = self.context_manager.check_context(current_tokens)

            if window.should_compress:
                logger.info(f"Context at {current_tokens}/{window.total_tokens} tokens, compacting")
                # Use advanced compaction
                target_tokens = int(window.total_tokens * 0.7)  # Use 70% of window
                compacted = self.compaction_manager.compact(messages_for_api, target_tokens)

                # Update session with compacted messages
                # Convert back to Message objects
                from .session import Message

                session.messages = [
                    Message(
                        role=m["role"],
                        content=m["content"],
                        tool_calls=m.get("tool_calls"),
                        tool_call_id=m.get("tool_call_id"),
                        name=m.get("name"),
                    )
                    for m in compacted
                ]

                event = AgentEvent(
                    "compaction",
                    {
                        "original_tokens": current_tokens,
                        "compacted_tokens": self.token_analyzer.estimate_messages_tokens(compacted),
                        "strategy": self.compaction_strategy.value,
                    },
                )
                await self._notify_observers(event)
                yield event

        event = Event(
            type=EventType.AGENT_STARTED,
            source="agent-runtime",
            session_id=session.session_id if session else None,
            data={"phase": "start"},
        )
        await self._notify_observers(event)
        yield event

        # Execute with retry logic and failover
        retry_count = 0
        thinking_state = {}  # State for streaming thinking extraction

        while retry_count <= self.max_retries:
            try:
                # Get current model (may change with failover)
                current_model = self.model_str
                if self.fallback_manager:
                    current_model = self.fallback_manager.get_current_model()
                    logger.info(f"Using model: {current_model}")

                # Convert session messages to LLM format
                llm_messages = []
                for msg in session.get_messages():
                    # Include images if present
                    msg_images = getattr(msg, 'images', None)
                    llm_messages.append(LLMMessage(role=msg.role, content=msg.content, images=msg_images))

                # Format tools for provider
                tools_param = None
                if tools:
                    tools_param = [
                        {
                            "type": "function",
                            "function": {
                                "name": tool.name,
                                "description": tool.description,
                                "parameters": tool.get_schema(),
                            },
                        }
                        for tool in tools
                    ]

                # Stream from provider (may need multiple rounds for tool calling)
                accumulated_text = ""
                accumulated_thinking = ""
                tool_calls = []
                needs_tool_response = False

                async for response in self.provider.stream(
                    messages=llm_messages, tools=tools_param, max_tokens=max_tokens
                ):
                    if response.type == "text_delta":
                        text = response.content
                        accumulated_text += text

                        # Extract thinking if enabled
                        if self.thinking_mode != ThinkingMode.OFF and self.thinking_extractor:
                            thinking_delta, content_delta = (
                                self.thinking_extractor.extract_streaming(text, thinking_state)
                            )

                            # Stream thinking separately if mode is STREAM
                            if self.thinking_mode == ThinkingMode.STREAM and thinking_delta:
                                accumulated_thinking += thinking_delta
                                event = AgentEvent(
                                    "thinking",
                                    {"delta": {"text": thinking_delta}, "mode": "stream"},
                                )
                                await self._notify_observers(event)
                                yield event

                            # Stream content (non-thinking text)
                            if content_delta:
                                event = Event(
                                    type=EventType.AGENT_TEXT,
                                    source="agent-runtime",
                                    session_id=session.session_id if session else None,
                                    data={"delta": {"type": "text_delta", "text": content_delta}},
                                )
                                await self._notify_observers(event)
                                yield event
                        else:
                            # No thinking extraction, stream as-is
                            event = Event(
                                type=EventType.AGENT_TEXT,
                                source="agent-runtime",
                                session_id=session.session_id if session else None,
                                data={"delta": {"type": "text_delta", "text": text}},
                            )
                            await self._notify_observers(event)
                            yield event

                    elif response.type == "tool_call":
                        tool_calls = response.tool_calls or []

                        # Execute tools
                        for tc in tool_calls:
                            tool = next((t for t in tools if t.name == tc["name"]), None)
                            if tool:
                                # Format tool use
                                formatted_use = self.tool_formatter.format_tool_use(
                                    tc["name"], tc["arguments"]
                                )

                                event = AgentEvent(
                                    "tool_use",
                                    {
                                        "tool": tc["name"],
                                        "input": tc["arguments"],
                                        "formatted": formatted_use,
                                    },
                                )
                                await self._notify_observers(event)
                                yield event

                                # Execute tool
                                try:
                                    result = await tool.execute(tc["arguments"])
                                    success = result.success if result else False
                                    output = result.content if result else "No output"

                                    # Format tool result
                                    formatted_result = self.tool_formatter.format_tool_result(
                                        tc["name"], output, success
                                    )

                                    event = AgentEvent(
                                        "tool_result",
                                        {
                                            "tool": tc["name"],
                                            "result": output,
                                            "success": success,
                                            "formatted": formatted_result,
                                        },
                                    )
                                    await self._notify_observers(event)
                                    yield event

                                    # Add tool result to session
                                    session.add_tool_message(
                                        tool_call_id=tc["id"], content=output, name=tc["name"]
                                    )

                                except Exception as tool_error:
                                    error_msg = str(tool_error)
                                    formatted_error = self.tool_formatter.format_tool_result(
                                        tc["name"], error_msg, success=False
                                    )

                                    event = AgentEvent(
                                        "tool_result",
                                        {
                                            "tool": tc["name"],
                                            "result": error_msg,
                                            "success": False,
                                            "error": error_msg,
                                            "formatted": formatted_error,
                                        },
                                    )
                                    await self._notify_observers(event)
                                    yield event

                                    session.add_tool_message(
                                        tool_call_id=tc["id"],
                                        content=f"Error: {error_msg}",
                                        name=tc["name"],
                                    )

                    elif response.type == "done":
                        # Extract thinking if ON mode
                        final_text = accumulated_text
                        if self.thinking_mode == ThinkingMode.ON and self.thinking_extractor:
                            extracted = self.thinking_extractor.extract(accumulated_text)
                            if extracted.has_thinking:
                                # Include thinking in response
                                event = AgentEvent(
                                    "thinking", {"content": extracted.thinking, "mode": "on"}
                                )
                                await self._notify_observers(event)
                                yield event
                                final_text = extracted.content

                        # Save assistant message
                        if final_text or tool_calls:
                            session.add_assistant_message(final_text, tool_calls)

                        # If there were tool calls, we need to continue the conversation
                        # to let the model generate a response based on tool results
                        if tool_calls:
                            logger.info(f"Tool calls completed, will request final response from model")
                            needs_tool_response = True
                            # Don't break yet - we'll make another API call after this loop
                        else:
                            # Record success for failover manager
                            if self.fallback_manager:
                                self.fallback_manager.record_success(current_model)

                        break

                    elif response.type == "error":
                        raise Exception(response.content)

                # If we need to get a response after tool execution, make another API call
                if needs_tool_response:
                    logger.info("Making follow-up API call to get response based on tool results")
                    
                    # Rebuild messages with tool results
                    llm_messages = []
                    for msg in session.get_messages():
                        msg_images = getattr(msg, 'images', None)
                        llm_messages.append(LLMMessage(role=msg.role, content=msg.content, images=msg_images))
                    
                    # Reset for second response
                    accumulated_text = ""
                    tool_calls = []
                    
                    # Stream the final response WITHOUT tools (to prevent infinite loop)
                    # The model should now generate a text response based on tool results
                    async for response in self.provider.stream(
                        messages=llm_messages, tools=None, max_tokens=max_tokens
                    ):
                        if response.type == "text_delta":
                            text = response.content
                            accumulated_text += text
                            
                            # Stream text to user
                            event = Event(
                                type=EventType.AGENT_TEXT,
                                source="agent-runtime",
                                session_id=session.session_id if session else None,
                                data={"delta": {"type": "text_delta", "text": text}},
                            )
                            await self._notify_observers(event)
                            yield event
                            
                        elif response.type == "done":
                            # Save final response
                            if accumulated_text:
                                session.add_assistant_message(accumulated_text, [])
                            break
                            
                        elif response.type == "error":
                            raise Exception(response.content)
                    
                    # Record success
                    if self.fallback_manager:
                        self.fallback_manager.record_success(current_model)

                # Success, exit retry loop
                event = Event(
                    type=EventType.AGENT_TURN_COMPLETE,
                    source="agent-runtime",
                    session_id=session.session_id if session else None,
                    data={"phase": "end"},
                )
                await self._notify_observers(event)
                yield event
                return

            except Exception as e:
                # Check if should failover
                should_failover = False
                failover_reason = FailoverReason.UNKNOWN

                if self.fallback_manager:
                    should_failover, failover_reason = self.fallback_manager.should_failover(e)

                    if should_failover:
                        next_model = self.fallback_manager.get_next_model()
                        if next_model:
                            logger.info(f"Failing over from {current_model} to {next_model}")

                            # Update provider for new model
                            self.provider_name, self.model_name = self._parse_model(next_model)
                            self.provider = self._create_provider()

                            event = AgentEvent(
                                "failover",
                                {
                                    "from": current_model,
                                    "to": next_model,
                                    "reason": failover_reason.value,
                                    "error": str(e),
                                },
                            )
                            await self._notify_observers(event)
                            yield event

                            # Continue to next attempt (no sleep, immediate retry with new model)
                            continue

                # Check if retryable
                if not is_retryable_error(e) and not should_failover:
                    logger.error(f"Non-retryable error: {format_error_message(e)}")
                    event = AgentEvent(
                        "error",
                        {"message": format_error_message(e), "category": classify_error(e).value},
                    )
                    await self._notify_observers(event)
                    yield event

                    event = AgentEvent("lifecycle", {"phase": "end"})
                    await self._notify_observers(event)
                    yield event
                    return

                if retry_count >= self.max_retries:
                    logger.error(f"Max retries reached: {format_error_message(e)}")
                    event = AgentEvent(
                        "error",
                        {
                            "message": f"Max retries exceeded: {format_error_message(e)}",
                            "category": classify_error(e).value,
                        },
                    )
                    await self._notify_observers(event)
                    yield event

                    event = AgentEvent("lifecycle", {"phase": "end"})
                    await self._notify_observers(event)
                    yield event
                    return

                # Retry with exponential backoff
                retry_count += 1
                delay = min(2 ** (retry_count - 1), 30)
                logger.warning(f"Retry {retry_count}/{self.max_retries} after {delay}s: {e}")

                event = AgentEvent(
                    "retry",
                    {
                        "attempt": retry_count,
                        "max_retries": self.max_retries,
                        "delay": delay,
                        "error": str(e),
                    },
                )
                await self._notify_observers(event)
                yield event

                await asyncio.sleep(delay)


# Alias for backward compatibility
AgentRuntime = MultiProviderRuntime

"""
Session message order guards

Ensures messages follow correct ordering rules for different LLM providers.
Inspired by pi-mono's session-tool-result-guard.ts
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openclaw.agents.types import AgentMessage

logger = logging.getLogger(__name__)


class SessionToolResultGuard:
    """
    Ensures tool results are properly ordered relative to assistant messages with tool calls.
    
    This prevents errors like:
    - "function response turn must come immediately after function call turn" (Gemini)
    - Tool results appearing before their corresponding function calls
    
    Rules:
    1. A tool result message must follow an assistant message that contains tool calls
    2. Tool result tool_call_id must match one of the tool calls in the preceding assistant message
    3. All tool calls in an assistant message must have corresponding tool results before the next assistant message
    """
    
    def __init__(self):
        self._pending_tool_calls: dict[str, str] = {}  # tool_call_id -> tool_name
    
    def validate_message_order(self, messages: list[AgentMessage]) -> tuple[bool, str]:
        """
        Validate that messages follow correct ordering rules.
        
        Returns:
            (is_valid, error_message)
        """
        pending_calls = {}
        last_assistant_idx = None
        
        for i, msg in enumerate(messages):
            if msg.role == "assistant":
                last_assistant_idx = i
                # Track tool calls from this message
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    for tc in msg.tool_calls:
                        tool_call_id = tc.get("id") if isinstance(tc, dict) else tc.id
                        tool_name = tc.get("name") if isinstance(tc, dict) else tc.name
                        pending_calls[tool_call_id] = tool_name
            
            elif msg.role == "tool":
                # Tool result must follow an assistant message
                if last_assistant_idx is None:
                    return False, f"Tool result at index {i} has no preceding assistant message"
                
                # Tool call ID must be in pending calls
                tool_call_id = msg.tool_call_id if hasattr(msg, 'tool_call_id') else None
                if tool_call_id not in pending_calls:
                    return False, f"Tool result at index {i} references unknown tool_call_id: {tool_call_id}"
                
                # Mark this call as completed
                del pending_calls[tool_call_id]
        
        # All pending calls should be resolved
        if pending_calls:
            unresolved = ", ".join(pending_calls.keys())
            return False, f"Unresolved tool calls: {unresolved}"
        
        return True, ""
    
    def insert_tool_result(
        self,
        messages: list[AgentMessage],
        tool_result: AgentMessage,
    ) -> list[AgentMessage]:
        """
        Insert a tool result message at the correct position.
        
        Rules:
        1. Must be inserted after the assistant message that made the tool call
        2. Should be inserted before any subsequent assistant messages
        3. Multiple tool results for the same assistant message should be grouped together
        
        Args:
            messages: Current message list
            tool_result: Tool result message to insert
        
        Returns:
            Updated message list with tool result inserted
        """
        tool_call_id = tool_result.tool_call_id if hasattr(tool_result, 'tool_call_id') else None
        
        if not tool_call_id:
            logger.warning("Tool result has no tool_call_id, appending to end")
            return messages + [tool_result]
        
        # Find the assistant message that made this tool call
        assistant_idx = None
        for i in range(len(messages) - 1, -1, -1):  # Search backwards
            msg = messages[i]
            if msg.role == "assistant" and hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    tc_id = tc.get("id") if isinstance(tc, dict) else tc.id
                    if tc_id == tool_call_id:
                        assistant_idx = i
                        break
            if assistant_idx is not None:
                break
        
        if assistant_idx is None:
            logger.warning(f"Could not find assistant message for tool_call_id {tool_call_id}, appending to end")
            return messages + [tool_result]
        
        # Find the insertion point: after the assistant message and any existing tool results
        insert_idx = assistant_idx + 1
        while insert_idx < len(messages) and messages[insert_idx].role == "tool":
            insert_idx += 1
        
        # Insert the tool result
        new_messages = messages[:insert_idx] + [tool_result] + messages[insert_idx:]
        
        logger.debug(f"Inserted tool result for {tool_call_id} at index {insert_idx}")
        return new_messages
    
    def ensure_tool_results_after_assistant(
        self,
        messages: list[AgentMessage],
    ) -> list[AgentMessage]:
        """
        Reorder messages to ensure all tool results appear after their corresponding assistant message.
        
        This is a repair function for messages that may have been added in the wrong order.
        
        Returns:
            Reordered message list
        """
        # Collect tool results that need to be moved
        tool_results = []
        other_messages = []
        
        # Extract tool results and track their tool_call_ids
        for msg in messages:
            if msg.role == "tool":
                tool_results.append(msg)
            else:
                other_messages.append(msg)
        
        # Build corrected message list
        corrected = []
        pending_tool_results = tool_results.copy()
        
        for msg in other_messages:
            corrected.append(msg)
            
            # If this is an assistant message with tool calls, insert matching tool results
            if msg.role == "assistant" and hasattr(msg, 'tool_calls') and msg.tool_calls:
                tool_call_ids = {
                    tc.get("id") if isinstance(tc, dict) else tc.id
                    for tc in msg.tool_calls
                }
                
                # Find and insert matching tool results
                matched_results = []
                remaining_results = []
                
                for tr in pending_tool_results:
                    tr_id = tr.tool_call_id if hasattr(tr, 'tool_call_id') else None
                    if tr_id in tool_call_ids:
                        matched_results.append(tr)
                    else:
                        remaining_results.append(tr)
                
                corrected.extend(matched_results)
                pending_tool_results = remaining_results
        
        # Append any remaining tool results (orphaned)
        if pending_tool_results:
            logger.warning(f"Found {len(pending_tool_results)} orphaned tool results")
            corrected.extend(pending_tool_results)
        
        return corrected
    
    def check_provider_specific_rules(
        self,
        messages: list[AgentMessage],
        provider: str = "gemini"
    ) -> tuple[bool, str]:
        """
        Check provider-specific message ordering rules.
        
        Args:
            messages: Message list to check
            provider: Provider name ("gemini", "anthropic", etc.)
        
        Returns:
            (is_valid, error_message)
        """
        if provider.lower() == "gemini":
            return self._check_gemini_rules(messages)
        elif provider.lower() in ["anthropic", "claude"]:
            return self._check_anthropic_rules(messages)
        else:
            # Generic validation
            return self.validate_message_order(messages)
    
    def _check_gemini_rules(self, messages: list[AgentMessage]) -> tuple[bool, str]:
        """
        Gemini-specific rules:
        - function response turn (tool) must come immediately after function call turn (assistant with tool_calls)
        - No intervening messages allowed
        """
        for i in range(len(messages) - 1):
            curr = messages[i]
            next_msg = messages[i + 1]
            
            # If current is assistant with tool calls, next must be tool result
            if curr.role == "assistant" and hasattr(curr, 'tool_calls') and curr.tool_calls:
                if next_msg.role != "tool":
                    return False, f"Gemini: function call at index {i} not immediately followed by function response"
        
        return True, ""
    
    def _check_anthropic_rules(self, messages: list[AgentMessage]) -> tuple[bool, str]:
        """
        Anthropic-specific rules:
        - Tool results can be batched together after an assistant message
        - More flexible than Gemini
        """
        return self.validate_message_order(messages)

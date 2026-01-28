"""
Token analysis for context management
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class TokenAnalyzer:
    """
    Analyze token usage in messages

    Provides accurate token counting for different models
    """

    # Approximate tokens per character for different models
    TOKENS_PER_CHAR = {
        "claude": 0.25,  # Claude models
        "gpt": 0.25,  # GPT models
        "gemini": 0.25,  # Gemini models
        "default": 0.25,  # Default estimate
    }

    def __init__(self, model_name: str = "default"):
        """
        Initialize analyzer

        Args:
            model_name: Model name for token estimation
        """
        self.model_name = model_name
        self._tokenizer = None

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text

        Args:
            text: Text to analyze

        Returns:
            Estimated token count
        """
        if not text:
            return 0

        # Try to use actual tokenizer if available
        if self._tokenizer:
            try:
                return len(self._tokenizer.encode(text))
            except Exception:
                pass

        # Fall back to character-based estimation
        model_family = self._get_model_family()
        tokens_per_char = self.TOKENS_PER_CHAR.get(model_family, self.TOKENS_PER_CHAR["default"])

        return int(len(text) * tokens_per_char)

    def estimate_messages_tokens(self, messages: list[dict[str, Any]]) -> int:
        """
        Estimate token count for list of messages

        Args:
            messages: List of message dicts

        Returns:
            Estimated total token count
        """
        total = 0

        for msg in messages:
            # Count role tokens (2-4 tokens per message overhead)
            total += 4

            # Count content tokens
            content = msg.get("content", "")
            if isinstance(content, str):
                total += self.estimate_tokens(content)
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        if "text" in item:
                            total += self.estimate_tokens(item["text"])
                        elif "content" in item:
                            total += self.estimate_tokens(str(item["content"]))

        return total

    def get_message_importance(self, message: dict[str, Any]) -> float:
        """
        Calculate importance score for a message

        Args:
            message: Message dict

        Returns:
            Importance score (0.0 to 1.0)
        """
        score = 0.5  # Base score

        role = message.get("role", "")

        # System messages are important
        if role == "system":
            score = 1.0

        # Assistant messages with tool calls are important
        elif role == "assistant":
            if message.get("tool_calls"):
                score = 0.9
            else:
                score = 0.7

        # User messages are moderately important
        elif role == "user":
            score = 0.6

        # Tool results are less important (can be summarized)
        elif role == "tool":
            score = 0.4

        return score

    def _get_model_family(self) -> str:
        """Determine model family from model name"""
        model_lower = self.model_name.lower()

        if "claude" in model_lower:
            return "claude"
        elif "gpt" in model_lower:
            return "gpt"
        elif "gemini" in model_lower:
            return "gemini"
        else:
            return "default"

    def _load_tokenizer(self):
        """Load actual tokenizer if available"""
        try:
            model_family = self._get_model_family()

            if model_family == "gpt":
                import tiktoken

                self._tokenizer = tiktoken.encoding_for_model("gpt-4")

            # Add other tokenizers as needed

        except Exception as e:
            logger.debug(f"Could not load tokenizer: {e}")

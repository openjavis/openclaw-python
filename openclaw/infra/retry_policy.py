"""Retry policies for network operations.

Matches TypeScript src/infra/retry-policy.ts
"""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass
from typing import Callable, Optional, TypeVar, Any

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class RetryConfig:
    """Retry configuration."""
    
    attempts: int = 3
    min_delay_ms: int = 400
    max_delay_ms: int = 30000
    jitter: float = 0.1


TELEGRAM_RETRY_DEFAULTS = RetryConfig(
    attempts=3,
    min_delay_ms=400,
    max_delay_ms=30000,
    jitter=0.1,
)


async def retry_async(
    fn: Callable[[], T],
    config: Optional[RetryConfig] = None,
    should_retry: Optional[Callable[[Exception], bool]] = None,
    retry_after_ms: Optional[Callable[[Exception], Optional[int]]] = None,
    on_retry: Optional[Callable[[dict[str, Any]], None]] = None,
    label: Optional[str] = None,
) -> T:
    """Retry an async function with exponential backoff.
    
    Args:
        fn: Async function to retry
        config: Retry configuration
        should_retry: Function to determine if error is retryable
        retry_after_ms: Function to extract retry_after from error
        on_retry: Callback on retry
        label: Label for logging
    
    Returns:
        Result of fn()
    
    Raises:
        Last exception if all retries fail
    """
    if config is None:
        config = TELEGRAM_RETRY_DEFAULTS
    
    last_error = None
    
    for attempt in range(1, config.attempts + 1):
        try:
            return await fn()
        except Exception as e:
            last_error = e
            
            # Check if should retry
            if should_retry and not should_retry(e):
                raise
            
            if attempt >= config.attempts:
                raise
            
            # Calculate delay
            delay_ms = config.min_delay_ms * (2 ** (attempt - 1))
            delay_ms = min(delay_ms, config.max_delay_ms)
            
            # Add jitter
            if config.jitter > 0:
                jitter_amount = delay_ms * config.jitter
                delay_ms += random.uniform(-jitter_amount, jitter_amount)
            
            # Check for retry_after from error
            if retry_after_ms:
                custom_delay = retry_after_ms(e)
                if custom_delay is not None:
                    delay_ms = custom_delay
            
            delay_ms = max(0, delay_ms)
            
            # Call retry callback
            if on_retry:
                on_retry({
                    "attempt": attempt,
                    "max_attempts": config.attempts,
                    "delay_ms": delay_ms,
                    "label": label,
                    "error": str(e),
                })
            
            logger.debug(
                f"Retry {attempt}/{config.attempts} for {label or 'operation'} "
                f"after {delay_ms}ms: {e}"
            )
            
            await asyncio.sleep(delay_ms / 1000)
    
    raise last_error


def create_telegram_retry_runner(
    retry: Optional[RetryConfig] = None,
    config_retry: Optional[RetryConfig] = None,
    verbose: bool = False,
    should_retry: Optional[Callable[[Exception], bool]] = None,
):
    """Create a retry runner for Telegram API calls.
    
    Args:
        retry: Explicit retry config
        config_retry: Config from settings
        verbose: Enable verbose logging
        should_retry: Function to check if error is retryable
    
    Returns:
        Retry runner function
    """
    # Merge configs
    merged_config = TELEGRAM_RETRY_DEFAULTS
    if config_retry:
        merged_config = RetryConfig(
            attempts=config_retry.attempts or merged_config.attempts,
            min_delay_ms=config_retry.min_delay_ms or merged_config.min_delay_ms,
            max_delay_ms=config_retry.max_delay_ms or merged_config.max_delay_ms,
            jitter=config_retry.jitter if config_retry.jitter is not None else merged_config.jitter,
        )
    if retry:
        merged_config = RetryConfig(
            attempts=retry.attempts or merged_config.attempts,
            min_delay_ms=retry.min_delay_ms or merged_config.min_delay_ms,
            max_delay_ms=retry.max_delay_ms or merged_config.max_delay_ms,
            jitter=retry.jitter if retry.jitter is not None else merged_config.jitter,
        )
    
    def get_retry_after_ms(err: Exception) -> Optional[int]:
        """Extract retry_after from Telegram error."""
        err_str = str(err).lower()
        if "429" in err_str or "retry_after" in err_str:
            # Try to extract retry_after value
            # Format: "retry_after: 30" or similar
            import re
            match = re.search(r'retry[_\s]*after[:\s]*(\d+)', err_str, re.IGNORECASE)
            if match:
                seconds = int(match.group(1))
                return seconds * 1000
        return None
    
    async def runner(fn: Callable[[], T], label: Optional[str] = None) -> T:
        return await retry_async(
            fn,
            config=merged_config,
            should_retry=should_retry,
            retry_after_ms=get_retry_after_ms,
            on_retry=lambda info: (
                logger.info(
                    f"telegram {info.get('label', 'request')} retry "
                    f"{info['attempt']}/{info['max_attempts']} in {info['delay_ms']}ms"
                )
                if verbose
                else None
            ),
            label=label,
        )
    
    return runner

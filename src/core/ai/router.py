"""AI request router - directs tasks to appropriate AI backend.

This module provides intelligent routing of AI requests to either OpenRouter
(for simple, fast tasks) or Claude (for complex, high-quality tasks).

Features:
- Intelligent task routing based on complexity
- Exponential backoff for rate limit errors (T083)
- Graceful degradation with fallback between backends (T084)
"""

import asyncio
import logging
import random
from typing import Any, Optional

from src.models.config import Configuration
from src.core.ai.openrouter import OpenRouterClient, OpenRouterError
from src.core.ai.claude import ClaudeClient, ClaudeAPIError

logger = logging.getLogger(__name__)


# Rate limit retry configuration (T083)
MAX_RETRIES = 3
BASE_DELAY = 1.0  # seconds
MAX_DELAY = 30.0  # seconds
JITTER_FACTOR = 0.25  # 25% jitter


# Task type to backend mapping
SIMPLE_TASKS = {"tagging", "summarize_short", "classify", "extract_keywords"}
COMPLEX_TASKS = {"summarize_long", "generate_backlinks", "analyze", "organize", "research"}


class AIRouterError(Exception):
    """Base exception for AI Router errors."""
    pass


def _calculate_backoff_delay(attempt: int) -> float:
    """Calculate exponential backoff delay with jitter.

    Args:
        attempt: The current attempt number (0-indexed)

    Returns:
        Delay in seconds
    """
    # Exponential backoff: BASE_DELAY * 2^attempt
    delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)

    # Add jitter to prevent thundering herd
    jitter = delay * JITTER_FACTOR * random.uniform(-1, 1)
    return max(0.1, delay + jitter)


def _is_rate_limit_error(error: Exception) -> bool:
    """Check if an error is a rate limit error.

    Args:
        error: The exception to check

    Returns:
        True if this is a rate limit error that should be retried
    """
    error_str = str(error).lower()
    rate_limit_indicators = ["rate limit", "rate_limit", "429", "too many requests"]
    return any(indicator in error_str for indicator in rate_limit_indicators)


def _is_temporary_error(error: Exception) -> bool:
    """Check if an error is temporary and might succeed on retry.

    Args:
        error: The exception to check

    Returns:
        True if this is a temporary error
    """
    error_str = str(error).lower()
    temporary_indicators = [
        "timeout", "connection", "network", "unavailable",
        "500", "502", "503", "504", "overloaded"
    ]
    return any(indicator in error_str for indicator in temporary_indicators)


class AIRouter:
    """Routes AI requests to the appropriate backend.

    This router uses lazy initialization to create clients only when needed,
    and intelligently routes requests based on task complexity:
    - Simple tasks (tagging, classification) -> OpenRouter (fast, cost-effective)
    - Complex tasks (analysis, research) -> Claude (high-quality, powerful)

    Features:
    - Exponential backoff with jitter for rate limit handling (T083)
    - Graceful degradation: falls back to alternate backend on failure (T084)
    - Intelligent retry for temporary errors (T082)

    Attributes:
        _config: Configuration containing API keys and settings
        _openrouter: Lazily initialized OpenRouter client
        _claude: Lazily initialized Claude client
    """

    def __init__(self, config: Configuration) -> None:
        """Initialize the AI Router.

        Args:
            config: Configuration object containing API keys and settings
        """
        self._config = config
        self._openrouter: Optional[OpenRouterClient] = None
        self._claude: Optional[ClaudeClient] = None
        logger.info("Initialized AIRouter")

    @property
    def openrouter(self) -> OpenRouterClient:
        """Get or create OpenRouter client (lazy initialization).

        Returns:
            OpenRouterClient instance

        Raises:
            AIRouterError: If OpenRouter API key is not configured
        """
        if self._openrouter is None:
            if not self._config.openrouter_api_key:
                raise AIRouterError(
                    "OpenRouter API key not configured. "
                    "Please set openrouter_api_key in your configuration."
                )
            self._openrouter = OpenRouterClient(api_key=self._config.openrouter_api_key)
            logger.info("Initialized OpenRouter client")
        return self._openrouter

    @property
    def claude(self) -> ClaudeClient:
        """Get or create Claude client (lazy initialization).

        Returns:
            ClaudeClient instance

        Raises:
            AIRouterError: If Claude API key is not configured
        """
        if self._claude is None:
            if not self._config.claude_api_key:
                raise AIRouterError(
                    "Claude API key not configured. "
                    "Please set claude_api_key in your configuration."
                )
            self._claude = ClaudeClient(api_key=self._config.claude_api_key)
            logger.info("Initialized Claude client")
        return self._claude

    def _has_fallback(self, primary_backend: str) -> bool:
        """Check if a fallback backend is available.

        Args:
            primary_backend: The primary backend that failed

        Returns:
            True if alternate backend is configured
        """
        if primary_backend == "openrouter":
            return bool(self._config.claude_api_key)
        else:  # claude
            return bool(self._config.openrouter_api_key)

    def _get_fallback_client(self, primary_backend: str) -> tuple[str, Any]:
        """Get the fallback backend client.

        Args:
            primary_backend: The primary backend that failed

        Returns:
            Tuple of (backend_name, client)

        Raises:
            AIRouterError: If no fallback is available
        """
        if primary_backend == "openrouter":
            return ("claude", self.claude)
        else:  # claude
            return ("openrouter", self.openrouter)

    async def _make_request_with_retry(
        self,
        client: Any,
        backend: str,
        prompt: str,
        system_prompt: Optional[str],
        **kwargs: Any
    ) -> str:
        """Make an API request with exponential backoff retry (T083).

        Args:
            client: The AI client to use
            backend: Backend name for logging
            prompt: The prompt to send
            system_prompt: Optional system prompt
            **kwargs: Additional parameters

        Returns:
            The AI response

        Raises:
            OpenRouterError, ClaudeAPIError: If all retries fail
        """
        last_error: Optional[Exception] = None

        for attempt in range(MAX_RETRIES):
            try:
                response = await client.complete(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    **kwargs
                )
                return response

            except (OpenRouterError, ClaudeAPIError) as e:
                last_error = e

                # Check if we should retry
                if _is_rate_limit_error(e) or _is_temporary_error(e):
                    if attempt < MAX_RETRIES - 1:
                        delay = _calculate_backoff_delay(attempt)
                        logger.warning(
                            f"Retryable error from {backend} (attempt {attempt + 1}/{MAX_RETRIES}): {e}. "
                            f"Retrying in {delay:.2f}s..."
                        )
                        await asyncio.sleep(delay)
                        continue

                # Non-retryable error or max retries reached
                raise

        # Should not reach here, but just in case
        if last_error:
            raise last_error
        raise AIRouterError(f"Unexpected: no response after {MAX_RETRIES} attempts")

    async def route_request(
        self,
        task_type: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any
    ) -> str:
        """Route an AI request to the appropriate backend.

        Routes the request based on task_type:
        - Simple tasks (SIMPLE_TASKS) -> OpenRouter
        - Complex tasks (COMPLEX_TASKS) -> Claude
        - Unknown tasks -> Claude (default to quality)

        Features (T082, T083, T084):
        - Exponential backoff with jitter for rate limit errors
        - Automatic retry for temporary network errors
        - Graceful degradation: falls back to alternate backend on failure

        Args:
            task_type: Type of task to perform (e.g., "tagging", "analyze")
            prompt: The prompt to send to the AI
            system_prompt: Optional system prompt for context/behavior
            **kwargs: Additional parameters to pass to the backend
                     (e.g., temperature, max_tokens, model)

        Returns:
            The AI response as a string

        Raises:
            AIRouterError: If all backends fail
            ValueError: If prompt is empty
        """
        if not prompt:
            raise ValueError("Prompt cannot be empty")

        if not task_type:
            raise ValueError("Task type cannot be empty")

        # Normalize task type to lowercase for comparison
        normalized_task = task_type.lower().strip()

        # Determine which backend to use
        if normalized_task in SIMPLE_TASKS:
            backend = "openrouter"
            client = self.openrouter
            logger.debug(f"Routing task '{task_type}' to OpenRouter")
        elif normalized_task in COMPLEX_TASKS:
            backend = "claude"
            client = self.claude
            logger.debug(f"Routing task '{task_type}' to Claude")
        else:
            # Default to Claude for unknown tasks (prefer quality over speed)
            backend = "claude"
            client = self.claude
            logger.warning(
                f"Unknown task type '{task_type}', defaulting to Claude. "
                f"Known simple tasks: {SIMPLE_TASKS}. "
                f"Known complex tasks: {COMPLEX_TASKS}."
            )

        # Make the API call with retry logic (T083)
        try:
            response = await self._make_request_with_retry(
                client=client,
                backend=backend,
                prompt=prompt,
                system_prompt=system_prompt,
                **kwargs
            )
            logger.info(
                f"Successfully routed '{task_type}' to {backend}, "
                f"response length: {len(response)}"
            )
            return response

        except (OpenRouterError, ClaudeAPIError) as e:
            primary_error = e
            logger.warning(f"Primary backend {backend} failed: {e}")

            # Try fallback backend if available (T084 - graceful degradation)
            if self._has_fallback(backend):
                fallback_backend, fallback_client = self._get_fallback_client(backend)
                logger.info(f"Attempting fallback to {fallback_backend}...")

                try:
                    response = await self._make_request_with_retry(
                        client=fallback_client,
                        backend=fallback_backend,
                        prompt=prompt,
                        system_prompt=system_prompt,
                        **kwargs
                    )
                    logger.info(
                        f"Fallback to {fallback_backend} succeeded for '{task_type}', "
                        f"response length: {len(response)}"
                    )
                    return response

                except (OpenRouterError, ClaudeAPIError) as fallback_error:
                    # Both backends failed
                    error_msg = (
                        f"Both backends failed for '{task_type}'. "
                        f"Primary ({backend}): {primary_error}. "
                        f"Fallback ({fallback_backend}): {fallback_error}"
                    )
                    logger.error(error_msg)
                    raise AIRouterError(error_msg) from fallback_error

            # No fallback available
            error_msg = f"Failed to route '{task_type}' to {backend}: {str(e)}"
            logger.error(error_msg)
            raise AIRouterError(error_msg) from e

        except Exception as e:
            error_msg = f"Unexpected error routing '{task_type}' to {backend}: {str(e)}"
            logger.error(error_msg)
            raise AIRouterError(error_msg) from e

    async def close(self) -> None:
        """Close all initialized clients and cleanup resources.

        This should be called when the router is no longer needed to properly
        clean up HTTP connections and other resources.
        """
        if self._openrouter is not None:
            await self._openrouter.close()
            logger.info("Closed OpenRouter client")

        # Note: ClaudeClient doesn't currently have a close method,
        # but we check for it in case it's added in the future
        if self._claude is not None and hasattr(self._claude, 'close'):
            await self._claude.close()  # type: ignore
            logger.info("Closed Claude client")

    async def __aenter__(self) -> "AIRouter":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

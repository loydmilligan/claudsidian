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
import time
from dataclasses import dataclass
from typing import Any, Optional

from src.models.config import Configuration, ModelConfig
from src.core.ai.openrouter import OpenRouterClient, OpenRouterError, OpenRouterResponse
from src.core.ai.claude import ClaudeClient, ClaudeAPIError, ClaudeResponse

logger = logging.getLogger(__name__)


@dataclass
class AIResponse:
    """Response from an AI request with metadata."""

    content: str
    backend: str  # "claude" or "openrouter"
    model: str  # e.g., "claude-sonnet-4-20250514" or "anthropic/claude-3-haiku"
    temperature: float
    max_tokens: int
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0  # Estimated cost in USD
    time_seconds: float = 0.0  # Response time in seconds


# Model pricing per million tokens (input, output) in USD
# Updated December 2024 - check for latest pricing
MODEL_PRICING: dict[str, tuple[float, float]] = {
    # Anthropic direct API
    "claude-sonnet-4-20250514": (3.00, 15.00),
    "claude-3-haiku-20240307": (0.25, 1.25),
    # OpenRouter pricing (usually slightly higher due to margin)
    "anthropic/claude-3-haiku": (0.25, 1.25),
    "anthropic/claude-3.5-sonnet": (3.00, 15.00),
    "openai/gpt-4o-mini": (0.15, 0.60),
    "google/gemini-flash-1.5": (0.075, 0.30),
    # Free models (currently free tier on OpenRouter)
    "x-ai/grok-4.1-fast:free": (0.0, 0.0),
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost in USD for a model call.

    Args:
        model: Model ID
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens

    Returns:
        Estimated cost in USD
    """
    pricing = MODEL_PRICING.get(model)
    if not pricing:
        # Default to Haiku pricing for unknown models
        pricing = (0.25, 1.25)

    input_cost = (input_tokens / 1_000_000) * pricing[0]
    output_cost = (output_tokens / 1_000_000) * pricing[1]
    return input_cost + output_cost


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
    ) -> ClaudeResponse | OpenRouterResponse:
        """Make an API request with exponential backoff retry (T083).

        Args:
            client: The AI client to use
            backend: Backend name for logging
            prompt: The prompt to send
            system_prompt: Optional system prompt
            **kwargs: Additional parameters

        Returns:
            ClaudeResponse or OpenRouterResponse with content and token usage

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

    def _get_model_name(self, backend: str, client: Any) -> str:
        """Get the model name from a client."""
        if backend == "claude":
            return client.default_model
        else:
            return client.model

    async def route_request(
        self,
        task_type: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any
    ) -> AIResponse:
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
            AIResponse with content and metadata about the call

        Raises:
            AIRouterError: If all backends fail
            ValueError: If prompt is empty
        """
        if not prompt:
            raise ValueError("Prompt cannot be empty")

        if not task_type:
            raise ValueError("Task type cannot be empty")

        # Extract parameters for metadata (with defaults)
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens", 1024)

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
            model = self._get_model_name(backend, client)
            cost = estimate_cost(model, response.input_tokens, response.output_tokens)
            logger.info(
                f"Successfully routed '{task_type}' to {backend} ({model}), "
                f"response length: {len(response.content)}, "
                f"tokens: {response.input_tokens}in/{response.output_tokens}out, "
                f"cost: ${cost:.6f}"
            )
            return AIResponse(
                content=response.content,
                backend=backend,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                cost_usd=cost
            )

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
                    model = self._get_model_name(fallback_backend, fallback_client)
                    cost = estimate_cost(model, response.input_tokens, response.output_tokens)
                    logger.info(
                        f"Fallback to {fallback_backend} ({model}) succeeded for '{task_type}', "
                        f"response length: {len(response.content)}, "
                        f"tokens: {response.input_tokens}in/{response.output_tokens}out"
                    )
                    return AIResponse(
                        content=response.content,
                        backend=fallback_backend,
                        model=model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        input_tokens=response.input_tokens,
                        output_tokens=response.output_tokens,
                        cost_usd=cost
                    )

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

    async def route_with_model(
        self,
        backend: str,
        model: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any
    ) -> AIResponse:
        """Route an AI request to a specific backend and model.

        This method allows explicit control over which backend and model to use,
        bypassing the task-type based routing logic.

        Args:
            backend: Backend to use ("claude" or "openrouter")
            model: Model ID to use (e.g., "claude-sonnet-4-20250514" or "anthropic/claude-3-haiku")
            prompt: The prompt to send to the AI
            system_prompt: Optional system prompt for context/behavior
            **kwargs: Additional parameters to pass to the backend
                     (e.g., temperature, max_tokens)

        Returns:
            AIResponse with content and metadata about the call

        Raises:
            AIRouterError: If the backend fails
            ValueError: If prompt is empty or backend is invalid
        """
        if not prompt:
            raise ValueError("Prompt cannot be empty")

        if backend not in ("claude", "openrouter"):
            raise ValueError(f"Invalid backend: {backend}. Must be 'claude' or 'openrouter'")

        # Extract parameters for metadata (with defaults)
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens", 1024)

        # Add model to kwargs so client uses it
        kwargs["model"] = model

        # Get the appropriate client
        if backend == "claude":
            client = self.claude
        else:
            client = self.openrouter

        logger.debug(f"Direct routing to {backend} with model {model}")

        # Make the API call with retry logic and timing
        try:
            start_time = time.perf_counter()
            response = await self._make_request_with_retry(
                client=client,
                backend=backend,
                prompt=prompt,
                system_prompt=system_prompt,
                **kwargs
            )
            elapsed_time = time.perf_counter() - start_time
            cost = estimate_cost(model, response.input_tokens, response.output_tokens)
            logger.info(
                f"Successfully routed to {backend} ({model}), "
                f"response length: {len(response.content)}, "
                f"tokens: {response.input_tokens}in/{response.output_tokens}out, "
                f"cost: ${cost:.6f}, time: {elapsed_time:.2f}s"
            )
            return AIResponse(
                content=response.content,
                backend=backend,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                cost_usd=cost,
                time_seconds=elapsed_time
            )

        except (OpenRouterError, ClaudeAPIError) as e:
            primary_error = e
            logger.warning(f"Backend {backend} failed: {e}")

            # Try fallback backend if available
            if self._has_fallback(backend):
                fallback_backend, fallback_client = self._get_fallback_client(backend)
                logger.info(f"Attempting fallback to {fallback_backend}...")

                # Remove explicit model for fallback (use default)
                fallback_kwargs = {k: v for k, v in kwargs.items() if k != "model"}

                try:
                    response = await self._make_request_with_retry(
                        client=fallback_client,
                        backend=fallback_backend,
                        prompt=prompt,
                        system_prompt=system_prompt,
                        **fallback_kwargs
                    )
                    fallback_model = self._get_model_name(fallback_backend, fallback_client)
                    cost = estimate_cost(fallback_model, response.input_tokens, response.output_tokens)
                    logger.info(
                        f"Fallback to {fallback_backend} ({fallback_model}) succeeded, "
                        f"response length: {len(response.content)}, "
                        f"tokens: {response.input_tokens}in/{response.output_tokens}out"
                    )
                    return AIResponse(
                        content=response.content,
                        backend=fallback_backend,
                        model=fallback_model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        input_tokens=response.input_tokens,
                        output_tokens=response.output_tokens,
                        cost_usd=cost
                    )

                except (OpenRouterError, ClaudeAPIError) as fallback_error:
                    error_msg = (
                        f"Both backends failed. "
                        f"Primary ({backend}): {primary_error}. "
                        f"Fallback ({fallback_backend}): {fallback_error}"
                    )
                    logger.error(error_msg)
                    raise AIRouterError(error_msg) from fallback_error

            # No fallback available
            error_msg = f"Failed to route to {backend}: {str(e)}"
            logger.error(error_msg)
            raise AIRouterError(error_msg) from e

        except Exception as e:
            error_msg = f"Unexpected error routing to {backend}: {str(e)}"
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

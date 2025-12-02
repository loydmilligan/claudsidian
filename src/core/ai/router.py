"""AI request router - directs tasks to appropriate AI backend.

This module provides intelligent routing of AI requests to either OpenRouter
(for simple, fast tasks) or Claude (for complex, high-quality tasks).
"""

import logging
from typing import Any, Optional

from src.models.config import Configuration
from src.core.ai.openrouter import OpenRouterClient, OpenRouterError
from src.core.ai.claude import ClaudeClient, ClaudeAPIError

logger = logging.getLogger(__name__)


# Task type to backend mapping
SIMPLE_TASKS = {"tagging", "summarize_short", "classify", "extract_keywords"}
COMPLEX_TASKS = {"summarize_long", "generate_backlinks", "analyze", "organize", "research"}


class AIRouterError(Exception):
    """Base exception for AI Router errors."""
    pass


class AIRouter:
    """Routes AI requests to the appropriate backend.

    This router uses lazy initialization to create clients only when needed,
    and intelligently routes requests based on task complexity:
    - Simple tasks (tagging, classification) -> OpenRouter (fast, cost-effective)
    - Complex tasks (analysis, research) -> Claude (high-quality, powerful)

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

        Args:
            task_type: Type of task to perform (e.g., "tagging", "analyze")
            prompt: The prompt to send to the AI
            system_prompt: Optional system prompt for context/behavior
            **kwargs: Additional parameters to pass to the backend
                     (e.g., temperature, max_tokens, model)

        Returns:
            The AI response as a string

        Raises:
            AIRouterError: If the request fails or backend is unavailable
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

        # Make the API call
        try:
            response = await client.complete(
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

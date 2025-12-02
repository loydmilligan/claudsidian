"""OpenRouter API wrapper using OpenAI SDK.

This module provides a client for interacting with OpenRouter's API,
which is compatible with the OpenAI SDK.
"""

from typing import Optional

from openai import AsyncOpenAI, OpenAIError


class OpenRouterError(Exception):
    """Base exception for OpenRouter-related errors."""

    pass


class OpenRouterClient:
    """Client for interacting with OpenRouter API.

    This client uses the OpenAI SDK with a custom base URL to interact
    with OpenRouter's API, which provides access to various AI models
    including Claude models.

    Attributes:
        DEFAULT_MODEL: Default model to use for completions.
        BASE_URL: OpenRouter API base URL.
    """

    DEFAULT_MODEL = "anthropic/claude-3-haiku"
    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(self, api_key: str, model: Optional[str] = None):
        """Initialize the OpenRouter client.

        Args:
            api_key: OpenRouter API key for authentication.
            model: Model to use for completions. Defaults to claude-3-haiku.

        Raises:
            ValueError: If api_key is empty or None.
        """
        if not api_key:
            raise ValueError("API key cannot be empty")

        self.model = model or self.DEFAULT_MODEL
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=self.BASE_URL,
        )

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        """Get a completion from the OpenRouter API.

        Args:
            prompt: The user prompt to send to the model.
            system_prompt: Optional system prompt to guide model behavior.
            model: Model to use for this specific completion. Overrides instance model.
            temperature: Sampling temperature (0.0 to 2.0). Higher values make output
                more random, lower values more deterministic.
            max_tokens: Maximum number of tokens to generate.

        Returns:
            The completion text from the model.

        Raises:
            OpenRouterError: If the API request fails or returns an error.
            ValueError: If prompt is empty.
        """
        if not prompt:
            raise ValueError("Prompt cannot be empty")

        # Build messages array
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Use provided model or fall back to instance model
        selected_model = model or self.model

        try:
            response = await self._client.chat.completions.create(
                model=selected_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # Extract the completion text
            if not response.choices:
                raise OpenRouterError("No completion choices returned from API")

            content = response.choices[0].message.content
            if content is None:
                raise OpenRouterError("Completion content is None")

            return content

        except OpenAIError as e:
            raise OpenRouterError(f"OpenRouter API error: {str(e)}") from e
        except Exception as e:
            raise OpenRouterError(f"Unexpected error during completion: {str(e)}") from e

    async def close(self):
        """Close the underlying HTTP client.

        This should be called when the client is no longer needed to properly
        clean up resources.
        """
        await self._client.close()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

"""OpenRouter API wrapper using OpenAI SDK.

This module provides a client for interacting with OpenRouter's API,
which is compatible with the OpenAI SDK.
"""

from dataclasses import dataclass
from typing import Optional

from openai import AsyncOpenAI, OpenAIError


@dataclass
class OpenRouterResponse:
    """Response from OpenRouter API with usage metadata."""
    content: str
    input_tokens: int
    output_tokens: int


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

    # App identification for OpenRouter dashboard
    APP_NAME = "Claudsidian"
    APP_URL = "https://github.com/loydmilligan/claudsidian"

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
            default_headers={
                "HTTP-Referer": self.APP_URL,
                "X-Title": self.APP_NAME,
            },
        )

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        enable_reasoning: bool = False,
        image_data: Optional[str] = None,
        image_media_type: str = "image/png",
    ) -> OpenRouterResponse:
        """Get a completion from the OpenRouter API.

        Args:
            prompt: The user prompt to send to the model.
            system_prompt: Optional system prompt to guide model behavior.
            model: Model to use for this specific completion. Overrides instance model.
            temperature: Sampling temperature (0.0 to 2.0). Higher values make output
                more random, lower values more deterministic.
            max_tokens: Maximum number of tokens to generate.
            enable_reasoning: Enable reasoning mode for models that support it.
            image_data: Optional base64-encoded image data for vision models.
            image_media_type: MIME type of the image (default: image/png).

        Returns:
            OpenRouterResponse with completion text and token usage.

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

        # Build user message - with image if provided
        if image_data:
            # Multimodal message with image and text
            user_content = [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{image_media_type};base64,{image_data}"
                    }
                },
                {
                    "type": "text",
                    "text": prompt
                }
            ]
            messages.append({"role": "user", "content": user_content})
        else:
            messages.append({"role": "user", "content": prompt})

        # Use provided model or fall back to instance model
        selected_model = model or self.model

        try:
            # Build extra parameters for OpenRouter
            extra_body = {}
            if not enable_reasoning:
                # Explicitly disable reasoning for models that support it
                # This ensures we get content in the standard 'content' field
                extra_body["reasoning"] = {"effort": "none"}

            response = await self._client.chat.completions.create(
                model=selected_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                extra_body=extra_body if extra_body else None,
            )

            # Extract the completion text
            if not response.choices:
                raise OpenRouterError("No completion choices returned from API")

            message = response.choices[0].message
            content = message.content

            # For reasoning models (like Gemini-3-Pro-Preview, o1), the actual
            # response might be in the 'reasoning' field instead of 'content'
            if not content and hasattr(message, 'reasoning') and message.reasoning:
                content = message.reasoning

            if not content:
                raise OpenRouterError("Completion content is empty")

            # Extract token usage
            input_tokens = response.usage.prompt_tokens if response.usage else 0
            output_tokens = response.usage.completion_tokens if response.usage else 0

            return OpenRouterResponse(
                content=content,
                input_tokens=input_tokens,
                output_tokens=output_tokens
            )

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

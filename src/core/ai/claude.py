"""Claude API wrapper using the Anthropic SDK.

This module provides a simple interface for interacting with the Claude API
for tasks like summarization and tagging.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from anthropic import Anthropic, APIError, APIConnectionError, RateLimitError

logger = logging.getLogger(__name__)


@dataclass
class ClaudeResponse:
    """Response from Claude API with usage metadata."""
    content: str
    input_tokens: int
    output_tokens: int


class ClaudeAPIError(Exception):
    """Base exception for Claude API errors."""
    pass


class ClaudeClient:
    """Client for interacting with the Claude API.

    This class provides a simple interface for making completions with Claude,
    with configurable models and error handling.

    Attributes:
        client: The Anthropic client instance.
        default_model: The default model to use for completions.
    """

    DEFAULT_MODEL = "claude-sonnet-4-20250514"
    DEFAULT_MAX_TOKENS = 4096

    def __init__(self, api_key: str, default_model: Optional[str] = None):
        """Initialize the Claude client.

        Args:
            api_key: The Anthropic API key.
            default_model: The default model to use. Defaults to claude-3-sonnet.

        Raises:
            ValueError: If api_key is empty or None.
        """
        if not api_key:
            raise ValueError("API key cannot be empty")

        self.client = Anthropic(api_key=api_key)
        self.default_model = default_model or self.DEFAULT_MODEL
        logger.info(f"Initialized ClaudeClient with model: {self.default_model}")

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 1.0,
    ) -> ClaudeResponse:
        """Get a completion from Claude.

        Args:
            prompt: The user prompt to send to Claude.
            system_prompt: Optional system prompt to set context/behavior.
            model: The model to use. If None, uses the default model.
            max_tokens: Maximum tokens to generate. Defaults to 4096.
            temperature: Sampling temperature (0-1). Defaults to 1.0.

        Returns:
            ClaudeResponse with completion text and token usage.

        Raises:
            ClaudeAPIError: If there's an error communicating with the API.
            ValueError: If prompt is empty.
        """
        if not prompt:
            raise ValueError("Prompt cannot be empty")

        model_to_use = model or self.default_model
        max_tokens_to_use = max_tokens or self.DEFAULT_MAX_TOKENS

        try:
            logger.debug(f"Sending completion request to {model_to_use}")

            # Build the message structure
            messages = [
                {
                    "role": "user",
                    "content": prompt
                }
            ]

            # Prepare API call parameters
            api_params = {
                "model": model_to_use,
                "max_tokens": max_tokens_to_use,
                "messages": messages,
                "temperature": temperature,
            }

            # Add system prompt if provided
            if system_prompt:
                api_params["system"] = system_prompt

            # Make the API call
            response = self.client.messages.create(**api_params)

            # Extract the text from the response
            if not response.content:
                raise ClaudeAPIError("Received empty response from Claude API")

            # Get the first content block's text
            completion_text = response.content[0].text

            # Extract token usage
            input_tokens = response.usage.input_tokens if response.usage else 0
            output_tokens = response.usage.output_tokens if response.usage else 0

            logger.debug(
                f"Received completion: {len(completion_text)} chars, "
                f"{input_tokens} in / {output_tokens} out tokens"
            )

            return ClaudeResponse(
                content=completion_text,
                input_tokens=input_tokens,
                output_tokens=output_tokens
            )

        except RateLimitError as e:
            logger.error(f"Rate limit error: {e}")
            raise ClaudeAPIError(f"Rate limit exceeded: {e}") from e

        except APIConnectionError as e:
            logger.error(f"API connection error: {e}")
            raise ClaudeAPIError(f"Failed to connect to Claude API: {e}") from e

        except APIError as e:
            logger.error(f"API error: {e}")
            raise ClaudeAPIError(f"Claude API error: {e}") from e

        except Exception as e:
            logger.error(f"Unexpected error during completion: {e}")
            raise ClaudeAPIError(f"Unexpected error: {e}") from e

    async def complete_with_image(
        self,
        prompt: str,
        image_data: str,
        media_type: str = "image/png",
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 1.0,
    ) -> ClaudeResponse:
        """Get a completion from Claude with an image input.

        Uses Claude's vision capabilities to analyze images.

        Args:
            prompt: The user prompt describing what to analyze
            image_data: Base64-encoded image data
            media_type: Image MIME type (image/png, image/jpeg, image/webp, image/gif)
            system_prompt: Optional system prompt
            model: Model to use (must support vision - sonnet/opus)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            ClaudeResponse with analysis and token usage

        Raises:
            ClaudeAPIError: If there's an error with the API
        """
        if not prompt:
            raise ValueError("Prompt cannot be empty")
        if not image_data:
            raise ValueError("Image data cannot be empty")

        # Vision requires a capable model
        model_to_use = model or "claude-sonnet-4-20250514"
        max_tokens_to_use = max_tokens or self.DEFAULT_MAX_TOKENS

        try:
            logger.debug(f"Sending vision request to {model_to_use}")

            # Build message with image
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]

            api_params = {
                "model": model_to_use,
                "max_tokens": max_tokens_to_use,
                "messages": messages,
                "temperature": temperature,
            }

            if system_prompt:
                api_params["system"] = system_prompt

            response = self.client.messages.create(**api_params)

            if not response.content:
                raise ClaudeAPIError("Received empty response from Claude API")

            completion_text = response.content[0].text
            input_tokens = response.usage.input_tokens if response.usage else 0
            output_tokens = response.usage.output_tokens if response.usage else 0

            logger.debug(
                f"Received vision completion: {len(completion_text)} chars, "
                f"{input_tokens} in / {output_tokens} out tokens"
            )

            return ClaudeResponse(
                content=completion_text,
                input_tokens=input_tokens,
                output_tokens=output_tokens
            )

        except RateLimitError as e:
            logger.error(f"Rate limit error: {e}")
            raise ClaudeAPIError(f"Rate limit exceeded: {e}") from e

        except APIConnectionError as e:
            logger.error(f"API connection error: {e}")
            raise ClaudeAPIError(f"Failed to connect to Claude API: {e}") from e

        except APIError as e:
            logger.error(f"API error: {e}")
            raise ClaudeAPIError(f"Claude API error: {e}") from e

        except Exception as e:
            logger.error(f"Unexpected error during vision completion: {e}")
            raise ClaudeAPIError(f"Unexpected error: {e}") from e

    async def close(self) -> None:
        """Close the client (no-op for sync client, but keeps interface consistent)."""
        pass

    def complete_sync(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 1.0,
    ) -> ClaudeResponse:
        """Synchronous version of complete().

        This is a convenience method for non-async contexts. For async code,
        prefer using the async complete() method.

        Args:
            prompt: The user prompt to send to Claude.
            system_prompt: Optional system prompt to set context/behavior.
            model: The model to use. If None, uses the default model.
            max_tokens: Maximum tokens to generate. Defaults to 4096.
            temperature: Sampling temperature (0-1). Defaults to 1.0.

        Returns:
            ClaudeResponse with completion text and token usage.

        Raises:
            ClaudeAPIError: If there's an error communicating with the API.
            ValueError: If prompt is empty.
        """
        if not prompt:
            raise ValueError("Prompt cannot be empty")

        model_to_use = model or self.default_model
        max_tokens_to_use = max_tokens or self.DEFAULT_MAX_TOKENS

        try:
            logger.debug(f"Sending sync completion request to {model_to_use}")

            # Build the message structure
            messages = [
                {
                    "role": "user",
                    "content": prompt
                }
            ]

            # Prepare API call parameters
            api_params = {
                "model": model_to_use,
                "max_tokens": max_tokens_to_use,
                "messages": messages,
                "temperature": temperature,
            }

            # Add system prompt if provided
            if system_prompt:
                api_params["system"] = system_prompt

            # Make the API call (synchronous)
            response = self.client.messages.create(**api_params)

            # Extract the text from the response
            if not response.content:
                raise ClaudeAPIError("Received empty response from Claude API")

            # Get the first content block's text
            completion_text = response.content[0].text

            # Extract token usage
            input_tokens = response.usage.input_tokens if response.usage else 0
            output_tokens = response.usage.output_tokens if response.usage else 0

            logger.debug(
                f"Received completion: {len(completion_text)} chars, "
                f"{input_tokens} in / {output_tokens} out tokens"
            )

            return ClaudeResponse(
                content=completion_text,
                input_tokens=input_tokens,
                output_tokens=output_tokens
            )

        except RateLimitError as e:
            logger.error(f"Rate limit error: {e}")
            raise ClaudeAPIError(f"Rate limit exceeded: {e}") from e

        except APIConnectionError as e:
            logger.error(f"API connection error: {e}")
            raise ClaudeAPIError(f"Failed to connect to Claude API: {e}") from e

        except APIError as e:
            logger.error(f"API error: {e}")
            raise ClaudeAPIError(f"Claude API error: {e}") from e

        except Exception as e:
            logger.error(f"Unexpected error during completion: {e}")
            raise ClaudeAPIError(f"Unexpected error: {e}") from e

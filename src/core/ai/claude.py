"""Claude API wrapper using the Anthropic SDK.

This module provides a simple interface for interacting with the Claude API
for tasks like summarization and tagging.
"""

import logging
from typing import Optional

from anthropic import Anthropic, APIError, APIConnectionError, RateLimitError

logger = logging.getLogger(__name__)


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

    DEFAULT_MODEL = "claude-3-sonnet-20240229"
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
    ) -> str:
        """Get a completion from Claude.

        Args:
            prompt: The user prompt to send to Claude.
            system_prompt: Optional system prompt to set context/behavior.
            model: The model to use. If None, uses the default model.
            max_tokens: Maximum tokens to generate. Defaults to 4096.
            temperature: Sampling temperature (0-1). Defaults to 1.0.

        Returns:
            The completion text from Claude.

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

            logger.debug(f"Received completion of length {len(completion_text)}")
            return completion_text

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

    def complete_sync(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 1.0,
    ) -> str:
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
            The completion text from Claude.

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

            logger.debug(f"Received completion of length {len(completion_text)}")
            return completion_text

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

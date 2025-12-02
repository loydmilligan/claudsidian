"""AI integration module for Claude and OpenRouter APIs."""

from src.core.ai.prompts import (
    Prompts,
    get_summarization_prompt,
    get_tag_generation_prompt,
)

__all__ = [
    "Prompts",
    "get_summarization_prompt",
    "get_tag_generation_prompt",
]

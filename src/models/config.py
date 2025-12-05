"""Configuration models for Claudsidian.

This module defines the configuration data models using Pydantic v2.
"""

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# Available model presets
AVAILABLE_MODELS = {
    # Claude models (via Anthropic API)
    "claude-sonnet-4": "claude-sonnet-4-20250514",
    "claude-haiku-3": "claude-3-haiku-20240307",
    # OpenRouter models
    "openrouter-haiku": "anthropic/claude-3-haiku",
    "openrouter-sonnet": "anthropic/claude-3.5-sonnet",
    "openrouter-gpt4o-mini": "openai/gpt-4o-mini",
    "openrouter-gemini-flash": "google/gemini-flash-1.5",
    "openrouter-grok-fast": "x-ai/grok-4.1-fast",
}

# Default model assignments
DEFAULT_SUMMARY_MODEL = "openrouter-grok-fast"  # x-ai/grok-4.1-fast
DEFAULT_TAGS_MODEL = "openrouter-haiku"
CHEAP_MODE_MODEL = "openrouter-haiku"


class ModelConfig(BaseModel):
    """Configuration for AI model selection per task.

    Attributes:
        summary_model: Model to use for summarization (default: claude-sonnet-4)
        tags_model: Model to use for tag generation (default: openrouter-haiku)
        cheap_mode: If True, use cheapest model for all tasks (overrides above)
    """

    summary_model: str = Field(
        default=DEFAULT_SUMMARY_MODEL,
        description="Model preset for summarization (e.g., claude-sonnet-4, openrouter-haiku)"
    )
    tags_model: str = Field(
        default=DEFAULT_TAGS_MODEL,
        description="Model preset for tag generation"
    )
    cheap_mode: bool = Field(
        default=False,
        description="Use cheapest model (openrouter-haiku) for all tasks"
    )

    def get_summary_model(self) -> tuple[str, str]:
        """Get backend and model ID for summarization.

        Returns:
            Tuple of (backend, model_id) where backend is 'claude' or 'openrouter'
        """
        if self.cheap_mode:
            return self._resolve_model(CHEAP_MODE_MODEL)
        return self._resolve_model(self.summary_model)

    def get_tags_model(self) -> tuple[str, str]:
        """Get backend and model ID for tag generation.

        Returns:
            Tuple of (backend, model_id) where backend is 'claude' or 'openrouter'
        """
        if self.cheap_mode:
            return self._resolve_model(CHEAP_MODE_MODEL)
        return self._resolve_model(self.tags_model)

    def _resolve_model(self, preset: str) -> tuple[str, str]:
        """Resolve a model preset to backend and model ID.

        Args:
            preset: Model preset name (e.g., 'claude-sonnet-4', 'openrouter-haiku')

        Returns:
            Tuple of (backend, model_id)
        """
        model_id = AVAILABLE_MODELS.get(preset, preset)
        if preset.startswith("claude-"):
            return ("claude", model_id)
        elif preset.startswith("openrouter-"):
            return ("openrouter", model_id)
        # If unknown preset, assume it's a raw model ID - try to guess backend
        elif "/" in preset:
            return ("openrouter", preset)
        else:
            return ("claude", preset)


class FolderConfig(BaseModel):
    """Mapping of content types to folder paths in the vault.

    Attributes:
        article: Folder for article content
        video: Folder for video content
        repo: Folder for repository/project content
        news: Folder for news content
        walkthrough: Folder for walkthrough/guide content
        printable: Folder for 3D printable models
    """

    article: str = Field(default="Learning", description="Folder for article content")
    video: str = Field(default="Videos", description="Folder for video content")
    repo: str = Field(default="Projects", description="Folder for repository/project content")
    news: str = Field(default="News", description="Folder for news content")
    walkthrough: str = Field(default="Guides", description="Folder for walkthrough/guide content")
    printable: str = Field(default="3D-Models", description="Folder for 3D printable models")


class Configuration(BaseModel):
    """Main configuration model for Claudsidian.

    Attributes:
        vault_path: Absolute path to the Obsidian vault
        claude_api_key: Optional Anthropic API key for Claude
        openrouter_api_key: Optional OpenRouter API key
        server_port: Port number for the local HTTP server
        inbox_file: Name of the inbox file in the vault root
        folders: Folder configuration for different content types
        models: AI model configuration for different tasks
        vision_model: Model to use for vision/image analysis (default: claude for Claude API)
    """

    vault_path: str = Field(
        ...,
        description="Absolute path to Obsidian vault"
    )
    claude_api_key: Optional[str] = Field(
        default=None,
        description="Anthropic API key"
    )
    openrouter_api_key: Optional[str] = Field(
        default=None,
        description="OpenRouter API key"
    )
    server_port: int = Field(
        default=8765,
        description="Local HTTP server port",
        ge=1,
        le=65535
    )
    inbox_file: str = Field(
        default="inbox.md",
        description="Inbox file name in vault root"
    )
    folders: FolderConfig = Field(
        default_factory=FolderConfig,
        description="Content type to folder mapping"
    )
    models: ModelConfig = Field(
        default_factory=ModelConfig,
        description="AI model configuration for different tasks"
    )
    vision_model: str = Field(
        default="google/gemini-2.0-flash-exp:free",
        description="Model for vision/image analysis. Use 'claude' for Claude API or OpenRouter model ID like 'qwen/qwen3-vl-32b-instruct'"
    )

    @field_validator('vault_path')
    @classmethod
    def validate_vault_path(cls, v: str) -> str:
        """Validate that vault_path is an absolute path.

        Args:
            v: The vault path to validate

        Returns:
            The validated vault path

        Raises:
            ValueError: If the path is not absolute
        """
        path = Path(v)
        if not path.is_absolute():
            raise ValueError(f"vault_path must be an absolute path, got: {v}")
        return v

    @model_validator(mode='after')
    def validate_api_keys(self) -> 'Configuration':
        """Validate that at least one API key is provided.

        Returns:
            The validated Configuration instance

        Raises:
            ValueError: If no API keys are provided
        """
        if not self.claude_api_key and not self.openrouter_api_key:
            raise ValueError(
                "At least one API key must be provided: "
                "claude_api_key or openrouter_api_key"
            )
        return self

    model_config = {
        "validate_assignment": True,
        "extra": "forbid",
        "str_strip_whitespace": True,
    }

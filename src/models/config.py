"""Configuration models for Claudsidian.

This module defines the configuration data models using Pydantic v2.
"""

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


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

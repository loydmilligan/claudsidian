"""Note model representing a captured piece of content in the Obsidian vault."""

from datetime import datetime
from typing import Optional

import yaml
from pydantic import BaseModel, Field, HttpUrl

from src.core.content_type import ContentType


class Frontmatter(BaseModel):
    """
    YAML frontmatter metadata for a note.

    Attributes:
        source: Original URL where the content was captured from
        captured: ISO 8601 timestamp when the content was captured
        type: Classification of the content type
        tags: Auto-generated tags for organizing and finding notes
        summary: Optional one-line summary for preview purposes
    """

    source: HttpUrl = Field(..., description="Original URL where content was captured")
    captured: datetime = Field(..., description="ISO 8601 capture timestamp")
    type: ContentType = Field(..., description="Content type classification")
    tags: list[str] = Field(default_factory=list, description="Auto-generated tags")
    summary: Optional[str] = Field(
        None, description="One-line summary for preview purposes"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "source": "https://example.com/article",
                    "captured": "2025-12-01T12:00:00Z",
                    "type": "article",
                    "tags": ["technology", "ai", "knowledge-management"],
                    "summary": "An introduction to AI-powered knowledge capture",
                }
            ]
        }
    }


class Note(BaseModel):
    """
    Represents a note stored in the Obsidian vault.

    A note combines a title, markdown content, and frontmatter metadata.
    The file_path indicates where the note is stored relative to the vault root.

    Attributes:
        title: Note title (also used as filename)
        content: Markdown body content
        frontmatter: YAML metadata block
        file_path: Relative path in vault where the note is stored
    """

    title: str = Field(..., description="Note title (also filename)")
    content: str = Field(..., description="Markdown body content")
    frontmatter: Frontmatter = Field(..., description="YAML metadata block")
    file_path: str = Field(..., description="Relative path in vault")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "title": "AI-Powered Knowledge Capture",
                    "content": "# AI-Powered Knowledge Capture\n\nThis is the main content...",
                    "frontmatter": {
                        "source": "https://example.com/article",
                        "captured": "2025-12-01T12:00:00Z",
                        "type": "article",
                        "tags": ["technology", "ai"],
                        "summary": "Introduction to AI knowledge capture",
                    },
                    "file_path": "articles/ai-powered-knowledge-capture.md",
                }
            ]
        }
    }

    def to_markdown(self) -> str:
        """
        Render the note as markdown with YAML frontmatter.

        The output format follows Obsidian's expected structure:
        - YAML frontmatter enclosed in --- delimiters
        - Markdown content following the frontmatter

        Returns:
            Complete markdown document with frontmatter and content

        Example:
            >>> note = Note(
            ...     title="Example Note",
            ...     content="# Example\\n\\nContent here.",
            ...     frontmatter=Frontmatter(
            ...         source="https://example.com",
            ...         captured=datetime.now(),
            ...         type=ContentType.ARTICLE,
            ...         tags=["example"],
            ...         summary="Example note"
            ...     ),
            ...     file_path="notes/example.md"
            ... )
            >>> markdown = note.to_markdown()
            >>> print(markdown)
            ---
            source: https://example.com
            captured: '2025-12-01T12:00:00Z'
            type: article
            tags:
              - example
            summary: Example note
            ---

            # Example

            Content here.
        """
        # Convert frontmatter to dictionary, handling special types
        frontmatter_dict = {
            "source": str(self.frontmatter.source),
            "captured": self.frontmatter.captured.isoformat(),
            "type": self.frontmatter.type.value,
            "tags": self.frontmatter.tags,
        }

        # Only include summary if it's not None
        if self.frontmatter.summary is not None:
            frontmatter_dict["summary"] = self.frontmatter.summary

        # Serialize frontmatter to YAML
        yaml_content = yaml.dump(
            frontmatter_dict,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

        # Combine frontmatter and content
        markdown = f"---\n{yaml_content}---\n\n{self.content}"

        return markdown

    @classmethod
    def from_markdown(cls, markdown_text: str, file_path: str, title: str) -> "Note":
        """
        Parse a markdown document with YAML frontmatter into a Note object.

        Args:
            markdown_text: Complete markdown document including frontmatter
            file_path: Relative path in vault where the note is stored
            title: Note title

        Returns:
            Note object parsed from the markdown

        Raises:
            ValueError: If the markdown doesn't contain valid frontmatter

        Example:
            >>> markdown = '''---
            ... source: https://example.com
            ... captured: '2025-12-01T12:00:00Z'
            ... type: article
            ... tags:
            ...   - example
            ... summary: Example note
            ... ---
            ...
            ... # Example
            ...
            ... Content here.
            ... '''
            >>> note = Note.from_markdown(markdown, "notes/example.md", "Example")
        """
        # Split frontmatter and content
        if not markdown_text.startswith("---"):
            raise ValueError("Markdown must start with YAML frontmatter delimiter (---)")

        parts = markdown_text.split("---", 2)
        if len(parts) < 3:
            raise ValueError("Invalid frontmatter format")

        # Parse YAML frontmatter
        yaml_content = parts[1].strip()
        content = parts[2].strip()

        frontmatter_dict = yaml.safe_load(yaml_content)

        # Create Frontmatter object
        frontmatter = Frontmatter(
            source=frontmatter_dict["source"],
            captured=datetime.fromisoformat(frontmatter_dict["captured"]),
            type=ContentType(frontmatter_dict["type"]),
            tags=frontmatter_dict.get("tags", []),
            summary=frontmatter_dict.get("summary"),
        )

        return cls(
            title=title,
            content=content,
            frontmatter=frontmatter,
            file_path=file_path,
        )

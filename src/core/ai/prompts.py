"""AI prompt templates for content processing.

This module provides structured prompts for various AI tasks including
article summarization and tag generation. Prompts are designed to produce
consistent, high-quality outputs suitable for knowledge management.
"""

from typing import Tuple


class Prompts:
    """Collection of AI prompt templates for content processing.

    This class organizes system prompts used across different AI tasks.
    Each prompt is crafted to produce specific, actionable outputs that
    integrate well with Obsidian's knowledge management workflow.
    """

    ARTICLE_SUMMARY = """You are a helpful assistant that creates concise summaries.
Given an article's content, provide a 2-3 sentence summary that captures:
1. The main topic or argument
2. Key insights or conclusions
3. Why this might be valuable to save

Keep it clear and informative. Do not use phrases like "This article discusses..." - just state the content directly."""

    ARTICLE_TAGS = """You are a helpful assistant that generates tags for knowledge management.
Given content, generate 5-10 relevant tags following these rules:
1. Use lowercase with hyphens (e.g., machine-learning, not Machine Learning)
2. Include topic tags (what it's about)
3. Include technology tags if applicable (python, react, etc.)
4. Be specific enough to be useful for searching
5. Return ONLY a comma-separated list of tags, nothing else"""

    VIDEO_SUMMARY = """You are a helpful assistant that creates concise summaries of video content.
Given a video transcript or description, provide a 2-3 sentence summary that captures:
1. The main topic or theme
2. Key takeaways or learning points
3. Why this content is worth reviewing

Keep it clear and actionable. Focus on the content's value, not the format."""

    REPO_SUMMARY = """You are a helpful assistant that summarizes code repositories.
Given repository information, provide a 2-3 sentence summary that captures:
1. What the project does and its primary purpose
2. Key technologies or notable implementation details
3. Why this repository might be useful or interesting

Keep it technical but accessible. Focus on practical value."""


def get_summarization_prompt(content: str, content_type: str = "article") -> Tuple[str, str]:
    """Get system and user prompts for content summarization.

    Creates appropriate prompts based on the content type. Currently supports
    articles, videos, and repositories, with extensibility for future types.

    Args:
        content: The content to summarize (article text, transcript, README, etc.)
        content_type: Type of content ("article", "video", "repo"). Defaults to "article".

    Returns:
        Tuple of (system_prompt, user_prompt) ready for AI completion

    Raises:
        ValueError: If content is empty or content_type is invalid

    Example:
        >>> system, user = get_summarization_prompt(article_text, "article")
        >>> summary = await ai_client.complete(user, system_prompt=system)
    """
    if not content or not content.strip():
        raise ValueError("Content cannot be empty")

    content_type = content_type.lower().strip()

    # Select appropriate system prompt based on content type
    if content_type == "article":
        system_prompt = Prompts.ARTICLE_SUMMARY
    elif content_type == "video":
        system_prompt = Prompts.VIDEO_SUMMARY
    elif content_type == "repo":
        system_prompt = Prompts.REPO_SUMMARY
    else:
        raise ValueError(
            f"Invalid content_type: {content_type}. "
            f"Must be one of: article, video, repo"
        )

    # Create the user prompt with the actual content
    user_prompt = f"Please summarize the following {content_type} content:\n\n{content}"

    return system_prompt, user_prompt


def get_tag_generation_prompt(content: str, title: str) -> Tuple[str, str]:
    """Get system and user prompts for tag generation.

    Creates prompts for generating relevant tags from content. Tags are
    designed to work with Obsidian's tagging system and follow consistent
    formatting rules for searchability.

    Args:
        content: The full content to analyze for tag generation
        title: The title or headline of the content (provides additional context)

    Returns:
        Tuple of (system_prompt, user_prompt) ready for AI completion

    Raises:
        ValueError: If content or title is empty

    Example:
        >>> system, user = get_tag_generation_prompt(article_text, article_title)
        >>> tags_csv = await ai_client.complete(user, system_prompt=system)
        >>> tags = [tag.strip() for tag in tags_csv.split(',')]
    """
    if not content or not content.strip():
        raise ValueError("Content cannot be empty")

    if not title or not title.strip():
        raise ValueError("Title cannot be empty")

    system_prompt = Prompts.ARTICLE_TAGS

    # Create the user prompt with both title and content for context
    user_prompt = f"""Title: {title}

Content:
{content}

Generate tags for this content."""

    return system_prompt, user_prompt

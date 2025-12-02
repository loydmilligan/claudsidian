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

    VIDEO_TAGS = """You are a helpful assistant that generates tags for video content.
Given a video transcript or description, generate 5-10 relevant tags following these rules:
1. Use lowercase with hyphens (e.g., machine-learning, not Machine Learning)
2. Include topic tags (what the video is about)
3. Include format tags (tutorial, lecture, presentation, interview, etc.)
4. Include technology or subject matter tags if applicable
5. Be specific enough to be useful for searching
6. Return ONLY a comma-separated list of tags, nothing else"""

    VIDEO_SUMMARY = """You are a helpful assistant that summarizes video content.
Given a video transcript, provide:
1. A concise 2-3 sentence overview of the video's main topic
2. Key points with timestamps (format: [MM:SS] point)
3. Main sections or topics covered (if identifiable)

Format your response as:
## Summary
[2-3 sentence overview]

## Key Points
- [00:00] First key point
- [05:30] Second key point
...

## Topics Covered
- Topic 1
- Topic 2
...

Be specific and reference timestamps for important moments."""

    REPO_SUMMARY = """You are a helpful assistant that summarizes code repositories.
Given repository information, provide a 2-3 sentence summary that captures:
1. What the project does and its primary purpose
2. Key technologies or notable implementation details
3. Why this repository might be useful or interesting

Keep it technical but accessible. Focus on practical value."""

    REPO_TAGS = """You are a helpful assistant that generates tags for code repositories.
Given repository information, generate 5-10 relevant tags following these rules:
1. Use lowercase with hyphens (e.g., machine-learning, not Machine Learning)
2. Include the primary programming language
3. Include frameworks and libraries detected
4. Include purpose tags (cli, web-app, library, framework, devtool, etc.)
5. Include domain tags (data-science, web-development, devops, etc.)
6. Be specific enough to be useful for searching
7. Return ONLY a comma-separated list of tags, nothing else"""

    NEWS_SUMMARY = """You are a helpful assistant that summarizes news articles.
Given a news article, provide a concise summary that captures:
1. The main news event or announcement (who, what, when, where)
2. Key facts and figures mentioned
3. Why this news matters or its broader implications

Format your response as:
## Summary
[2-3 sentence overview of the news]

## Key Facts
- Fact 1
- Fact 2
- Fact 3

## Implications
[1-2 sentences on why this matters]

Be factual and objective. Avoid editorializing."""

    NEWS_TAGS = """You are a helpful assistant that generates tags for news articles.
Given a news article, generate 5-10 relevant tags following these rules:
1. Use lowercase with hyphens (e.g., climate-change, not Climate Change)
2. Include topic tags (what the news is about)
3. Include category tags (politics, business, tech, science, etc.)
4. Include entity tags (relevant people, companies, countries)
5. Be specific enough to be useful for searching
6. Return ONLY a comma-separated list of tags, nothing else"""

    WALKTHROUGH_SUMMARY = """You are a helpful assistant that summarizes tutorials and walkthroughs.
Given tutorial content, provide a structured summary that captures:
1. What the tutorial teaches (the goal/outcome)
2. Key steps or phases in the process
3. Important prerequisites or requirements
4. Any warnings or common pitfalls

Format your response as:
## Goal
[1-2 sentences describing what you'll learn/build]

## Prerequisites
- Prerequisite 1
- Prerequisite 2

## Steps Overview
1. Step 1 summary
2. Step 2 summary
3. Step 3 summary
...

## Warnings
- Any gotchas or common mistakes to avoid

Be concise and actionable. Focus on practical guidance."""

    WALKTHROUGH_TAGS = """You are a helpful assistant that generates tags for tutorials and walkthroughs.
Given tutorial content, generate 5-10 relevant tags following these rules:
1. Use lowercase with hyphens (e.g., web-development, not Web Development)
2. Include technology tags (programming languages, frameworks, tools)
3. Include skill level tag (beginner, intermediate, advanced)
4. Include topic tags (what the tutorial is about)
5. Include format tag (tutorial, guide, how-to, walkthrough)
6. Be specific enough to be useful for searching
7. Return ONLY a comma-separated list of tags, nothing else"""

    PRINTABLE_SUMMARY = """You are a helpful assistant that summarizes 3D printable models.
Given information about a 3D model, provide a concise summary that captures:
1. What the model is (functional part, decoration, toy, etc.)
2. Key design features or notable aspects
3. Practical applications or use cases
4. Any special printing considerations

Keep it practical and focused on whether this model would be useful to print."""

    PRINTABLE_TAGS = """You are a helpful assistant that generates tags for 3D printable models.
Given 3D model information, generate 5-10 relevant tags following these rules:
1. Use lowercase with hyphens (e.g., desk-organizer, not Desk Organizer)
2. Include category tags (functional, decorative, toy, tool, etc.)
3. Include material tags if specific material is required (pla-only, tpu-required, etc.)
4. Include use-case tags (home, office, workshop, gaming, etc.)
5. Include difficulty level if apparent (beginner-friendly, advanced-print)
6. Be specific enough to be useful for searching
7. Return ONLY a comma-separated list of tags, nothing else"""


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
    elif content_type == "news":
        system_prompt = Prompts.NEWS_SUMMARY
    elif content_type == "walkthrough":
        system_prompt = Prompts.WALKTHROUGH_SUMMARY
    elif content_type == "printable":
        system_prompt = Prompts.PRINTABLE_SUMMARY
    else:
        raise ValueError(
            f"Invalid content_type: {content_type}. "
            f"Must be one of: article, video, repo, news, walkthrough, printable"
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

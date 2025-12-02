"""Content type enumeration for classifying different types of web content."""

import re
from enum import StrEnum
from urllib.parse import urlparse

from src.utils.url import extract_domain, extract_github_repo


class ContentType(StrEnum):
    """
    Enumeration of content types for web pages and documents.

    Attributes:
        ARTICLE: Long-form written content such as blog posts, essays, or articles.
        VIDEO: Video content or pages primarily containing video media.
        REPO: Software repositories, typically from platforms like GitHub or GitLab.
        NEWS: News articles or press releases with time-sensitive information.
        WALKTHROUGH: Tutorial, guide, or step-by-step instructional content.
        PRINTABLE: Content formatted or optimized for printing (PDFs, documents).
    """

    ARTICLE = "article"
    VIDEO = "video"
    REPO = "repo"
    NEWS = "news"
    WALKTHROUGH = "walkthrough"
    PRINTABLE = "printable"


def detect_content_type(url: str, content: str | None = None) -> ContentType:
    """
    Detect the content type based on URL and optionally content analysis.

    Detection is performed in the following priority order:
    1. Domain-based detection (highest priority)
    2. Content-based detection (if content is provided)
    3. Default to ARTICLE

    Args:
        url: The URL to analyze for content type detection
        content: Optional content text for additional analysis

    Returns:
        The detected ContentType

    Examples:
        >>> detect_content_type("https://youtube.com/watch?v=123")
        ContentType.VIDEO
        >>> detect_content_type("https://github.com/user/repo")
        ContentType.REPO
        >>> detect_content_type("https://example.com", "How to build a website step by step")
        ContentType.WALKTHROUGH
        >>> detect_content_type("https://example.com")
        ContentType.ARTICLE
    """
    # 1. Domain-based detection (highest priority)
    try:
        domain = extract_domain(url).lower()
        parsed_url = urlparse(url)
        path = parsed_url.path.lower()

        # Remove port if present for domain comparison
        domain_without_port = domain.split(":")[0]

        # VIDEO detection
        video_domains = {"youtube.com", "youtu.be", "vimeo.com", "www.youtube.com", "www.vimeo.com"}
        if domain_without_port in video_domains or domain_without_port.endswith((".youtube.com", ".vimeo.com")):
            return ContentType.VIDEO

        # REPO detection - check if it's a valid GitHub repository
        if "github.com" in domain_without_port:
            repo_info = extract_github_repo(url)
            if repo_info is not None:
                return ContentType.REPO

        # PRINTABLE detection
        printable_domains = {"thingiverse.com", "printables.com", "cults3d.com", "www.thingiverse.com", "www.printables.com", "www.cults3d.com"}
        if domain_without_port in printable_domains or any(domain_without_port.endswith(f".{d}") for d in printable_domains):
            return ContentType.PRINTABLE

        # NEWS detection - known news domains
        news_domains = {
            "cnn.com", "bbc.com", "reuters.com", "nytimes.com",
            "www.cnn.com", "www.bbc.com", "www.reuters.com", "www.nytimes.com",
            "apnews.com", "www.apnews.com",
            "theguardian.com", "www.theguardian.com",
            "washingtonpost.com", "www.washingtonpost.com",
            "npr.org", "www.npr.org",
            "foxnews.com", "www.foxnews.com",
            "nbcnews.com", "www.nbcnews.com",
            "abcnews.go.com",
            "bloomberg.com", "www.bloomberg.com",
            "wsj.com", "www.wsj.com",
        }

        # Check if domain is a news domain or path contains /news/
        if domain_without_port in news_domains or any(domain_without_port.endswith(f".{d}") for d in news_domains):
            return ContentType.NEWS

        if "/news/" in path:
            return ContentType.NEWS

    except ValueError:
        # If URL parsing fails, continue to content-based detection
        pass

    # 2. Content-based detection (if content provided)
    if content:
        content_lower = content.lower()

        # WALKTHROUGH detection - look for tutorial/guide keywords
        walkthrough_keywords = [
            "how to",
            "tutorial",
            "step by step",
            "step-by-step",
            "guide",
            "walkthrough",
            "instructions",
        ]

        if any(keyword in content_lower for keyword in walkthrough_keywords):
            return ContentType.WALKTHROUGH

    # 3. Default to ARTICLE
    return ContentType.ARTICLE

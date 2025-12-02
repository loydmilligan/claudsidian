"""Content extractors for different content types."""

from src.core.extractors.article import ArticleContent, ArticleExtractor
from src.core.extractors.github import GitHubContent, GitHubExtractor
from src.core.extractors.news import NewsContent, NewsExtractor
from src.core.extractors.printable import PrintableContent, PrintableExtractor, PrintSettings
from src.core.extractors.walkthrough import WalkthroughContent, WalkthroughExtractor, Step
from src.core.extractors.youtube import (
    Chapter,
    TranscriptSegment,
    YouTubeContent,
    YouTubeExtractor,
)

__all__ = [
    "ArticleExtractor",
    "ArticleContent",
    "GitHubExtractor",
    "GitHubContent",
    "NewsExtractor",
    "NewsContent",
    "PrintableExtractor",
    "PrintableContent",
    "PrintSettings",
    "WalkthroughExtractor",
    "WalkthroughContent",
    "Step",
    "YouTubeExtractor",
    "YouTubeContent",
    "Chapter",
    "TranscriptSegment",
]

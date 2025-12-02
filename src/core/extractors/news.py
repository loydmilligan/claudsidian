"""News article extractor with date and source extraction.

This module extends the base article extractor with news-specific features
like publication date extraction, source name detection, and news metadata.
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from readability import Document

from src.utils.url import extract_domain

logger = logging.getLogger(__name__)


# Known news source display names
NEWS_SOURCE_NAMES = {
    "cnn.com": "CNN",
    "bbc.com": "BBC",
    "bbc.co.uk": "BBC",
    "reuters.com": "Reuters",
    "nytimes.com": "The New York Times",
    "apnews.com": "Associated Press",
    "theguardian.com": "The Guardian",
    "washingtonpost.com": "The Washington Post",
    "npr.org": "NPR",
    "foxnews.com": "Fox News",
    "nbcnews.com": "NBC News",
    "abcnews.go.com": "ABC News",
    "bloomberg.com": "Bloomberg",
    "wsj.com": "The Wall Street Journal",
    "politico.com": "Politico",
    "thehill.com": "The Hill",
    "axios.com": "Axios",
    "vox.com": "Vox",
    "techcrunch.com": "TechCrunch",
    "theverge.com": "The Verge",
    "arstechnica.com": "Ars Technica",
    "wired.com": "Wired",
    "engadget.com": "Engadget",
    "mashable.com": "Mashable",
}


@dataclass
class NewsContent:
    """Extracted news article content.

    Attributes:
        title: Article headline
        content: Cleaned markdown-formatted content
        author: Article author if found
        publish_date: Publication date (ISO 8601 format)
        source_name: Human-readable source name (e.g., "CNN", "BBC")
        source_domain: Domain of the news source
        source_url: Original article URL
        word_count: Number of words in the content
        section: News section/category if detected (e.g., "Politics", "Tech")
        is_breaking: Whether article appears to be breaking news
        last_updated: Last update timestamp if different from publish date
    """

    title: str
    content: str
    author: Optional[str]
    publish_date: Optional[str]
    source_name: str
    source_domain: str
    source_url: str
    word_count: int
    section: Optional[str] = None
    is_breaking: bool = False
    last_updated: Optional[str] = None


class NewsExtractor:
    """Extracts content from news articles.

    Extends basic article extraction with news-specific features like
    publication date detection, source identification, and section detection.

    Example:
        >>> extractor = NewsExtractor()
        >>> news = await extractor.extract("https://cnn.com/article/...")
        >>> print(f"{news.source_name}: {news.title}")
        >>> await extractor.close()
    """

    def __init__(self) -> None:
        """Initialize the news extractor with HTTP client."""
        self._client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 Claudsidian/1.0"},
        )

    async def extract(self, url: str) -> NewsContent:
        """Extract news article content from URL.

        Args:
            url: The news article URL to extract

        Returns:
            NewsContent with extracted article data

        Raises:
            httpx.HTTPError: If the HTTP request fails
            ValueError: If URL doesn't contain valid HTML
        """
        # Fetch the URL
        response = await self._client.get(url)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "").lower()
        if "html" not in content_type:
            raise ValueError(f"URL does not contain HTML content: {content_type}")

        html = response.text

        # Use readability for main content extraction
        doc = Document(html)
        title = doc.title()
        summary_html = doc.summary()

        # Parse full HTML for metadata
        soup = BeautifulSoup(html, "html.parser")

        # Extract domain and source info
        domain = extract_domain(url)
        source_name = self._get_source_name(domain)

        # Extract metadata
        author = self._extract_author(soup)
        publish_date = self._extract_publish_date(soup)
        last_updated = self._extract_last_updated(soup)
        section = self._extract_section(soup, url)
        is_breaking = self._detect_breaking_news(soup, title)

        # Convert HTML to markdown
        content_markdown = self._html_to_markdown(summary_html)

        # Handle empty content
        if not content_markdown or not content_markdown.strip():
            content_markdown = "*No content could be extracted from this article.*"

        # Fallback title
        if not title or not title.strip():
            title = "Untitled News Article"

        word_count = len(content_markdown.split())

        logger.info(f"Extracted news: {title} from {source_name}")

        return NewsContent(
            title=title.strip(),
            content=content_markdown,
            author=author,
            publish_date=publish_date,
            source_name=source_name,
            source_domain=domain,
            source_url=url,
            word_count=word_count,
            section=section,
            is_breaking=is_breaking,
            last_updated=last_updated,
        )

    def _get_source_name(self, domain: str) -> str:
        """Get human-readable source name from domain.

        Args:
            domain: The domain name

        Returns:
            Human-readable source name or formatted domain
        """
        # Remove www. prefix
        clean_domain = domain.lower().replace("www.", "")

        # Check known sources
        if clean_domain in NEWS_SOURCE_NAMES:
            return NEWS_SOURCE_NAMES[clean_domain]

        # Format domain as title case
        return clean_domain.split(".")[0].title()

    def _extract_author(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract author from news article metadata."""
        author_selectors = [
            ('meta[name="author"]', "content"),
            ('meta[property="article:author"]', "content"),
            ('meta[name="byl"]', "content"),
            ('[rel="author"]', "text"),
            (".author-name", "text"),
            (".byline__name", "text"),
            (".article-author", "text"),
            (".story-meta__author", "text"),
        ]

        for selector, attr_type in author_selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    if attr_type == "content":
                        author = element.get("content")
                    else:
                        author = element.get_text(strip=True)

                    if author and author.strip():
                        # Clean up common prefixes
                        author = re.sub(r"^By\s+", "", author.strip(), flags=re.IGNORECASE)
                        return author
            except Exception:
                continue

        return None

    def _extract_publish_date(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract publication date from news article."""
        date_selectors = [
            ('meta[property="article:published_time"]', "content"),
            ('meta[name="publish_date"]', "content"),
            ('meta[name="date"]', "content"),
            ('meta[property="og:article:published_time"]', "content"),
            ('time[datetime]', "datetime"),
            ('time[pubdate]', "datetime"),
            ('[itemprop="datePublished"]', "content"),
        ]

        for selector, attr in date_selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    date_str = element.get(attr) or element.get("content")
                    if date_str and date_str.strip():
                        normalized = self._normalize_date(date_str.strip())
                        if normalized:
                            return normalized
            except Exception:
                continue

        return None

    def _extract_last_updated(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract last updated timestamp if different from publish date."""
        update_selectors = [
            ('meta[property="article:modified_time"]', "content"),
            ('meta[name="last-modified"]', "content"),
            ('[itemprop="dateModified"]', "content"),
        ]

        for selector, attr in update_selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    date_str = element.get(attr) or element.get("content")
                    if date_str and date_str.strip():
                        normalized = self._normalize_date(date_str.strip())
                        if normalized:
                            return normalized
            except Exception:
                continue

        return None

    def _extract_section(self, soup: BeautifulSoup, url: str) -> Optional[str]:
        """Extract news section/category."""
        # Try meta tags first
        section_selectors = [
            ('meta[property="article:section"]', "content"),
            ('meta[name="section"]', "content"),
            ('meta[property="og:article:section"]', "content"),
        ]

        for selector, attr in section_selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    section = element.get(attr)
                    if section and section.strip():
                        return section.strip().title()
            except Exception:
                continue

        # Try to extract from URL path
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split("/") if p]

        # Common section names in URL paths
        section_keywords = {
            "politics", "business", "tech", "technology", "science",
            "health", "sports", "entertainment", "world", "us", "opinion",
            "lifestyle", "culture", "travel", "food", "money", "weather"
        }

        for part in path_parts[:2]:  # Check first two path segments
            if part.lower() in section_keywords:
                return part.title()

        return None

    def _detect_breaking_news(self, soup: BeautifulSoup, title: str) -> bool:
        """Detect if article appears to be breaking news."""
        breaking_indicators = [
            "breaking:",
            "breaking news:",
            "just in:",
            "developing:",
            "urgent:",
            "live updates:",
        ]

        title_lower = title.lower()
        for indicator in breaking_indicators:
            if indicator in title_lower:
                return True

        # Check for breaking news classes/elements
        if soup.select_one(".breaking-news, .is-breaking, [data-breaking]"):
            return True

        return False

    def _normalize_date(self, date_str: str) -> Optional[str]:
        """Normalize date string to ISO 8601 format."""
        date_formats = [
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%B %d, %Y",
            "%b %d, %Y",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S.%fZ",
        ]

        for fmt in date_formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.isoformat()
            except ValueError:
                continue

        # If it looks like ISO format, return as-is
        if re.match(r"\d{4}-\d{2}-\d{2}", date_str):
            return date_str

        return None

    def _html_to_markdown(self, html: str) -> str:
        """Convert HTML to clean markdown."""
        soup = BeautifulSoup(html, "html.parser")

        # Remove unwanted elements
        for selector in ["script", "style", "nav", "aside", ".ad", ".advertisement"]:
            for element in soup.select(selector):
                element.decompose()

        # Simple conversion
        lines = []
        for element in soup.find_all(["p", "h1", "h2", "h3", "h4", "blockquote"]):
            text = element.get_text(strip=True)
            if not text:
                continue

            if element.name.startswith("h"):
                level = int(element.name[1])
                lines.append(f"{'#' * level} {text}")
            elif element.name == "blockquote":
                lines.append(f"> {text}")
            else:
                lines.append(text)
            lines.append("")

        return "\n".join(lines).strip()

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> "NewsExtractor":
        """Support async context manager."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Support async context manager."""
        await self.close()

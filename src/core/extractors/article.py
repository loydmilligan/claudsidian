"""Article content extractor using readability-lxml."""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup, Comment, NavigableString
from readability import Document

from src.utils.url import extract_domain


# Paywall detection constants
PAYWALL_KEYWORDS = [
    "subscribe to continue",
    "premium content",
    "members only",
    "sign in to read",
    "create an account to",
    "subscription required",
    "for subscribers",
    "this article is for subscribers",
    "become a member",
    "unlock this article",
    "paywall",
    "subscriber exclusive",
    "exclusive to members",
]

PAYWALL_CLASSES = [
    "paywall",
    "premium-content",
    "subscriber-only",
    "locked-content",
    "registration-wall",
    "subscription-required",
    "member-exclusive",
    "content-locked",
]


@dataclass
class ArticleContent:
    """
    Extracted article content.

    Attributes:
        title: Article title
        content: Cleaned markdown-formatted content
        author: Article author if found
        publish_date: Publication date if found (ISO 8601 format)
        word_count: Number of words in the content
        source_url: Original URL where content was extracted from
        paywall_warning: Warning message if paywall/login detected
    """

    title: str
    content: str
    author: Optional[str]
    publish_date: Optional[str]
    word_count: int
    source_url: str
    paywall_warning: Optional[str] = None


class ArticleExtractor:
    """
    Extracts article content from web pages using readability-lxml.

    This extractor fetches web pages, uses the readability algorithm to extract
    the main content, and converts it to clean markdown format. It handles common
    edge cases like missing titles, empty content, and non-HTML responses.

    Example:
        >>> extractor = ArticleExtractor()
        >>> article = await extractor.extract("https://example.com/article")
        >>> print(article.title)
        'Example Article Title'
        >>> await extractor.close()
    """

    def __init__(self) -> None:
        """Initialize the article extractor with an HTTP client."""
        self._client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 Claudsidian/1.0"},
        )

    async def extract(self, url: str) -> ArticleContent:
        """
        Extract article content from URL.

        Args:
            url: The URL to extract content from

        Returns:
            ArticleContent object with extracted data

        Raises:
            httpx.HTTPError: If the HTTP request fails
            ValueError: If the URL doesn't contain valid HTML content

        Example:
            >>> extractor = ArticleExtractor()
            >>> article = await extractor.extract("https://example.com/article")
            >>> print(f"{article.title}: {article.word_count} words")
            'Example Article: 1234 words'
        """
        # Fetch the URL
        response = await self._client.get(url)
        response.raise_for_status()

        # Check if response is HTML
        content_type = response.headers.get("content-type", "").lower()
        if "html" not in content_type:
            raise ValueError(f"URL does not contain HTML content: {content_type}")

        html = response.text

        # Use readability to extract main content
        doc = Document(html)
        title = doc.title()
        summary_html = doc.summary()

        # Fallback to domain if title is empty or just whitespace
        if not title or not title.strip():
            try:
                domain = extract_domain(url)
                title = domain
            except ValueError:
                title = "Untitled Article"

        # Extract metadata
        soup = BeautifulSoup(html, "html.parser")
        author = self._extract_author(soup)
        publish_date = self._extract_publish_date(soup)

        # Convert HTML to markdown
        content_markdown = self._html_to_markdown(summary_html)

        # Handle empty content
        if not content_markdown or not content_markdown.strip():
            content_markdown = "*No content could be extracted from this page.*"

        # Calculate word count
        word_count = len(content_markdown.split())

        # Detect paywall
        paywall_warning = self._detect_paywall(html, content_markdown)

        return ArticleContent(
            title=title.strip(),
            content=content_markdown,
            author=author,
            publish_date=publish_date,
            word_count=word_count,
            source_url=url,
            paywall_warning=paywall_warning,
        )

    def _extract_author(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Extract author from HTML metadata.

        Looks for author in common meta tags and JSON-LD structured data.

        Args:
            soup: BeautifulSoup object of the HTML

        Returns:
            Author name if found, None otherwise
        """
        # Try meta tags
        author_selectors = [
            ('meta[name="author"]', "content"),
            ('meta[property="article:author"]', "content"),
            ('meta[name="article:author"]', "content"),
            ('meta[property="og:article:author"]', "content"),
            ('meta[name="byl"]', "content"),  # New York Times
            (".author", "text"),
            (".byline", "text"),
            ('[rel="author"]', "text"),
        ]

        for selector, attr_type in author_selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    if attr_type == "content":
                        author = element.get("content")
                    else:  # text
                        author = element.get_text(strip=True)

                    if author and author.strip():
                        # Clean up "By " prefix if present
                        author = re.sub(r"^By\s+", "", author.strip(), flags=re.IGNORECASE)
                        return author
            except Exception:
                continue

        return None

    def _extract_publish_date(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Extract publication date from HTML metadata.

        Looks for dates in common meta tags and attempts to parse them to ISO 8601 format.

        Args:
            soup: BeautifulSoup object of the HTML

        Returns:
            ISO 8601 formatted date string if found, None otherwise
        """
        date_selectors = [
            ('meta[property="article:published_time"]', "content"),
            ('meta[name="article:published_time"]', "content"),
            ('meta[property="og:published_time"]', "content"),
            ('meta[name="publish_date"]', "content"),
            ('meta[name="date"]', "content"),
            ('meta[property="article:published"]', "content"),
            ('time[datetime]', "datetime"),
            ('time[pubdate]', "datetime"),
        ]

        for selector, attr in date_selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    date_str = element.get(attr)
                    if date_str and date_str.strip():
                        # Try to parse and normalize to ISO 8601
                        normalized_date = self._normalize_date(date_str.strip())
                        if normalized_date:
                            return normalized_date
            except Exception:
                continue

        return None

    def _normalize_date(self, date_str: str) -> Optional[str]:
        """
        Normalize various date formats to ISO 8601.

        Args:
            date_str: Date string to normalize

        Returns:
            ISO 8601 formatted date string if parsing succeeds, None otherwise
        """
        # Try common date formats
        date_formats = [
            "%Y-%m-%dT%H:%M:%S%z",  # ISO 8601 with timezone
            "%Y-%m-%dT%H:%M:%S",  # ISO 8601 without timezone
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%B %d, %Y",  # January 1, 2024
            "%b %d, %Y",  # Jan 1, 2024
            "%Y-%m-%dT%H:%M:%S.%f%z",  # ISO 8601 with microseconds
            "%Y-%m-%dT%H:%M:%S.%fZ",  # ISO 8601 with microseconds and Z
        ]

        for fmt in date_formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.isoformat()
            except ValueError:
                continue

        # If no format matches, return the original if it looks like a date
        if re.match(r"\d{4}-\d{2}-\d{2}", date_str):
            return date_str

        return None

    def _detect_paywall(self, html: str, content: str) -> Optional[str]:
        """
        Detect if content is behind a paywall or login wall.

        This method checks multiple indicators that might suggest the content
        is restricted:
        - Short content with truncation indicators
        - Presence of login forms (password fields)
        - Paywall-related keywords in the HTML
        - CSS classes commonly used for paywalled content
        - Meta tags indicating restricted content

        Args:
            html: Raw HTML content of the page
            content: Extracted markdown content

        Returns:
            Warning message if paywall detected, None otherwise

        Example:
            >>> html = '<html><div class="paywall">Subscribe to read</div></html>'
            >>> content = "Short article..."
            >>> warning = extractor._detect_paywall(html, content)
            >>> print(warning)
            'Paywall class detected: paywall'
        """
        warnings = []

        # Check content length and truncation indicators
        word_count = len(content.split())
        if word_count < 200:
            # Check for truncation indicators in the last portion of content
            content_lower = content.lower()
            last_part = content[-100:] if len(content) > 100 else content

            truncation_indicators = ["...", "read more", "continue reading", "see more"]
            for indicator in truncation_indicators:
                if indicator in last_part.lower():
                    warnings.append("Content appears truncated (possible paywall)")
                    break

        # Parse HTML for more detailed checks
        soup = BeautifulSoup(html, "html.parser")

        # Check for login forms (password input fields)
        if soup.find("input", {"type": "password"}):
            warnings.append("Login form detected")

        # Check for paywall keywords in HTML
        html_lower = html.lower()
        for keyword in PAYWALL_KEYWORDS:
            if keyword in html_lower:
                warnings.append(f"Paywall indicator: '{keyword}'")
                break  # Only report first match to avoid duplicate warnings

        # Check for paywall CSS classes
        for cls in PAYWALL_CLASSES:
            if soup.find(class_=re.compile(cls, re.I)):
                warnings.append(f"Paywall class detected: {cls}")
                break  # Only report first match

        # Check for restricted content meta tags
        meta_selectors = [
            ('meta[name="robots"]', "content", "noindex"),
            ('meta[property="article:content_tier"]', "content", "locked"),
            ('meta[property="article:content_tier"]', "content", "metered"),
            ('meta[name="content-gating"]', "content", None),
        ]

        for selector, attr, value_check in meta_selectors:
            meta = soup.select_one(selector)
            if meta:
                content_value = meta.get(attr, "").lower()
                if value_check:
                    if value_check in content_value:
                        warnings.append(f"Restricted content meta tag: {attr}={value_check}")
                        break
                else:
                    warnings.append("Content gating meta tag detected")
                    break

        # Return combined warning message or None
        return "; ".join(warnings) if warnings else None

    def _html_to_markdown(self, html: str) -> str:
        """
        Convert HTML content to clean markdown.

        This method parses HTML and converts common elements to markdown syntax:
        - Headings (h1-h6) to # markdown
        - Paragraphs to text with double newlines
        - Lists (ul/ol) to markdown lists
        - Links to [text](url) format
        - Code blocks to ``` syntax
        - Bold/italic to markdown syntax

        Strips out unwanted elements like ads, navigation, comments.

        Args:
            html: HTML content to convert

        Returns:
            Clean markdown-formatted text
        """
        soup = BeautifulSoup(html, "html.parser")

        # Remove unwanted elements
        unwanted_selectors = [
            "script",
            "style",
            "nav",
            "footer",
            "header",
            "aside",
            ".advertisement",
            ".ad",
            ".ads",
            ".social-share",
            ".related-articles",
            ".comments",
            ".comment",
            '[role="complementary"]',
            '[aria-label*="advertisement"]',
        ]

        for selector in unwanted_selectors:
            for element in soup.select(selector):
                element.decompose()

        # Remove HTML comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        # Convert to markdown
        markdown_lines = []
        self._process_element(soup, markdown_lines, 0)

        # Join lines and clean up
        markdown = "\n".join(markdown_lines)

        # Clean up excessive whitespace
        markdown = re.sub(r"\n{3,}", "\n\n", markdown)  # Max 2 consecutive newlines
        markdown = re.sub(r" +", " ", markdown)  # Multiple spaces to single space
        markdown = markdown.strip()

        return markdown

    def _process_element(
        self, element, markdown_lines: list[str], list_depth: int = 0
    ) -> None:
        """
        Recursively process HTML element and convert to markdown.

        Args:
            element: BeautifulSoup element to process
            markdown_lines: List to append markdown lines to
            list_depth: Current depth of nested lists (for indentation)
        """
        if isinstance(element, NavigableString):
            text = str(element).strip()
            if text and element.parent.name not in ["script", "style"]:
                markdown_lines.append(text)
            return

        tag_name = element.name

        # Handle different HTML elements
        if tag_name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            level = int(tag_name[1])
            text = element.get_text(strip=True)
            if text:
                markdown_lines.append(f"{'#' * level} {text}")
                markdown_lines.append("")

        elif tag_name == "p":
            text = self._get_inline_text(element)
            if text:
                markdown_lines.append(text)
                markdown_lines.append("")

        elif tag_name == "br":
            markdown_lines.append("")

        elif tag_name == "hr":
            markdown_lines.append("---")
            markdown_lines.append("")

        elif tag_name in ["ul", "ol"]:
            for i, li in enumerate(element.find_all("li", recursive=False)):
                indent = "  " * list_depth
                bullet = f"{i + 1}." if tag_name == "ol" else "-"
                text = self._get_inline_text(li)
                if text:
                    markdown_lines.append(f"{indent}{bullet} {text}")

                # Handle nested lists
                for nested_list in li.find_all(["ul", "ol"], recursive=False):
                    self._process_element(nested_list, markdown_lines, list_depth + 1)

            markdown_lines.append("")

        elif tag_name == "blockquote":
            for child in element.children:
                if isinstance(child, NavigableString):
                    text = str(child).strip()
                    if text:
                        markdown_lines.append(f"> {text}")
                else:
                    text = child.get_text(strip=True)
                    if text:
                        markdown_lines.append(f"> {text}")
            markdown_lines.append("")

        elif tag_name == "pre":
            code = element.get_text()
            markdown_lines.append("```")
            markdown_lines.append(code.strip())
            markdown_lines.append("```")
            markdown_lines.append("")

        elif tag_name == "code" and element.parent.name != "pre":
            # Inline code
            text = element.get_text(strip=True)
            if text:
                markdown_lines.append(f"`{text}`")

        elif tag_name == "a":
            text = element.get_text(strip=True)
            href = element.get("href", "")
            if text and href:
                markdown_lines.append(f"[{text}]({href})")
            elif text:
                markdown_lines.append(text)

        elif tag_name in ["strong", "b"]:
            text = element.get_text(strip=True)
            if text:
                markdown_lines.append(f"**{text}**")

        elif tag_name in ["em", "i"]:
            text = element.get_text(strip=True)
            if text:
                markdown_lines.append(f"*{text}*")

        elif tag_name == "img":
            alt = element.get("alt", "")
            src = element.get("src", "")
            if src:
                markdown_lines.append(f"![{alt}]({src})")
                markdown_lines.append("")

        elif tag_name in ["div", "section", "article", "main"]:
            # Process children recursively
            for child in element.children:
                self._process_element(child, markdown_lines, list_depth)

        else:
            # For other elements, just process children
            for child in element.children:
                self._process_element(child, markdown_lines, list_depth)

    def _get_inline_text(self, element) -> str:
        """
        Extract text from element preserving inline markdown formatting.

        Args:
            element: BeautifulSoup element

        Returns:
            Text with inline markdown formatting
        """
        parts = []

        for child in element.descendants:
            if isinstance(child, NavigableString):
                text = str(child).strip()
                if text:
                    # Check parent for formatting
                    parent = child.parent
                    if parent.name in ["strong", "b"]:
                        parts.append(f"**{text}**")
                    elif parent.name in ["em", "i"]:
                        parts.append(f"*{text}*")
                    elif parent.name == "code":
                        parts.append(f"`{text}`")
                    elif parent.name == "a":
                        href = parent.get("href", "")
                        if href:
                            parts.append(f"[{text}]({href})")
                        else:
                            parts.append(text)
                    else:
                        parts.append(text)

        return " ".join(parts)

    async def close(self) -> None:
        """
        Close the HTTP client.

        Should be called when done using the extractor to properly clean up resources.

        Example:
            >>> extractor = ArticleExtractor()
            >>> try:
            ...     article = await extractor.extract("https://example.com")
            ... finally:
            ...     await extractor.close()
        """
        await self._client.aclose()

    async def __aenter__(self):
        """Support async context manager protocol."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Support async context manager protocol."""
        await self.close()

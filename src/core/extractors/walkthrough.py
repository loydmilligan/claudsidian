"""Walkthrough/Tutorial extractor with step and structure detection.

This module extracts tutorial content with special handling for:
- Numbered steps and procedures
- Prerequisites and requirements
- Code blocks and commands
- Warnings and gotchas
- Estimated time and difficulty
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

import httpx
from bs4 import BeautifulSoup
from readability import Document

from src.utils.url import extract_domain

logger = logging.getLogger(__name__)


@dataclass
class Step:
    """A single step in a walkthrough."""

    number: int
    title: str
    content: str
    has_code: bool = False
    has_warning: bool = False


@dataclass
class WalkthroughContent:
    """Extracted walkthrough/tutorial content.

    Attributes:
        title: Tutorial title
        content: Full markdown content
        steps: Extracted numbered steps
        prerequisites: List of prerequisites/requirements
        warnings: List of warnings/gotchas found
        code_blocks: Number of code blocks found
        estimated_time: Estimated completion time if found
        difficulty: Difficulty level if detected
        source_url: Original URL
        word_count: Number of words
        author: Author if found
        has_steps: Whether structured steps were detected
    """

    title: str
    content: str
    steps: list[Step] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    code_blocks: int = 0
    estimated_time: Optional[str] = None
    difficulty: Optional[str] = None
    source_url: str = ""
    word_count: int = 0
    author: Optional[str] = None
    has_steps: bool = False


class WalkthroughExtractor:
    """Extracts content from tutorial and walkthrough pages.

    Specialized extractor that identifies tutorial structure including
    numbered steps, prerequisites, code examples, and warnings.

    Example:
        >>> extractor = WalkthroughExtractor()
        >>> tutorial = await extractor.extract("https://example.com/how-to-...")
        >>> print(f"Found {len(tutorial.steps)} steps")
        >>> await extractor.close()
    """

    def __init__(self) -> None:
        """Initialize the walkthrough extractor."""
        self._client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 Claudsidian/1.0"},
        )

    async def extract(self, url: str) -> WalkthroughContent:
        """Extract walkthrough content from URL.

        Args:
            url: The tutorial/walkthrough URL

        Returns:
            WalkthroughContent with extracted structure

        Raises:
            httpx.HTTPError: If request fails
            ValueError: If content is not HTML
        """
        response = await self._client.get(url)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "").lower()
        if "html" not in content_type:
            raise ValueError(f"URL does not contain HTML: {content_type}")

        html = response.text

        # Extract main content
        doc = Document(html)
        title = doc.title()
        summary_html = doc.summary()

        # Parse for metadata
        soup = BeautifulSoup(html, "html.parser")
        full_soup = BeautifulSoup(summary_html, "html.parser")

        # Extract metadata
        author = self._extract_author(soup)
        estimated_time = self._extract_time_estimate(soup, html)
        difficulty = self._extract_difficulty(soup, html)

        # Convert to markdown
        content_markdown = self._html_to_markdown(summary_html)

        # Extract structured elements
        steps = self._extract_steps(full_soup, content_markdown)
        prerequisites = self._extract_prerequisites(full_soup, content_markdown)
        warnings = self._extract_warnings(full_soup, content_markdown)
        code_blocks = self._count_code_blocks(full_soup)

        # Fallback title
        if not title or not title.strip():
            title = "Untitled Tutorial"

        word_count = len(content_markdown.split())

        logger.info(f"Extracted walkthrough: {title} ({len(steps)} steps)")

        return WalkthroughContent(
            title=title.strip(),
            content=content_markdown,
            steps=steps,
            prerequisites=prerequisites,
            warnings=warnings,
            code_blocks=code_blocks,
            estimated_time=estimated_time,
            difficulty=difficulty,
            source_url=url,
            word_count=word_count,
            author=author,
            has_steps=len(steps) > 0,
        )

    def _extract_author(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract author from tutorial."""
        selectors = [
            ('meta[name="author"]', "content"),
            (".author", "text"),
            (".byline", "text"),
            ('[rel="author"]', "text"),
        ]

        for selector, attr_type in selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    if attr_type == "content":
                        author = element.get("content")
                    else:
                        author = element.get_text(strip=True)
                    if author:
                        return re.sub(r"^By\s+", "", author, flags=re.IGNORECASE).strip()
            except Exception:
                continue
        return None

    def _extract_time_estimate(self, soup: BeautifulSoup, html: str) -> Optional[str]:
        """Extract estimated completion time."""
        # Look for common time patterns
        time_patterns = [
            r"(\d+)\s*(?:min(?:ute)?s?|mins?)",
            r"(\d+)\s*(?:hour)s?",
            r"time[:\s]+(\d+\s*(?:min|hour|minute)s?)",
            r"duration[:\s]+(\d+\s*(?:min|hour|minute)s?)",
            r"estimated[:\s]+(\d+\s*(?:min|hour|minute)s?)",
        ]

        html_lower = html.lower()
        for pattern in time_patterns:
            match = re.search(pattern, html_lower)
            if match:
                return match.group(0).strip()

        # Check meta tags
        meta = soup.select_one('meta[name="duration"], meta[property="article:read_time"]')
        if meta and meta.get("content"):
            return meta["content"]

        return None

    def _extract_difficulty(self, soup: BeautifulSoup, html: str) -> Optional[str]:
        """Extract difficulty level."""
        difficulty_keywords = {
            "beginner": ["beginner", "easy", "basic", "introduction", "getting started"],
            "intermediate": ["intermediate", "medium", "moderate"],
            "advanced": ["advanced", "expert", "complex", "in-depth"],
        }

        html_lower = html.lower()

        for level, keywords in difficulty_keywords.items():
            for keyword in keywords:
                # Look for difficulty indicators
                patterns = [
                    f"difficulty[:\\s]+{keyword}",
                    f"level[:\\s]+{keyword}",
                    f"{keyword}\\s+(?:tutorial|guide|walkthrough)",
                ]
                for pattern in patterns:
                    if re.search(pattern, html_lower):
                        return level.title()

        return None

    def _extract_steps(self, soup: BeautifulSoup, content: str) -> list[Step]:
        """Extract numbered steps from content."""
        steps = []

        # Pattern 1: Look for ordered lists
        for ol in soup.find_all("ol"):
            for i, li in enumerate(ol.find_all("li", recursive=False), 1):
                text = li.get_text(strip=True)
                if text and len(text) > 10:  # Skip very short items
                    has_code = bool(li.find("code") or li.find("pre"))
                    has_warning = bool(
                        li.find(class_=re.compile(r"warn|caution|note", re.I))
                        or "warning" in text.lower()
                        or "caution" in text.lower()
                    )
                    steps.append(Step(
                        number=i,
                        title=text[:100] + "..." if len(text) > 100 else text,
                        content=text,
                        has_code=has_code,
                        has_warning=has_warning,
                    ))

        # Pattern 2: Look for "Step N:" patterns in text
        if not steps:
            step_pattern = r"(?:step\s+)?(\d+)[.):]\s*(.+?)(?=(?:step\s+)?\d+[.):]\s|$)"
            matches = re.findall(step_pattern, content.lower(), re.IGNORECASE | re.DOTALL)
            for num, text in matches[:20]:  # Limit to 20 steps
                text = text.strip()
                if len(text) > 10:
                    steps.append(Step(
                        number=int(num),
                        title=text[:100] + "..." if len(text) > 100 else text,
                        content=text,
                        has_code="```" in text or "`" in text,
                        has_warning="warning" in text.lower() or "caution" in text.lower(),
                    ))

        # Pattern 3: Look for h2/h3 headings with numbers
        if not steps:
            for i, heading in enumerate(soup.find_all(["h2", "h3"]), 1):
                text = heading.get_text(strip=True)
                if re.match(r"^\d+[.)]?\s", text) or re.match(r"^step\s+\d+", text.lower()):
                    steps.append(Step(
                        number=i,
                        title=text,
                        content=text,
                        has_code=False,
                        has_warning=False,
                    ))

        return steps

    def _extract_prerequisites(self, soup: BeautifulSoup, content: str) -> list[str]:
        """Extract prerequisites/requirements."""
        prerequisites = []

        # Look for prerequisite sections
        prereq_keywords = ["prerequisite", "requirement", "before you begin", "what you need", "you will need"]

        content_lower = content.lower()
        for keyword in prereq_keywords:
            if keyword in content_lower:
                # Find the section and extract list items
                idx = content_lower.find(keyword)
                section = content[idx:idx + 500]  # Look at next 500 chars

                # Extract bullet points
                bullets = re.findall(r"[-*]\s+(.+?)(?=[-*]|\n\n|$)", section)
                prerequisites.extend([b.strip() for b in bullets if b.strip()])

        # Look for elements with prerequisite classes
        for element in soup.find_all(class_=re.compile(r"prereq|requirement", re.I)):
            for li in element.find_all("li"):
                text = li.get_text(strip=True)
                if text and text not in prerequisites:
                    prerequisites.append(text)

        return prerequisites[:10]  # Limit to 10

    def _extract_warnings(self, soup: BeautifulSoup, content: str) -> list[str]:
        """Extract warnings and gotchas."""
        warnings = []

        # Look for warning elements
        warning_selectors = [
            ".warning", ".caution", ".note", ".alert",
            '[role="alert"]', ".admonition-warning", ".callout-warning"
        ]

        for selector in warning_selectors:
            for element in soup.select(selector):
                text = element.get_text(strip=True)
                if text and len(text) > 10:
                    warnings.append(text[:200] + "..." if len(text) > 200 else text)

        # Look for warning patterns in text
        warning_patterns = [
            r"(?:warning|caution|note|important)[:\s]+(.+?)(?=\n\n|$)",
            r"(?:⚠️|⚠|⛔|❗)\s*(.+?)(?=\n|$)",
        ]

        for pattern in warning_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                text = match.strip()
                if text and text not in warnings:
                    warnings.append(text[:200] + "..." if len(text) > 200 else text)

        return warnings[:10]  # Limit to 10

    def _count_code_blocks(self, soup: BeautifulSoup) -> int:
        """Count code blocks in content."""
        pre_count = len(soup.find_all("pre"))
        code_count = len(soup.find_all("code"))
        # Subtract inline code from pre blocks
        return max(pre_count, code_count - pre_count)

    def _html_to_markdown(self, html: str) -> str:
        """Convert HTML to markdown."""
        soup = BeautifulSoup(html, "html.parser")

        # Remove unwanted elements
        for selector in ["script", "style", "nav", "aside", ".ad"]:
            for element in soup.select(selector):
                element.decompose()

        lines = []
        for element in soup.find_all(["p", "h1", "h2", "h3", "h4", "pre", "ol", "ul", "blockquote"]):
            if element.name.startswith("h"):
                level = int(element.name[1])
                text = element.get_text(strip=True)
                if text:
                    lines.append(f"{'#' * level} {text}")
            elif element.name == "pre":
                code = element.get_text()
                lines.append("```")
                lines.append(code.strip())
                lines.append("```")
            elif element.name == "ol":
                for i, li in enumerate(element.find_all("li", recursive=False), 1):
                    lines.append(f"{i}. {li.get_text(strip=True)}")
            elif element.name == "ul":
                for li in element.find_all("li", recursive=False):
                    lines.append(f"- {li.get_text(strip=True)}")
            elif element.name == "blockquote":
                text = element.get_text(strip=True)
                if text:
                    lines.append(f"> {text}")
            else:
                text = element.get_text(strip=True)
                if text:
                    lines.append(text)
            lines.append("")

        return "\n".join(lines).strip()

    async def close(self) -> None:
        """Close HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> "WalkthroughExtractor":
        """Support async context manager."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Support async context manager."""
        await self.close()

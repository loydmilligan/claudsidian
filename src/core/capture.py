"""Capture orchestration - main entry point for URL capture.

This module implements the complete capture flow:
1. Check for duplicates (T031)
2. Fetch URL content with HTTP error handling (T031b)
3. Detect content type
4. Extract content using appropriate extractor
5. Generate summary and tags via AI
6. Find backlinks
7. Write note to vault
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import httpx

from src.models.capture import CaptureRequest
from src.models.config import Configuration
from src.models.note import Note, Frontmatter
from src.models.queue import QueueItem, QueueStatus
from src.core.content_type import ContentType, detect_content_type
from src.core.extractors.article import ArticleExtractor, ArticleContent
from src.core.ai.router import AIRouter, AIRouterError
from src.core.ai.prompts import get_summarization_prompt, get_tag_generation_prompt
from src.core.vault.writer import VaultWriter
from src.core.vault.backlinks import BacklinkFinder
from src.core.queue import CaptureQueue
from src.utils.url import normalize_url

logger = logging.getLogger(__name__)


# HTTP status codes that are unrecoverable and should not be retried
UNRECOVERABLE_HTTP_ERRORS = {404, 410, 451}  # Not Found, Gone, Unavailable For Legal Reasons

# HTTP status codes that indicate temporary errors and should be queued for retry
RETRY_HTTP_ERRORS = {403, 429, 500, 502, 503, 504}  # Forbidden, Rate Limit, Server Errors

# Maximum number of retry attempts
MAX_RETRY_ATTEMPTS = 3


@dataclass
class CaptureResult:
    """Result of a capture operation.

    Attributes:
        success: Whether the capture was successful
        note_path: Path to the created note (relative to vault root)
        title: Title of the captured note
        tags: Generated tags for the note
        content_type: Detected content type
        error: Error message if capture failed
        is_duplicate: Whether URL was already captured
        existing_note: Path to existing note if duplicate
        queued: Whether the request was queued for retry
        queue_id: ID of the queue item if queued
    """

    success: bool
    note_path: str | None = None
    title: str | None = None
    tags: list[str] = field(default_factory=list)
    content_type: str | None = None
    error: str | None = None
    is_duplicate: bool = False
    existing_note: str | None = None
    queued: bool = False
    queue_id: str | None = None


class CaptureService:
    """Orchestrates URL capture and note creation.

    This service coordinates all the components needed to capture a URL and
    create a note in the Obsidian vault. It handles:
    - Duplicate detection
    - HTTP error handling and retry logic
    - Content extraction
    - AI processing (summary and tags)
    - Backlink discovery
    - Note writing

    Attributes:
        _config: Configuration object containing settings
        _writer: VaultWriter for saving notes
        _backlinks: BacklinkFinder for discovering related notes
        _ai_router: AIRouter for AI processing
        _queue: CaptureQueue for managing retries
        _extractor: ArticleExtractor for content extraction
    """

    def __init__(self, config: Configuration) -> None:
        """Initialize the capture service.

        Args:
            config: Configuration object containing vault path, API keys, etc.
        """
        self._config = config
        self._writer = VaultWriter(config)
        self._backlinks = BacklinkFinder(config.vault_path)
        self._ai_router = AIRouter(config)

        # Initialize queue with path in vault root
        queue_path = Path(config.vault_path) / ".claudsidian" / "queue.json"
        self._queue = CaptureQueue(queue_path)

        # Extractor will be created per-request to avoid connection issues
        self._extractor: ArticleExtractor | None = None

        logger.info("Initialized CaptureService")

    async def capture(self, request: CaptureRequest) -> CaptureResult:
        """Capture a URL and create a note in the vault.

        This is the main entry point for the capture flow. It orchestrates
        all the steps needed to capture a URL and create a note.

        Flow:
        1. Check for duplicates
        2. Fetch URL content
        3. Detect content type
        4. Extract content using appropriate extractor
        5. Generate summary and tags via AI
        6. Find backlinks
        7. Write note to vault
        8. Return result

        Args:
            request: CaptureRequest containing URL and metadata

        Returns:
            CaptureResult with success status and note information or error details

        Example:
            >>> service = CaptureService(config)
            >>> request = CaptureRequest(
            ...     url="https://example.com/article",
            ...     source=CaptureSource.BROWSER,
            ...     timestamp=datetime.now()
            ... )
            >>> result = await service.capture(request)
            >>> if result.success:
            ...     print(f"Note created at: {result.note_path}")
            ... else:
            ...     print(f"Error: {result.error}")
        """
        url = str(request.url)
        logger.info(f"Starting capture for URL: {url}")

        try:
            # Normalize URL for duplicate checking
            normalized_url = normalize_url(url)

            # Step 1: Check for duplicates (T031)
            existing_note = self._check_duplicate(normalized_url)
            if existing_note:
                logger.info(f"Duplicate URL found: {existing_note}")
                return CaptureResult(
                    success=False,
                    is_duplicate=True,
                    existing_note=existing_note,
                    error=f"URL already captured in note: {existing_note}"
                )

            # Step 2: Fetch and extract content (T031b - HTTP error handling)
            try:
                article = await self._fetch_content(url)
            except httpx.HTTPStatusError as e:
                return await self._handle_http_error(e, request)
            except httpx.HTTPError as e:
                # Network errors (timeout, connection error, etc.)
                logger.error(f"Network error fetching URL: {e}")
                return await self._queue_for_retry(
                    request,
                    f"Network error: {str(e)}"
                )

            # Step 3: Detect content type
            content_type = self._detect_content_type(request, url, article.content)
            logger.info(f"Detected content type: {content_type}")

            # Step 4: Extract content (already done in fetch_content for articles)
            # For other types (video, repo), we'd use different extractors here

            # Step 5: Generate summary and tags via AI
            try:
                summary = await self._generate_summary(article.content, content_type.value)
                tags = await self._generate_tags(article.content, article.title)
            except AIRouterError as e:
                # AI errors should trigger retry (could be temporary API issues)
                logger.error(f"AI processing error: {e}")
                return await self._queue_for_retry(
                    request,
                    f"AI processing error: {str(e)}"
                )

            # Step 6: Find backlinks
            related_notes = self._backlinks.find_related(tags, min_shared=2)
            backlinks_section = self._backlinks.format_backlinks(related_notes)

            # Step 7: Combine content with metadata
            full_content = self._format_note_content(
                article,
                summary,
                backlinks_section
            )

            # Step 8: Create note object
            frontmatter = Frontmatter(
                source=request.url,
                captured=request.timestamp,
                type=content_type,
                tags=tags,
                summary=summary
            )

            # Get target folder based on content type
            target_folder = self._get_folder_for_type(content_type)

            note = Note(
                title=article.title,
                content=full_content,
                frontmatter=frontmatter,
                file_path=f"{target_folder}/{article.title}.md"  # Will be sanitized by writer
            )

            # Step 9: Write note to vault
            note_path = self._writer.write_note(note, subfolder=target_folder)
            relative_path = str(note_path.relative_to(Path(self._config.vault_path)))

            logger.info(f"Successfully created note at: {relative_path}")

            return CaptureResult(
                success=True,
                note_path=relative_path,
                title=article.title,
                tags=tags,
                content_type=content_type.value
            )

        except Exception as e:
            # Catch-all for unexpected errors
            logger.exception(f"Unexpected error during capture: {e}")
            return CaptureResult(
                success=False,
                error=f"Unexpected error: {str(e)}"
            )

    def _check_duplicate(self, url: str) -> str | None:
        """Check if URL already captured (T031).

        Searches the vault for notes with matching source URL in frontmatter.

        Args:
            url: The normalized URL to check

        Returns:
            Path to existing note if duplicate found, None otherwise
        """
        vault_path = Path(self._config.vault_path)

        # Search all markdown files in vault
        for md_file in vault_path.rglob("*.md"):
            try:
                content = md_file.read_text(encoding='utf-8')

                # Quick check before parsing
                if url not in content and "source:" not in content:
                    continue

                # Parse frontmatter
                frontmatter = self._backlinks._parse_frontmatter(content)
                if not frontmatter:
                    continue

                # Check if source URL matches
                source = frontmatter.get('source', '')
                if source:
                    # Normalize both URLs for comparison
                    try:
                        source_normalized = normalize_url(str(source))
                        if source_normalized == url:
                            relative_path = str(md_file.relative_to(vault_path))
                            logger.info(f"Found duplicate: {relative_path}")
                            return relative_path
                    except ValueError:
                        # Skip if URL normalization fails
                        continue

            except (OSError, UnicodeDecodeError):
                # Skip files that can't be read
                continue

        return None

    async def _fetch_content(self, url: str) -> ArticleContent:
        """Fetch and extract content from URL.

        Args:
            url: The URL to fetch

        Returns:
            ArticleContent with extracted data

        Raises:
            httpx.HTTPStatusError: For HTTP errors (404, 500, etc.)
            httpx.HTTPError: For network errors
        """
        # Create extractor for this request
        async with ArticleExtractor() as extractor:
            article = await extractor.extract(url)
            logger.info(
                f"Extracted article: {article.title} "
                f"({article.word_count} words)"
            )
            return article

    async def _handle_http_error(
        self,
        error: httpx.HTTPStatusError,
        request: CaptureRequest
    ) -> CaptureResult:
        """Handle HTTP errors with retry logic (T031b).

        Args:
            error: The HTTP status error
            request: The original capture request

        Returns:
            CaptureResult with error information or queue status
        """
        status_code = error.response.status_code
        url = str(request.url)

        logger.warning(f"HTTP {status_code} error for URL: {url}")

        # Handle redirects (should be automatic with httpx follow_redirects=True)
        if 300 <= status_code < 400:
            logger.info(f"Redirect encountered: {status_code}")
            # Should not reach here due to follow_redirects=True
            return CaptureResult(
                success=False,
                error=f"Redirect error: HTTP {status_code}"
            )

        # Unrecoverable errors - don't retry
        if status_code in UNRECOVERABLE_HTTP_ERRORS:
            error_msg = f"Unrecoverable HTTP {status_code} error"
            logger.error(f"{error_msg} for URL: {url}")
            return CaptureResult(
                success=False,
                error=error_msg
            )

        # Retry-able errors - queue for retry
        if status_code in RETRY_HTTP_ERRORS:
            return await self._queue_for_retry(
                request,
                f"HTTP {status_code} error (will retry)"
            )

        # Other HTTP errors - treat as unrecoverable
        error_msg = f"HTTP {status_code} error"
        logger.error(f"{error_msg} for URL: {url}")
        return CaptureResult(
            success=False,
            error=error_msg
        )

    async def _queue_for_retry(
        self,
        request: CaptureRequest,
        error_message: str
    ) -> CaptureResult:
        """Queue a failed request for retry.

        Args:
            request: The capture request to queue
            error_message: Error message describing the failure

        Returns:
            CaptureResult indicating the request was queued
        """
        queue_item = QueueItem(
            request=request,
            status=QueueStatus.FAILED,
            attempts=0,
            error=error_message
        )

        self._queue.add(queue_item)
        queue_id = str(queue_item.id)

        logger.info(f"Queued request for retry: {queue_id}")

        return CaptureResult(
            success=False,
            error=error_message,
            queued=True,
            queue_id=queue_id
        )

    def _detect_content_type(
        self,
        request: CaptureRequest,
        url: str,
        content: str
    ) -> ContentType:
        """Detect content type with force_type override support.

        Args:
            request: The capture request (may contain force_type)
            url: The URL being captured
            content: The extracted content

        Returns:
            Detected or forced ContentType
        """
        # Check if user forced a specific type
        if request.force_type:
            forced_type = ContentType(request.force_type.value)
            logger.info(f"Using forced content type: {forced_type}")
            return forced_type

        # Auto-detect
        return detect_content_type(url, content)

    async def _generate_summary(self, content: str, content_type: str) -> str:
        """Generate AI summary of content.

        Args:
            content: The content to summarize
            content_type: Type of content (article, video, repo, etc.)

        Returns:
            Generated summary text

        Raises:
            AIRouterError: If AI processing fails
        """
        logger.info(f"Generating summary for {content_type} content")

        # Truncate very long content to avoid token limits
        max_chars = 50000  # Approximately 12-15k tokens
        truncated_content = content[:max_chars]
        if len(content) > max_chars:
            logger.info(f"Truncated content from {len(content)} to {max_chars} chars")

        system_prompt, user_prompt = get_summarization_prompt(
            truncated_content,
            content_type
        )

        summary = await self._ai_router.route_request(
            task_type="summarize_long",
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.7
        )

        return summary.strip()

    async def _generate_tags(self, content: str, title: str) -> list[str]:
        """Generate AI tags for content.

        Args:
            content: The content to analyze
            title: Title of the content

        Returns:
            List of generated tags

        Raises:
            AIRouterError: If AI processing fails
        """
        logger.info("Generating tags")

        # Truncate content for tag generation (tags don't need full context)
        max_chars = 10000
        truncated_content = content[:max_chars]

        system_prompt, user_prompt = get_tag_generation_prompt(
            truncated_content,
            title
        )

        tags_csv = await self._ai_router.route_request(
            task_type="tagging",
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.5
        )

        # Parse comma-separated tags
        tags = [tag.strip() for tag in tags_csv.split(',') if tag.strip()]

        logger.info(f"Generated {len(tags)} tags: {', '.join(tags[:5])}...")

        return tags

    def _format_note_content(
        self,
        article: ArticleContent,
        summary: str,
        backlinks_section: str
    ) -> str:
        """Format the final note content.

        Combines the article content with AI-generated summary, metadata,
        and related notes backlinks.

        Args:
            article: Extracted article content
            summary: AI-generated summary
            backlinks_section: Formatted backlinks section

        Returns:
            Complete formatted markdown content
        """
        sections = []

        # Title
        sections.append(f"# {article.title}")
        sections.append("")

        # Summary section
        sections.append("## Summary")
        sections.append("")
        sections.append(summary)
        sections.append("")

        # Metadata section
        metadata_parts = []
        if article.author:
            metadata_parts.append(f"**Author:** {article.author}")
        if article.publish_date:
            metadata_parts.append(f"**Published:** {article.publish_date}")
        metadata_parts.append(f"**Word Count:** {article.word_count:,}")
        metadata_parts.append(f"**Source:** {article.source_url}")

        if metadata_parts:
            sections.append("## Metadata")
            sections.append("")
            sections.extend(metadata_parts)
            sections.append("")

        # Paywall warning if detected
        if article.paywall_warning:
            sections.append("> **⚠️ Warning:** " + article.paywall_warning)
            sections.append("")

        # Main content
        sections.append("## Content")
        sections.append("")
        sections.append(article.content)
        sections.append("")

        # Backlinks section
        if backlinks_section:
            sections.append("")
            sections.append(backlinks_section)

        return "\n".join(sections)

    def _get_folder_for_type(self, content_type: ContentType) -> str:
        """Get the target folder for a content type.

        Args:
            content_type: The content type

        Returns:
            Folder path relative to vault root
        """
        folders = self._config.folders

        mapping = {
            ContentType.ARTICLE: folders.article,
            ContentType.VIDEO: folders.video,
            ContentType.REPO: folders.repo,
            ContentType.NEWS: folders.news,
            ContentType.WALKTHROUGH: folders.walkthrough,
            ContentType.PRINTABLE: folders.printable,
        }

        return mapping.get(content_type, folders.article)

    async def close(self) -> None:
        """Close resources and cleanup.

        Should be called when done using the service to properly clean up
        HTTP connections and other resources.
        """
        await self._ai_router.close()
        logger.info("Closed CaptureService")

    async def __aenter__(self) -> "CaptureService":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

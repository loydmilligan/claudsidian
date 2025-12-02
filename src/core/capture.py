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
from src.models.note import Note, Frontmatter, AIMetadata, AICallInfo
from src.models.queue import QueueItem, QueueStatus
from src.core.content_type import ContentType, detect_content_type
from src.core.extractors.article import ArticleExtractor, ArticleContent
from src.core.extractors.github import GitHubExtractor, GitHubContent
from src.core.extractors.news import NewsExtractor, NewsContent
from src.core.extractors.printable import PrintableExtractor, PrintableContent
from src.core.extractors.walkthrough import WalkthroughExtractor, WalkthroughContent
from src.core.extractors.youtube import YouTubeExtractor, YouTubeContent
from src.core.ai.router import AIRouter, AIRouterError, AIResponse
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

            # Step 2: Detect content type first (needed to choose extractor)
            # For videos, we detect from URL; for articles, we may refine after fetching
            content_type = self._detect_content_type(request, url, "")
            logger.info(f"Initial content type detection: {content_type}")

            # Step 3: Fetch and extract content based on type (T031b - HTTP error handling)
            try:
                if content_type == ContentType.VIDEO:
                    extracted = await self._fetch_video_content(url)
                    content_for_ai = extracted.transcript_text or extracted.description
                    title = extracted.title
                elif content_type == ContentType.REPO:
                    extracted = await self._fetch_repo_content(url)
                    content_for_ai = extracted.readme_content or extracted.description
                    title = extracted.full_name
                elif content_type == ContentType.NEWS:
                    extracted = await self._fetch_news_content(url)
                    content_for_ai = extracted.content
                    title = extracted.title
                elif content_type == ContentType.WALKTHROUGH:
                    extracted = await self._fetch_walkthrough_content(url)
                    content_for_ai = extracted.content
                    title = extracted.title
                elif content_type == ContentType.PRINTABLE:
                    extracted = await self._fetch_printable_content(url)
                    content_for_ai = extracted.description
                    title = extracted.title
                else:
                    extracted = await self._fetch_article_content(url)
                    content_for_ai = extracted.content
                    title = extracted.title
                    # Refine content type detection with actual content
                    content_type = self._detect_content_type(request, url, extracted.content)
                    logger.info(f"Refined content type: {content_type}")
            except httpx.HTTPStatusError as e:
                return await self._handle_http_error(e, request)
            except httpx.HTTPError as e:
                # Network errors (timeout, connection error, etc.)
                logger.error(f"Network error fetching URL: {e}")
                return await self._queue_for_retry(
                    request,
                    f"Network error: {str(e)}"
                )
            except Exception as e:
                # Handle yt-dlp or other extraction errors
                logger.error(f"Extraction error: {e}")
                return CaptureResult(
                    success=False,
                    error=f"Failed to extract content: {str(e)}"
                )

            # Step 4: Generate summary and tags via AI
            try:
                summary_response = await self._generate_summary(content_for_ai, content_type.value)
                tags, tags_response = await self._generate_tags(content_for_ai, title)
            except AIRouterError as e:
                # AI errors should trigger retry (could be temporary API issues)
                logger.error(f"AI processing error: {e}")
                return await self._queue_for_retry(
                    request,
                    f"AI processing error: {str(e)}"
                )

            # Extract summary text for use in note
            summary = summary_response.content

            # Step 5: Find backlinks
            related_notes = self._backlinks.find_related(tags, min_shared=2)
            backlinks_section = self._backlinks.format_backlinks(related_notes)

            # Step 6: Format note content based on type
            if content_type == ContentType.VIDEO:
                full_content = self._format_video_content(
                    extracted,  # type: YouTubeContent
                    summary,
                    backlinks_section
                )
            elif content_type == ContentType.REPO:
                full_content = self._format_repo_content(
                    extracted,  # type: GitHubContent
                    summary,
                    backlinks_section
                )
            elif content_type == ContentType.NEWS:
                full_content = self._format_news_content(
                    extracted,  # type: NewsContent
                    summary,
                    backlinks_section
                )
            elif content_type == ContentType.WALKTHROUGH:
                full_content = self._format_walkthrough_content(
                    extracted,  # type: WalkthroughContent
                    summary,
                    backlinks_section
                )
            elif content_type == ContentType.PRINTABLE:
                full_content = self._format_printable_content(
                    extracted,  # type: PrintableContent
                    summary,
                    backlinks_section
                )
            else:
                full_content = self._format_note_content(
                    extracted,  # type: ArticleContent
                    summary,
                    backlinks_section
                )

            # Step 7: Create note object with AI metadata
            ai_metadata = AIMetadata(
                summary=AICallInfo(
                    backend=summary_response.backend,
                    model=summary_response.model,
                    temperature=summary_response.temperature,
                    max_tokens=summary_response.max_tokens
                ),
                tags=AICallInfo(
                    backend=tags_response.backend,
                    model=tags_response.model,
                    temperature=tags_response.temperature,
                    max_tokens=tags_response.max_tokens
                )
            )

            frontmatter = Frontmatter(
                source=request.url,
                captured=request.timestamp,
                type=content_type,
                tags=tags,
                summary=summary,
                ai=ai_metadata
            )

            # Get target folder based on content type
            target_folder = self._get_folder_for_type(content_type)

            note = Note(
                title=title,
                content=full_content,
                frontmatter=frontmatter,
                file_path=f"{target_folder}/{title}.md"  # Will be sanitized by writer
            )

            # Step 8: Write note to vault
            note_path = self._writer.write_note(note, subfolder=target_folder)
            relative_path = str(note_path.relative_to(Path(self._config.vault_path)))

            logger.info(f"Successfully created note at: {relative_path}")

            return CaptureResult(
                success=True,
                note_path=relative_path,
                title=title,
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

    async def _fetch_article_content(self, url: str) -> ArticleContent:
        """Fetch and extract article content from URL.

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

    async def _fetch_video_content(self, url: str) -> YouTubeContent:
        """Fetch and extract YouTube video content from URL.

        Args:
            url: The YouTube URL to fetch

        Returns:
            YouTubeContent with extracted data (metadata, transcript, chapters)

        Raises:
            Exception: For yt-dlp or transcript API errors
        """
        extractor = YouTubeExtractor()
        video = extractor.extract(url)
        logger.info(
            f"Extracted video: {video.title} "
            f"(duration: {video.duration}s, has_transcript: {video.has_transcript})"
        )
        return video

    async def _fetch_repo_content(self, url: str) -> GitHubContent:
        """Fetch and extract GitHub repository content from URL.

        Args:
            url: The GitHub repository URL to fetch

        Returns:
            GitHubContent with extracted data (metadata, README, tech tags)

        Raises:
            httpx.HTTPError: For API errors
            ValueError: For invalid GitHub URLs
        """
        async with GitHubExtractor() as extractor:
            repo = await extractor.extract(url)
            logger.info(
                f"Extracted repo: {repo.full_name} "
                f"(stars: {repo.stars}, language: {repo.language})"
            )
            return repo

    async def _fetch_news_content(self, url: str) -> NewsContent:
        """Fetch and extract news article content from URL.

        Args:
            url: The news article URL to fetch

        Returns:
            NewsContent with extracted data (article, metadata, source info)

        Raises:
            httpx.HTTPError: For HTTP errors
            ValueError: For invalid HTML content
        """
        async with NewsExtractor() as extractor:
            news = await extractor.extract(url)
            logger.info(
                f"Extracted news: {news.title} "
                f"(source: {news.source_name}, words: {news.word_count})"
            )
            return news

    async def _fetch_walkthrough_content(self, url: str) -> WalkthroughContent:
        """Fetch and extract walkthrough/tutorial content from URL.

        Args:
            url: The tutorial URL to fetch

        Returns:
            WalkthroughContent with extracted data (steps, prerequisites, warnings)

        Raises:
            httpx.HTTPError: For HTTP errors
            ValueError: For invalid HTML content
        """
        async with WalkthroughExtractor() as extractor:
            walkthrough = await extractor.extract(url)
            logger.info(
                f"Extracted walkthrough: {walkthrough.title} "
                f"(steps: {len(walkthrough.steps)}, code_blocks: {walkthrough.code_blocks})"
            )
            return walkthrough

    async def _fetch_printable_content(self, url: str) -> PrintableContent:
        """Fetch and extract 3D printable model content from URL.

        Args:
            url: The 3D model URL to fetch (Thingiverse, Printables, Cults3D)

        Returns:
            PrintableContent with extracted data (metadata, print settings, files)

        Raises:
            httpx.HTTPError: For HTTP errors
            ValueError: For unsupported platforms
        """
        async with PrintableExtractor() as extractor:
            printable = await extractor.extract(url)
            logger.info(
                f"Extracted printable: {printable.title} "
                f"(platform: {printable.platform}, files: {', '.join(printable.file_types)})"
            )
            return printable

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

    async def _generate_summary(self, content: str, content_type: str) -> AIResponse:
        """Generate AI summary of content.

        Args:
            content: The content to summarize
            content_type: Type of content (article, video, repo, etc.)

        Returns:
            AIResponse with summary and metadata

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

        response = await self._ai_router.route_request(
            task_type="summarize_long",
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.7
        )

        # Clean up the content
        response.content = response.content.strip()
        return response

    async def _generate_tags(self, content: str, title: str) -> tuple[list[str], AIResponse]:
        """Generate AI tags for content.

        Args:
            content: The content to analyze
            title: Title of the content

        Returns:
            Tuple of (tags list, AIResponse with metadata)

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

        response = await self._ai_router.route_request(
            task_type="tagging",
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.5
        )

        # Parse comma-separated tags
        tags = [tag.strip() for tag in response.content.split(',') if tag.strip()]

        logger.info(f"Generated {len(tags)} tags: {', '.join(tags[:5])}...")

        return tags, response

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

    def _format_video_content(
        self,
        video: YouTubeContent,
        summary: str,
        backlinks_section: str
    ) -> str:
        """Format YouTube video note content.

        Combines video metadata, transcript summary, chapters, and backlinks.

        Args:
            video: Extracted YouTube video content
            summary: AI-generated summary
            backlinks_section: Formatted backlinks section

        Returns:
            Complete formatted markdown content
        """
        sections = []

        # Title
        sections.append(f"# {video.title}")
        sections.append("")

        # Video embed/link
        sections.append("## Video")
        sections.append("")
        if video.thumbnail_url:
            sections.append(f"[![{video.title}]({video.thumbnail_url})]({video.source_url})")
        else:
            sections.append(f"[Watch on YouTube]({video.source_url})")
        sections.append("")

        # Metadata
        sections.append("## Info")
        sections.append("")
        sections.append(f"**Channel:** [{video.channel}]({video.channel_url or video.source_url})")

        # Format duration
        hours, remainder = divmod(video.duration, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            duration_str = f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            duration_str = f"{minutes}:{seconds:02d}"
        sections.append(f"**Duration:** {duration_str}")

        if video.upload_date:
            sections.append(f"**Uploaded:** {video.upload_date}")
        if video.view_count:
            sections.append(f"**Views:** {video.view_count:,}")
        sections.append("")

        # Summary section
        sections.append("## Summary")
        sections.append("")
        sections.append(summary)
        sections.append("")

        # Chapters if available
        if video.chapters:
            sections.append("## Chapters")
            sections.append("")
            for chapter in video.chapters:
                # Format timestamp
                ch_mins, ch_secs = divmod(chapter.start_time, 60)
                ch_hours, ch_mins = divmod(ch_mins, 60)
                if ch_hours > 0:
                    ts = f"{ch_hours}:{ch_mins:02d}:{ch_secs:02d}"
                else:
                    ts = f"{ch_mins}:{ch_secs:02d}"
                # Link to timestamp
                sections.append(f"- [{ts}]({video.source_url}&t={chapter.start_time}) {chapter.title}")
            sections.append("")

        # Transcript notice
        if video.has_transcript:
            sections.append("## Transcript")
            sections.append("")
            sections.append("*Transcript available - used for AI summarization.*")
            sections.append("")
        else:
            sections.append("> **Note:** No transcript available for this video.")
            sections.append("")

        # Description (truncated)
        if video.description:
            sections.append("## Description")
            sections.append("")
            desc = video.description[:1000]
            if len(video.description) > 1000:
                desc += "..."
            sections.append(desc)
            sections.append("")

        # Backlinks section
        if backlinks_section:
            sections.append("")
            sections.append(backlinks_section)

        return "\n".join(sections)

    def _format_repo_content(
        self,
        repo: GitHubContent,
        summary: str,
        backlinks_section: str
    ) -> str:
        """Format GitHub repository note content.

        Combines repository metadata, README summary, and backlinks.

        Args:
            repo: Extracted GitHub repository content
            summary: AI-generated summary
            backlinks_section: Formatted backlinks section

        Returns:
            Complete formatted markdown content
        """
        sections = []

        # Title
        sections.append(f"# {repo.full_name}")
        sections.append("")

        # Summary section
        sections.append("## Summary")
        sections.append("")
        sections.append(summary)
        sections.append("")

        # Repository info table
        sections.append("## Repository Info")
        sections.append("")
        sections.append("| Metric | Value |")
        sections.append("|--------|-------|")
        sections.append(f"| Stars | ⭐ {repo.stars:,} |")
        sections.append(f"| Forks | 🔱 {repo.forks:,} |")
        if repo.language:
            sections.append(f"| Language | {repo.language} |")
        if repo.license:
            sections.append(f"| License | {repo.license} |")
        sections.append(f"| Open Issues | {repo.open_issues:,} |")
        if repo.updated_at:
            # Format date nicely
            update_date = repo.updated_at[:10] if repo.updated_at else "Unknown"
            sections.append(f"| Last Updated | {update_date} |")
        sections.append("")

        # Links
        sections.append(f"[View on GitHub]({repo.source_url})")
        if repo.homepage:
            sections.append(f" | [Project Homepage]({repo.homepage})")
        sections.append("")

        # Topics
        if repo.topics:
            sections.append("## Topics")
            sections.append("")
            topics_formatted = " ".join([f"`{topic}`" for topic in repo.topics])
            sections.append(topics_formatted)
            sections.append("")

        # Description
        if repo.description:
            sections.append("## Description")
            sections.append("")
            sections.append(repo.description)
            sections.append("")

        # README (truncated for note brevity)
        if repo.has_readme and repo.readme_content:
            sections.append("## README")
            sections.append("")
            # Truncate very long READMEs
            readme = repo.readme_content
            if len(readme) > 5000:
                readme = readme[:5000] + "\n\n*[README truncated - view full on GitHub]*"
            sections.append(readme)
            sections.append("")

        # Tech tags detected
        if repo.tech_tags:
            sections.append("## Technologies")
            sections.append("")
            tech_formatted = " ".join([f"`{tag}`" for tag in repo.tech_tags])
            sections.append(tech_formatted)
            sections.append("")

        # Backlinks section
        if backlinks_section:
            sections.append("")
            sections.append(backlinks_section)

        return "\n".join(sections)

    def _format_news_content(
        self,
        news: NewsContent,
        summary: str,
        backlinks_section: str
    ) -> str:
        """Format news article note content.

        Combines news article with source info, metadata, and backlinks.

        Args:
            news: Extracted news article content
            summary: AI-generated summary
            backlinks_section: Formatted backlinks section

        Returns:
            Complete formatted markdown content
        """
        sections = []

        # Title
        sections.append(f"# {news.title}")
        sections.append("")

        # Breaking news indicator
        if news.is_breaking:
            sections.append("> **BREAKING NEWS**")
            sections.append("")

        # Summary section
        sections.append("## Summary")
        sections.append("")
        sections.append(summary)
        sections.append("")

        # Source info table
        sections.append("## Source Info")
        sections.append("")
        sections.append("| Field | Value |")
        sections.append("|-------|-------|")
        sections.append(f"| Source | **{news.source_name}** |")
        if news.publish_date:
            pub_date = news.publish_date[:10] if news.publish_date else "Unknown"
            sections.append(f"| Published | {pub_date} |")
        if news.author:
            sections.append(f"| Author | {news.author} |")
        if news.section:
            sections.append(f"| Section | {news.section} |")
        if news.last_updated and news.last_updated != news.publish_date:
            update_date = news.last_updated[:10] if news.last_updated else ""
            sections.append(f"| Updated | {update_date} |")
        sections.append(f"| Word Count | {news.word_count:,} |")
        sections.append("")

        # Link to original
        sections.append(f"[Read Original Article]({news.source_url})")
        sections.append("")

        # Main content
        sections.append("## Content")
        sections.append("")
        sections.append(news.content)
        sections.append("")

        # Backlinks section
        if backlinks_section:
            sections.append("")
            sections.append(backlinks_section)

        return "\n".join(sections)

    def _format_walkthrough_content(
        self,
        walkthrough: WalkthroughContent,
        summary: str,
        backlinks_section: str
    ) -> str:
        """Format walkthrough/tutorial note content.

        Combines tutorial content with steps, prerequisites, and backlinks.

        Args:
            walkthrough: Extracted walkthrough content
            summary: AI-generated summary
            backlinks_section: Formatted backlinks section

        Returns:
            Complete formatted markdown content
        """
        sections = []

        # Title
        sections.append(f"# {walkthrough.title}")
        sections.append("")

        # Info table
        if walkthrough.difficulty or walkthrough.estimated_time or walkthrough.steps:
            sections.append("| Info | Value |")
            sections.append("|------|-------|")
            if walkthrough.difficulty:
                sections.append(f"| Difficulty | {walkthrough.difficulty} |")
            if walkthrough.estimated_time:
                sections.append(f"| Est. Time | {walkthrough.estimated_time} |")
            if walkthrough.steps:
                sections.append(f"| Steps | {len(walkthrough.steps)} |")
            if walkthrough.code_blocks:
                sections.append(f"| Code Blocks | {walkthrough.code_blocks} |")
            sections.append("")

        # Summary section
        sections.append("## Summary")
        sections.append("")
        sections.append(summary)
        sections.append("")

        # Prerequisites
        if walkthrough.prerequisites:
            sections.append("## Prerequisites")
            sections.append("")
            for prereq in walkthrough.prerequisites:
                sections.append(f"- {prereq}")
            sections.append("")

        # Warnings
        if walkthrough.warnings:
            sections.append("## Warnings")
            sections.append("")
            for warning in walkthrough.warnings:
                sections.append(f"> ⚠️ {warning}")
            sections.append("")

        # Steps
        if walkthrough.steps:
            sections.append("## Steps")
            sections.append("")
            for step in walkthrough.steps:
                indicators = ""
                if step.has_warning:
                    indicators += "⚠️ "
                if step.has_code:
                    indicators += "💻 "
                sections.append(f"### Step {step.number}: {step.title}")
                if indicators:
                    sections.append(f"*{indicators.strip()}*")
                sections.append("")

        # Full content
        sections.append("## Full Content")
        sections.append("")
        sections.append(walkthrough.content)
        sections.append("")

        # Source link
        sections.append(f"[View Original Tutorial]({walkthrough.source_url})")
        sections.append("")

        # Backlinks section
        if backlinks_section:
            sections.append("")
            sections.append(backlinks_section)

        return "\n".join(sections)

    def _format_printable_content(
        self,
        printable: PrintableContent,
        summary: str,
        backlinks_section: str
    ) -> str:
        """Format 3D printable model note content.

        Combines model metadata, print settings, and backlinks.

        Args:
            printable: Extracted 3D model content
            summary: AI-generated summary
            backlinks_section: Formatted backlinks section

        Returns:
            Complete formatted markdown content
        """
        sections = []

        # Title
        sections.append(f"# {printable.title}")
        sections.append("")

        # Summary section
        sections.append("## Summary")
        sections.append("")
        sections.append(summary)
        sections.append("")

        # Model info table
        sections.append("## Model Info")
        sections.append("")
        sections.append("| Field | Value |")
        sections.append("|-------|-------|")
        sections.append(f"| Platform | **{printable.platform}** |")

        creator_link = f"[{printable.creator}]({printable.creator_url})" if printable.creator_url else printable.creator
        sections.append(f"| Creator | {creator_link} |")

        if printable.download_count:
            sections.append(f"| Downloads | {printable.download_count:,} |")
        if printable.like_count:
            sections.append(f"| Likes | {printable.like_count:,} |")
        if printable.file_types:
            sections.append(f"| File Types | {', '.join(printable.file_types)} |")
        if printable.license:
            sections.append(f"| License | {printable.license} |")
        sections.append("")

        # Link to original
        sections.append(f"[View on {printable.platform}]({printable.source_url})")
        sections.append("")

        # Images
        if printable.images:
            sections.append("## Preview")
            sections.append("")
            for img in printable.images[:3]:  # Limit to 3 images
                sections.append(f"![{printable.title}]({img})")
            sections.append("")

        # Print settings
        ps = printable.print_settings
        if any([ps.material, ps.layer_height, ps.infill, ps.supports is not None]):
            sections.append("## Print Settings")
            sections.append("")
            sections.append("| Setting | Value |")
            sections.append("|---------|-------|")
            if ps.material:
                sections.append(f"| Material | {ps.material} |")
            if ps.layer_height:
                sections.append(f"| Layer Height | {ps.layer_height}mm |")
            if ps.infill is not None:
                sections.append(f"| Infill | {ps.infill}% |")
            if ps.supports is not None:
                sections.append(f"| Supports | {'Yes' if ps.supports else 'No'} |")
            if ps.raft is not None:
                sections.append(f"| Raft | {'Yes' if ps.raft else 'No'} |")
            if ps.print_time:
                sections.append(f"| Est. Time | {ps.print_time} |")
            if ps.notes:
                sections.append(f"| Notes | {ps.notes} |")
            sections.append("")

        # Tags from the model
        if printable.tags:
            sections.append("## Categories")
            sections.append("")
            tags_formatted = " ".join([f"`{tag}`" for tag in printable.tags])
            sections.append(tags_formatted)
            sections.append("")

        # Description
        if printable.description:
            sections.append("## Description")
            sections.append("")
            # Truncate very long descriptions
            desc = printable.description
            if len(desc) > 3000:
                desc = desc[:3000] + "\n\n*[Description truncated]*"
            sections.append(desc)
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

"""Inbox file watcher for URL capture.

This module watches an inbox.md file for URLs and automatically processes them
through the capture pipeline. URLs are extracted from markdown content and
removed after successful processing.

Features:
- Extract URLs from markdown formatted text
- Watch file for changes with debouncing
- Process URLs asynchronously
- Remove processed entries from inbox
- Handle concurrent file access
"""

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import urlparse

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

logger = logging.getLogger(__name__)


# URL regex pattern - matches http/https URLs
URL_PATTERN = re.compile(
    r'https?://[^\s<>"\'\]\)]+',
    re.IGNORECASE
)

# Markdown link pattern - [text](url)
MARKDOWN_LINK_PATTERN = re.compile(
    r'\[([^\]]*)\]\((https?://[^\s\)]+)\)',
    re.IGNORECASE
)


@dataclass
class InboxEntry:
    """An entry found in the inbox file.

    Attributes:
        url: The URL to capture
        line_number: Line number in the inbox file
        raw_line: The original line text
        is_markdown_link: Whether the URL was in markdown link format
        link_text: Text of the markdown link if applicable
    """

    url: str
    line_number: int
    raw_line: str
    is_markdown_link: bool = False
    link_text: Optional[str] = None


@dataclass
class ProcessingResult:
    """Result of processing an inbox entry.

    Attributes:
        entry: The inbox entry that was processed
        success: Whether processing succeeded
        note_path: Path to created note if successful
        error: Error message if failed
        timestamp: When processing completed
    """

    entry: InboxEntry
    success: bool
    note_path: Optional[str] = None
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


class InboxParser:
    """Parses inbox.md file to extract URLs for capture.

    Extracts URLs from various formats:
    - Plain URLs on their own line
    - Markdown links [text](url)
    - URLs in bullet points (- url or * url)
    - URLs mixed with text

    Example:
        >>> parser = InboxParser()
        >>> entries = parser.parse_file(Path("inbox.md"))
        >>> for entry in entries:
        ...     print(f"Found URL: {entry.url}")
    """

    def parse_file(self, file_path: Path) -> list[InboxEntry]:
        """Parse inbox file and extract all URLs.

        Args:
            file_path: Path to the inbox markdown file

        Returns:
            List of InboxEntry objects for each URL found

        Raises:
            FileNotFoundError: If file doesn't exist
            PermissionError: If file can't be read
        """
        if not file_path.exists():
            logger.warning(f"Inbox file not found: {file_path}")
            return []

        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception as e:
            logger.error(f"Error reading inbox file: {e}")
            return []

        return self.parse_content(content)

    def parse_content(self, content: str) -> list[InboxEntry]:
        """Parse content string and extract URLs.

        Args:
            content: Markdown content to parse

        Returns:
            List of InboxEntry objects
        """
        entries = []
        seen_urls = set()  # Avoid duplicates

        lines = content.split('\n')

        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()

            if not line_stripped:
                continue

            # Skip comments and headers
            if line_stripped.startswith('#') or line_stripped.startswith('<!--'):
                continue

            # Check for markdown links first
            for match in MARKDOWN_LINK_PATTERN.finditer(line):
                link_text, url = match.groups()
                url = self._clean_url(url)

                if url and self._is_valid_url(url) and url not in seen_urls:
                    seen_urls.add(url)
                    entries.append(InboxEntry(
                        url=url,
                        line_number=line_num,
                        raw_line=line,
                        is_markdown_link=True,
                        link_text=link_text,
                    ))

            # Check for plain URLs (not already found in markdown links)
            for match in URL_PATTERN.finditer(line):
                url = self._clean_url(match.group())

                if url and self._is_valid_url(url) and url not in seen_urls:
                    seen_urls.add(url)
                    entries.append(InboxEntry(
                        url=url,
                        line_number=line_num,
                        raw_line=line,
                        is_markdown_link=False,
                    ))

        logger.info(f"Parsed inbox: found {len(entries)} URLs")
        return entries

    def _clean_url(self, url: str) -> str:
        """Clean URL by removing trailing punctuation."""
        # Remove common trailing punctuation that might be captured
        url = url.rstrip('.,;:!?)\'\"')
        return url

    def _is_valid_url(self, url: str) -> bool:
        """Validate URL format."""
        try:
            parsed = urlparse(url)
            return bool(parsed.scheme and parsed.netloc)
        except Exception:
            return False

    def remove_entries(
        self,
        file_path: Path,
        entries: list[InboxEntry]
    ) -> bool:
        """Remove processed entries from inbox file.

        Args:
            file_path: Path to inbox file
            entries: Entries to remove

        Returns:
            True if file was updated successfully
        """
        if not entries:
            return True

        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\n')

            # Get line numbers to remove (0-indexed)
            lines_to_remove = {e.line_number - 1 for e in entries}

            # Filter out removed lines
            new_lines = [
                line for i, line in enumerate(lines)
                if i not in lines_to_remove
            ]

            # Remove consecutive empty lines
            cleaned_lines = []
            prev_empty = False
            for line in new_lines:
                is_empty = not line.strip()
                if not (is_empty and prev_empty):
                    cleaned_lines.append(line)
                prev_empty = is_empty

            # Write back
            file_path.write_text('\n'.join(cleaned_lines), encoding='utf-8')
            logger.info(f"Removed {len(entries)} entries from inbox")
            return True

        except Exception as e:
            logger.error(f"Error updating inbox file: {e}")
            return False


class InboxWatcher:
    """Watches inbox file for changes and triggers processing.

    Uses watchdog for cross-platform file system events with debouncing
    to handle rapid successive changes.

    Example:
        >>> watcher = InboxWatcher(Path("inbox.md"), callback)
        >>> watcher.start()
        >>> # ... file changes trigger callback ...
        >>> watcher.stop()
    """

    def __init__(
        self,
        inbox_path: Path,
        on_change: Callable[[], None],
        debounce_seconds: float = 1.0
    ):
        """Initialize inbox watcher.

        Args:
            inbox_path: Path to inbox file to watch
            on_change: Callback function when file changes
            debounce_seconds: Minimum time between callbacks
        """
        self._inbox_path = inbox_path
        self._on_change = on_change
        self._debounce_seconds = debounce_seconds
        self._observer: Optional[Observer] = None
        self._last_change_time = 0.0
        self._running = False

    def start(self) -> None:
        """Start watching the inbox file."""
        if self._running:
            return

        # Ensure parent directory exists
        watch_dir = self._inbox_path.parent
        if not watch_dir.exists():
            watch_dir.mkdir(parents=True)

        # Create inbox file if it doesn't exist
        if not self._inbox_path.exists():
            self._inbox_path.write_text(
                "# Inbox\n\n"
                "Add URLs here to capture them automatically.\n\n"
                "---\n\n",
                encoding='utf-8'
            )
            logger.info(f"Created inbox file: {self._inbox_path}")

        # Set up file watcher
        handler = _InboxEventHandler(self._on_file_change, self._inbox_path.name)
        self._observer = Observer()
        self._observer.schedule(handler, str(watch_dir), recursive=False)
        self._observer.start()
        self._running = True

        logger.info(f"Started watching inbox: {self._inbox_path}")

    def stop(self) -> None:
        """Stop watching the inbox file."""
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5.0)
            self._observer = None
        self._running = False
        logger.info("Stopped inbox watcher")

    def _on_file_change(self) -> None:
        """Handle file change event with debouncing."""
        current_time = time.time()

        if current_time - self._last_change_time < self._debounce_seconds:
            logger.debug("Debouncing file change")
            return

        self._last_change_time = current_time
        logger.info("Inbox file changed, triggering processing")
        self._on_change()

    @property
    def is_running(self) -> bool:
        """Check if watcher is running."""
        return self._running


class _InboxEventHandler(FileSystemEventHandler):
    """Internal handler for watchdog file events."""

    def __init__(self, callback: Callable[[], None], filename: str):
        self._callback = callback
        self._filename = filename
        super().__init__()

    def on_modified(self, event: FileModifiedEvent) -> None:
        """Handle file modification event."""
        if event.is_directory:
            return

        if Path(event.src_path).name == self._filename:
            self._callback()


class InboxProcessor:
    """Processes inbox entries through the capture pipeline.

    Coordinates parsing, capture, and cleanup of inbox entries.

    Example:
        >>> processor = InboxProcessor(config, inbox_path)
        >>> await processor.process_once()
        >>> # Or run continuously:
        >>> await processor.run()
    """

    def __init__(
        self,
        config,  # Configuration object
        inbox_path: Path,
        on_result: Optional[Callable[[ProcessingResult], None]] = None
    ):
        """Initialize inbox processor.

        Args:
            config: Configuration object for CaptureService
            inbox_path: Path to inbox file
            on_result: Optional callback for each processing result
        """
        self._config = config
        self._inbox_path = inbox_path
        self._on_result = on_result
        self._parser = InboxParser()
        self._watcher: Optional[InboxWatcher] = None
        self._running = False
        self._process_event = asyncio.Event()

    async def process_once(self) -> list[ProcessingResult]:
        """Process all entries in inbox once.

        Returns:
            List of processing results
        """
        from src.core.capture import CaptureService
        from src.models.capture import CaptureRequest, CaptureSource

        entries = self._parser.parse_file(self._inbox_path)
        if not entries:
            logger.debug("No entries in inbox")
            return []

        results = []
        successful_entries = []

        async with CaptureService(self._config) as service:
            for entry in entries:
                logger.info(f"Processing inbox entry: {entry.url}")

                try:
                    request = CaptureRequest(
                        url=entry.url,
                        source=CaptureSource.INBOX,
                        timestamp=datetime.now(),
                    )

                    capture_result = await service.capture(request)

                    result = ProcessingResult(
                        entry=entry,
                        success=capture_result.success,
                        note_path=capture_result.note_path,
                        error=capture_result.error,
                    )

                    if capture_result.success:
                        successful_entries.append(entry)
                        logger.info(f"Captured: {entry.url} -> {capture_result.note_path}")
                    elif capture_result.is_duplicate:
                        # Also remove duplicates from inbox
                        successful_entries.append(entry)
                        logger.info(f"Duplicate URL, removing: {entry.url}")
                    else:
                        logger.warning(f"Failed to capture: {entry.url} - {capture_result.error}")

                except Exception as e:
                    logger.error(f"Error processing {entry.url}: {e}")
                    result = ProcessingResult(
                        entry=entry,
                        success=False,
                        error=str(e),
                    )

                results.append(result)

                if self._on_result:
                    self._on_result(result)

        # Remove successfully processed entries
        if successful_entries:
            self._parser.remove_entries(self._inbox_path, successful_entries)

        return results

    async def run(self) -> None:
        """Run inbox processor continuously, watching for changes."""
        self._running = True

        # Set up watcher
        def on_change():
            self._process_event.set()

        self._watcher = InboxWatcher(self._inbox_path, on_change)
        self._watcher.start()

        # Initial processing
        await self.process_once()

        logger.info("Inbox processor running, waiting for changes...")

        try:
            while self._running:
                # Wait for change event or timeout
                try:
                    await asyncio.wait_for(
                        self._process_event.wait(),
                        timeout=60.0  # Check every minute even without changes
                    )
                except asyncio.TimeoutError:
                    pass

                self._process_event.clear()

                if self._running:
                    await self.process_once()

        finally:
            self.stop()

    def stop(self) -> None:
        """Stop the processor."""
        self._running = False
        self._process_event.set()  # Wake up the run loop

        if self._watcher:
            self._watcher.stop()
            self._watcher = None

        logger.info("Inbox processor stopped")

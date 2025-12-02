"""YouTube video extractor using yt-dlp and youtube-transcript-api."""

import logging
import re
from dataclasses import dataclass, field
from datetime import timedelta

import yt_dlp
from youtube_transcript_api import NoTranscriptFound, TranscriptsDisabled, YouTubeTranscriptApi

logger = logging.getLogger(__name__)


@dataclass
class Chapter:
    """Video chapter/section."""

    title: str
    start_time: int  # seconds
    end_time: int | None = None  # seconds, None for last chapter


@dataclass
class TranscriptSegment:
    """A segment of transcript with timestamp."""

    text: str
    start: float  # seconds
    duration: float


@dataclass
class YouTubeContent:
    """Extracted YouTube video content."""

    video_id: str
    title: str
    channel: str
    channel_url: str | None
    duration: int  # seconds
    description: str
    upload_date: str | None
    view_count: int | None
    thumbnail_url: str | None
    source_url: str
    transcript: list[TranscriptSegment] = field(default_factory=list)
    chapters: list[Chapter] = field(default_factory=list)
    transcript_text: str = ""  # Full transcript as plain text
    has_transcript: bool = False


class YouTubeExtractor:
    """Extracts content from YouTube videos."""

    def __init__(self) -> None:
        self._ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "skip_download": True,
        }

    def extract(self, url: str) -> YouTubeContent:
        """Extract video content from URL."""
        video_id = self._extract_video_id(url)
        if not video_id:
            raise ValueError(f"Could not extract video ID from URL: {url}")

        # Get metadata with yt-dlp
        metadata = self._get_metadata(url)

        # Get transcript
        transcript, transcript_text, has_transcript = self._get_transcript(video_id)

        # Get chapters
        chapters = self._extract_chapters(
            metadata.get("description", ""), metadata.get("duration", 0)
        )

        return YouTubeContent(
            video_id=video_id,
            title=metadata.get("title", "Unknown Title"),
            channel=metadata.get("channel", metadata.get("uploader", "Unknown Channel")),
            channel_url=metadata.get("channel_url"),
            duration=metadata.get("duration", 0),
            description=metadata.get("description", ""),
            upload_date=metadata.get("upload_date"),
            view_count=metadata.get("view_count"),
            thumbnail_url=metadata.get("thumbnail"),
            source_url=url,
            transcript=transcript,
            transcript_text=transcript_text,
            has_transcript=has_transcript,
            chapters=chapters,
        )

    def _extract_video_id(self, url: str) -> str | None:
        """Extract video ID from various YouTube URL formats."""
        patterns = [
            r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})",
            r"youtube\.com/v/([a-zA-Z0-9_-]{11})",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def _get_metadata(self, url: str) -> dict:
        """Get video metadata using yt-dlp."""
        with yt_dlp.YoutubeDL(self._ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)

    def _get_transcript(
        self, video_id: str
    ) -> tuple[list[TranscriptSegment], str, bool]:
        """Get video transcript. Returns (segments, full_text, has_transcript)."""
        try:
            # youtube-transcript-api v1.x uses instance method .fetch()
            api = YouTubeTranscriptApi()
            transcript_data = api.fetch(video_id, languages=["en", "en-US", "en-GB"])

            # Convert to our segment format
            segments = [
                TranscriptSegment(
                    text=snippet.text,
                    start=snippet.start,
                    duration=snippet.duration
                )
                for snippet in transcript_data
            ]
            full_text = " ".join(snippet.text for snippet in transcript_data)
            return segments, full_text, True
        except (NoTranscriptFound, TranscriptsDisabled) as e:
            logger.warning(f"No transcript available for {video_id}: {e}")
            return [], "", False
        except Exception as e:
            logger.error(f"Error getting transcript for {video_id}: {e}")
            return [], "", False

    def _extract_chapters(self, description: str, duration: int) -> list[Chapter]:
        """Extract chapters from description or return empty if none found."""
        # Pattern for timestamps like "0:00", "1:23:45"
        timestamp_pattern = r"^(\d{1,2}:)?(\d{1,2}):(\d{2})\s+[-–—]?\s*(.+?)$"

        chapters = []
        for line in description.split("\n"):
            match = re.match(timestamp_pattern, line.strip())
            if match:
                hours = int(match.group(1)[:-1]) if match.group(1) else 0
                minutes = int(match.group(2))
                seconds = int(match.group(3))
                title = match.group(4).strip()

                start_time = hours * 3600 + minutes * 60 + seconds
                chapters.append(Chapter(title=title, start_time=start_time))

        # Set end times
        for i, chapter in enumerate(chapters):
            if i + 1 < len(chapters):
                chapter.end_time = chapters[i + 1].start_time
            else:
                chapter.end_time = duration

        return chapters

    def format_timestamp(self, seconds: float) -> str:
        """Format seconds as HH:MM:SS or MM:SS."""
        td = timedelta(seconds=int(seconds))
        total_seconds = int(td.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"

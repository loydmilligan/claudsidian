"""Capture request models and enums."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, HttpUrl, field_validator


class CaptureSource(str, Enum):
    """Source of the capture request."""

    BROWSER = "browser"
    CLI = "cli"
    INBOX = "inbox"
    ANDROID = "android"


class ForceType(str, Enum):
    """Force a specific content type instead of auto-detection."""

    ARTICLE = "article"
    VIDEO = "video"
    REPO = "repo"
    NEWS = "news"
    WALKTHROUGH = "walkthrough"
    PRINTABLE = "printable"


class CaptureRequest(BaseModel):
    """Model for capturing content from various sources.

    Attributes:
        url: The URL to capture, must be valid HTTP/HTTPS
        source: Where the request came from
        timestamp: When the request was received
        force_type: Optional override for content type auto-detection
        skip_ai: If True, skip AI processing (for inbox quick-capture mode)
        model_override: Optional model ID to use instead of config default
        temperature_override: Optional temperature override (0.0-1.0)
        max_tokens_override: Optional max_tokens override
    """

    url: HttpUrl
    source: CaptureSource
    timestamp: datetime
    force_type: Optional[ForceType] = None
    skip_ai: bool = False
    model_override: Optional[str] = None
    temperature_override: Optional[float] = None
    max_tokens_override: Optional[int] = None

    @field_validator("url")
    @classmethod
    def validate_url_scheme(cls, v: HttpUrl) -> HttpUrl:
        """Ensure URL uses HTTP or HTTPS scheme."""
        if v.scheme not in ("http", "https"):
            raise ValueError("URL must use HTTP or HTTPS scheme")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "url": "https://example.com/article",
                    "source": "browser",
                    "timestamp": "2025-12-01T12:00:00Z",
                    "force_type": "article",
                }
            ]
        }
    }

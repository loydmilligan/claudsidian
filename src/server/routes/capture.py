"""Capture endpoint for URL processing.

This module provides the POST /capture endpoint for capturing web content
and converting it to Obsidian notes. It handles URL validation, content type
detection, and queuing for asynchronous processing.

The endpoint supports multiple response types:
- CaptureResponseBody: Successful immediate capture
- QueuedResponseBody: Capture queued for background processing
- DuplicateResponseBody: URL already captured
- ErrorResponseBody: Error during capture
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, HttpUrl

router = APIRouter()


class CaptureRequestBody(BaseModel):
    """Request body for capturing a URL.

    Attributes:
        url: The URL to capture (must be valid HTTP/HTTPS)
        source: Source of the capture request (browser, cli, inbox, android)
        force_type: Optional content type override (article, video, repo, news, walkthrough, printable)
    """

    url: HttpUrl
    source: str = "browser"
    force_type: str | None = None


class CaptureResponseBody(BaseModel):
    """Successful capture response.

    Attributes:
        success: Always True for successful captures
        note_path: Path to the created note relative to vault root
        title: Title of the captured note
        tags: List of auto-generated tags
        content_type: Detected or forced content type
    """

    success: bool = True
    note_path: str
    title: str
    tags: list[str]
    content_type: str


class QueuedResponseBody(BaseModel):
    """Response when capture is queued for processing.

    Attributes:
        queued: Always True for queued captures
        queue_id: Unique identifier for the queued capture
        message: Descriptive message about the queued capture
    """

    queued: bool = True
    queue_id: str
    message: str = "Capture queued for processing"


class DuplicateResponseBody(BaseModel):
    """Response when URL has already been captured.

    Attributes:
        duplicate: Always True for duplicate captures
        existing_note: Path to the existing note
        message: Descriptive message about the duplicate
    """

    duplicate: bool = True
    existing_note: str
    message: str = "Note already exists for this URL"


class ErrorResponseBody(BaseModel):
    """Error response for failed captures.

    Attributes:
        error: Always True for error responses
        message: Human-readable error message
        code: Error code for programmatic handling
    """

    error: bool = True
    message: str
    code: str


@router.post(
    "/capture",
    response_model=CaptureResponseBody,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Capture completed successfully",
            "model": CaptureResponseBody,
        },
        202: {
            "description": "Capture queued for processing",
            "model": QueuedResponseBody,
        },
        400: {
            "description": "Invalid request",
            "model": ErrorResponseBody,
        },
        409: {
            "description": "URL already captured",
            "model": DuplicateResponseBody,
        },
    },
)
async def capture_url(request: CaptureRequestBody) -> CaptureResponseBody:
    """Capture a URL and create a note in the Obsidian vault.

    This endpoint validates the provided URL and creates a structured note
    with metadata in the configured Obsidian vault. The actual capture logic
    is implemented in T029.

    Args:
        request: Capture request containing URL, source, and optional type override

    Returns:
        CaptureResponseBody with note details

    Raises:
        HTTPException: For invalid URLs or processing errors

    Example:
        >>> response = await capture_url(CaptureRequestBody(
        ...     url="https://example.com/article",
        ...     source="browser",
        ...     force_type="article"
        ... ))
        >>> response.success
        True
    """
    # Validate URL scheme
    if request.url.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": True,
                "message": "URL must use HTTP or HTTPS scheme",
                "code": "INVALID_URL_SCHEME",
            },
        )

    # Validate source
    valid_sources = ["browser", "cli", "inbox", "android"]
    if request.source not in valid_sources:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": True,
                "message": f"Invalid source. Must be one of: {', '.join(valid_sources)}",
                "code": "INVALID_SOURCE",
            },
        )

    # Validate force_type if provided
    if request.force_type is not None:
        valid_types = ["article", "video", "repo", "news", "walkthrough", "printable"]
        if request.force_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": True,
                    "message": f"Invalid force_type. Must be one of: {', '.join(valid_types)}",
                    "code": "INVALID_FORCE_TYPE",
                },
            )

    # TODO: Implement actual capture logic in T029
    # For now, return placeholder response
    return CaptureResponseBody(
        note_path="Learning/placeholder.md",
        title="Placeholder",
        tags=["placeholder"],
        content_type="article",
    )

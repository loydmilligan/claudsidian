"""Queue models for managing capture requests."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from src.models.capture import CaptureRequest


class QueueStatus(str, Enum):
    """Status of a queue item."""

    PENDING = "pending"
    PROCESSING = "processing"
    FAILED = "failed"
    COMPLETED = "completed"


class QueueItem(BaseModel):
    """Model for a queued capture request.

    Attributes:
        id: Unique identifier for the queue item
        request: The original capture request
        status: Current processing status
        attempts: Number of times processing was attempted
        error: Error message if the item failed
        created_at: Timestamp when the item was queued
        updated_at: Timestamp of the last status change
    """

    id: UUID = Field(default_factory=uuid4)
    request: CaptureRequest
    status: QueueStatus = QueueStatus.PENDING
    attempts: int = Field(default=0, ge=0)
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def increment_attempt(self) -> None:
        """Increment the attempt counter and update the timestamp."""
        self.attempts += 1
        self.updated_at = datetime.now(timezone.utc)

    def mark_failed(self, error: str) -> None:
        """Mark the item as failed and record the error.

        Args:
            error: Error message describing the failure
        """
        self.status = QueueStatus.FAILED
        self.error = error
        self.updated_at = datetime.now(timezone.utc)

    def mark_completed(self) -> None:
        """Mark the item as successfully completed."""
        self.status = QueueStatus.COMPLETED
        self.error = None
        self.updated_at = datetime.now(timezone.utc)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "request": {
                        "url": "https://example.com/article",
                        "source": "browser",
                        "timestamp": "2025-12-01T12:00:00Z",
                        "force_type": "article",
                    },
                    "status": "pending",
                    "attempts": 0,
                    "error": None,
                    "created_at": "2025-12-01T12:00:00Z",
                    "updated_at": "2025-12-01T12:00:00Z",
                }
            ]
        }
    }

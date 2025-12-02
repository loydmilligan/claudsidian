"""Queue API routes for managing the capture queue.

Provides REST endpoints for:
- GET /queue - List all queue items
- GET /queue/{id} - Get a specific queue item
- DELETE /queue/{id} - Remove an item from the queue
- POST /queue/retry - Retry failed items
- POST /queue/retry/{id} - Retry a specific item
"""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.core.config import config_exists, load_config
from src.core.queue import CaptureQueue
from src.models.queue import QueueStatus

router = APIRouter(prefix="/queue", tags=["queue"])


def _get_queue() -> CaptureQueue:
    """Get the capture queue.

    Returns:
        CaptureQueue instance

    Raises:
        HTTPException: If configuration is not set up
    """
    if not config_exists():
        raise HTTPException(status_code=500, detail="Configuration not found")

    cfg = load_config()
    if cfg is None:
        raise HTTPException(status_code=500, detail="Failed to load configuration")

    queue_path = Path(cfg.vault_path) / ".claudsidian" / "queue.json"
    return CaptureQueue(queue_path)


class QueueItemResponse(BaseModel):
    """Response model for a queue item."""

    id: str
    url: str
    status: str
    attempts: int
    error: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class QueueListResponse(BaseModel):
    """Response model for queue list."""

    total: int
    items: list[QueueItemResponse]


class RetryResponse(BaseModel):
    """Response for retry operations."""

    message: str
    count: int


class RemoveResponse(BaseModel):
    """Response for remove operations."""

    message: str
    removed: bool


@router.get("", response_model=QueueListResponse)
async def list_queue(
    status: Optional[str] = Query(None, description="Filter by status (pending, processing, completed, failed)")
) -> QueueListResponse:
    """List all items in the capture queue.

    Optionally filter by status.

    Args:
        status: Optional status filter

    Returns:
        QueueListResponse with all matching items
    """
    capture_queue = _get_queue()
    items = capture_queue.get_all()

    # Filter by status if specified
    if status:
        try:
            status_enum = QueueStatus(status)
            items = [item for item in items if item.status == status_enum]
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: pending, processing, completed, failed"
            )

    # Convert to response format
    response_items = []
    for item in items:
        response_items.append(QueueItemResponse(
            id=str(item.id),
            url=str(item.request.url),
            status=item.status.value,
            attempts=item.attempts,
            error=item.error,
            created_at=item.created_at.isoformat(),
            updated_at=item.updated_at.isoformat() if item.updated_at else None,
        ))

    return QueueListResponse(total=len(response_items), items=response_items)


@router.get("/{item_id}", response_model=QueueItemResponse)
async def get_queue_item(item_id: str) -> QueueItemResponse:
    """Get a specific queue item by ID.

    Args:
        item_id: The queue item ID

    Returns:
        QueueItemResponse for the item

    Raises:
        HTTPException: If item not found
    """
    capture_queue = _get_queue()
    item = capture_queue.get_by_id(item_id)

    if not item:
        raise HTTPException(status_code=404, detail=f"Queue item '{item_id}' not found")

    return QueueItemResponse(
        id=str(item.id),
        url=str(item.request.url),
        status=item.status.value,
        attempts=item.attempts,
        error=item.error,
        created_at=item.created_at.isoformat(),
        updated_at=item.updated_at.isoformat() if item.updated_at else None,
    )


@router.delete("/{item_id}", response_model=RemoveResponse)
async def remove_queue_item(item_id: str) -> RemoveResponse:
    """Remove an item from the queue.

    Args:
        item_id: The queue item ID to remove

    Returns:
        RemoveResponse with result

    Raises:
        HTTPException: If item not found
    """
    capture_queue = _get_queue()

    if capture_queue.remove(item_id):
        return RemoveResponse(message=f"Removed item {item_id}", removed=True)
    else:
        raise HTTPException(status_code=404, detail=f"Queue item '{item_id}' not found")


@router.post("/retry", response_model=RetryResponse)
async def retry_failed_items() -> RetryResponse:
    """Retry all failed items in the queue.

    Resets all items with FAILED status to PENDING.

    Returns:
        RetryResponse with count of items reset
    """
    capture_queue = _get_queue()
    items = [item for item in capture_queue.get_all() if item.status == QueueStatus.FAILED]

    count = 0
    for item in items:
        item.status = QueueStatus.PENDING
        capture_queue.update(item)
        count += 1

    return RetryResponse(message=f"Reset {count} items to pending", count=count)


@router.post("/retry/{item_id}", response_model=RetryResponse)
async def retry_queue_item(item_id: str) -> RetryResponse:
    """Retry a specific queue item.

    Resets the item to PENDING status if it was FAILED.

    Args:
        item_id: The queue item ID to retry

    Returns:
        RetryResponse with result

    Raises:
        HTTPException: If item not found or already completed
    """
    capture_queue = _get_queue()
    item = capture_queue.get_by_id(item_id)

    if not item:
        raise HTTPException(status_code=404, detail=f"Queue item '{item_id}' not found")

    if item.status == QueueStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Cannot retry completed item")

    item.status = QueueStatus.PENDING
    capture_queue.update(item)

    return RetryResponse(message=f"Reset item {item_id} to pending", count=1)


@router.delete("", response_model=RemoveResponse)
async def clear_queue(
    status: str = Query("completed", description="Clear items with this status (completed, failed, all)")
) -> RemoveResponse:
    """Clear items from the queue by status.

    Args:
        status: Which items to clear (completed, failed, or all)

    Returns:
        RemoveResponse with count of items removed
    """
    capture_queue = _get_queue()
    items = capture_queue.get_all()

    if status == "completed":
        count = capture_queue.clear_completed()
    elif status == "failed":
        to_remove = [item for item in items if item.status == QueueStatus.FAILED]
        count = 0
        for item in to_remove:
            if capture_queue.remove(str(item.id)):
                count += 1
    elif status == "all":
        count = 0
        for item in items:
            if capture_queue.remove(str(item.id)):
                count += 1
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: completed, failed, all"
        )

    return RemoveResponse(message=f"Cleared {count} items", removed=count > 0)

"""Queue persistence - manages capture queue with JSON storage."""

import json
from pathlib import Path
from typing import Optional

from src.models.queue import QueueItem, QueueStatus


class CaptureQueue:
    """Persistent queue for capture items.

    Manages a persistent queue of capture items stored in a JSON file.
    Provides methods to add, retrieve, update, and remove items from the queue.
    All modifications are immediately persisted to disk.
    """

    def __init__(self, queue_path: Path) -> None:
        """Initialize the queue with a file path.

        Args:
            queue_path: Path to the JSON file for storing queue items
        """
        self._path = queue_path
        self._items: dict[str, QueueItem] = {}
        self._load()

    def _load(self) -> None:
        """Load queue from disk.

        If the file doesn't exist, initializes an empty queue.
        If the file is corrupted or invalid, raises an exception.
        """
        if not self._path.exists():
            self._items = {}
            return

        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._items = {
                    item_id: QueueItem.model_validate(item_data)
                    for item_id, item_data in data.items()
                }
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse queue file: {e}") from e
        except Exception as e:
            raise ValueError(f"Failed to load queue: {e}") from e

    def _save(self) -> None:
        """Save queue to disk.

        Creates parent directories if they don't exist.
        Writes all items to the JSON file in a human-readable format.
        """
        self._path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            item_id: item.model_dump(mode="json")
            for item_id, item in self._items.items()
        }

        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def add(self, item: QueueItem) -> None:
        """Add an item to the queue.

        Args:
            item: The queue item to add
        """
        self._items[str(item.id)] = item
        self._save()

    def get_pending(self) -> list[QueueItem]:
        """Get all items with PENDING or FAILED status.

        Returns items that are ready to be processed or retried.
        Items are returned in the order they were created (oldest first).

        Returns:
            List of pending/failed queue items sorted by created_at
        """
        pending_items = [
            item for item in self._items.values()
            if item.status in (QueueStatus.PENDING, QueueStatus.FAILED)
        ]
        return sorted(pending_items, key=lambda x: x.created_at)

    def get_by_id(self, item_id: str) -> Optional[QueueItem]:
        """Get a queue item by its ID.

        Args:
            item_id: The unique identifier of the item

        Returns:
            The queue item if found, None otherwise
        """
        return self._items.get(item_id)

    def update(self, item: QueueItem) -> None:
        """Update an existing item in the queue.

        Args:
            item: The queue item with updated data

        Raises:
            KeyError: If the item doesn't exist in the queue
        """
        item_id = str(item.id)
        if item_id not in self._items:
            raise KeyError(f"Item with id {item_id} not found in queue")

        self._items[item_id] = item
        self._save()

    def remove(self, item_id: str) -> bool:
        """Remove an item from the queue.

        Args:
            item_id: The unique identifier of the item to remove

        Returns:
            True if the item was removed, False if it didn't exist
        """
        if item_id in self._items:
            del self._items[item_id]
            self._save()
            return True
        return False

    def get_all(self) -> list[QueueItem]:
        """Get all items in the queue.

        Returns:
            List of all queue items sorted by created_at
        """
        return sorted(self._items.values(), key=lambda x: x.created_at)

    def clear_completed(self) -> int:
        """Remove all completed items from the queue.

        Returns:
            Number of items removed
        """
        completed_ids = [
            item_id for item_id, item in self._items.items()
            if item.status == QueueStatus.COMPLETED
        ]

        for item_id in completed_ids:
            del self._items[item_id]

        if completed_ids:
            self._save()

        return len(completed_ids)

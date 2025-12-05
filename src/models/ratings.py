"""Rating and analytics models for tracking AI model performance."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import json
from pathlib import Path


@dataclass
class NoteRating:
    """A single note rating record for analytics.

    Captures all relevant metadata about a note's AI generation
    and the user's quality assessment.
    """
    # Identification
    note_path: str  # Relative path in vault
    note_title: str
    source_url: str

    # User rating
    user_rating: int  # 1-5 stars
    rated_at: datetime

    # Content info
    content_type: str  # article, video, repo, news, walkthrough, printable
    tags: list[str]

    # AI model info - summary task
    summary_backend: str  # claude, openrouter
    summary_model: str  # Full model ID
    summary_temperature: Optional[float] = None
    summary_max_tokens: Optional[int] = None

    # AI model info - tags task
    tags_backend: str = ""
    tags_model: str = ""
    tags_temperature: Optional[float] = None
    tags_max_tokens: Optional[int] = None

    # Token/cost metrics
    summary_input_tokens: int = 0
    summary_output_tokens: int = 0
    tags_input_tokens: int = 0
    tags_output_tokens: int = 0
    total_cost_usd: float = 0.0

    # Timestamps
    captured_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "note_path": self.note_path,
            "note_title": self.note_title,
            "source_url": self.source_url,
            "user_rating": self.user_rating,
            "rated_at": self.rated_at.isoformat(),
            "content_type": self.content_type,
            "tags": self.tags,
            "summary_backend": self.summary_backend,
            "summary_model": self.summary_model,
            "summary_temperature": self.summary_temperature,
            "summary_max_tokens": self.summary_max_tokens,
            "tags_backend": self.tags_backend,
            "tags_model": self.tags_model,
            "tags_temperature": self.tags_temperature,
            "tags_max_tokens": self.tags_max_tokens,
            "summary_input_tokens": self.summary_input_tokens,
            "summary_output_tokens": self.summary_output_tokens,
            "tags_input_tokens": self.tags_input_tokens,
            "tags_output_tokens": self.tags_output_tokens,
            "total_cost_usd": self.total_cost_usd,
            "captured_at": self.captured_at.isoformat() if self.captured_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NoteRating":
        """Create from dictionary."""
        return cls(
            note_path=data["note_path"],
            note_title=data["note_title"],
            source_url=data["source_url"],
            user_rating=data["user_rating"],
            rated_at=datetime.fromisoformat(data["rated_at"]),
            content_type=data["content_type"],
            tags=data.get("tags", []),
            summary_backend=data.get("summary_backend", ""),
            summary_model=data.get("summary_model", ""),
            summary_temperature=data.get("summary_temperature"),
            summary_max_tokens=data.get("summary_max_tokens"),
            tags_backend=data.get("tags_backend", ""),
            tags_model=data.get("tags_model", ""),
            tags_temperature=data.get("tags_temperature"),
            tags_max_tokens=data.get("tags_max_tokens"),
            summary_input_tokens=data.get("summary_input_tokens", 0),
            summary_output_tokens=data.get("summary_output_tokens", 0),
            tags_input_tokens=data.get("tags_input_tokens", 0),
            tags_output_tokens=data.get("tags_output_tokens", 0),
            total_cost_usd=data.get("total_cost_usd", 0.0),
            captured_at=datetime.fromisoformat(data["captured_at"]) if data.get("captured_at") else None,
        )


@dataclass
class ModelStats:
    """Aggregated statistics for a model across all rated notes."""
    model_id: str
    backend: str
    task_type: str  # summary, tags

    # Rating stats
    total_ratings: int = 0
    average_rating: float = 0.0
    rating_distribution: dict[int, int] = field(default_factory=lambda: {1: 0, 2: 0, 3: 0, 4: 0, 5: 0})

    # Cost stats
    total_cost_usd: float = 0.0
    average_cost_per_note: float = 0.0

    # Token stats
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    average_output_tokens: float = 0.0

    # Content type breakdown
    ratings_by_content_type: dict[str, list[int]] = field(default_factory=dict)

    def add_rating(self, rating: int, content_type: str, cost: float, input_tokens: int, output_tokens: int) -> None:
        """Add a rating to the stats."""
        self.total_ratings += 1
        self.rating_distribution[rating] = self.rating_distribution.get(rating, 0) + 1

        # Recalculate average
        total = sum(r * count for r, count in self.rating_distribution.items())
        self.average_rating = total / self.total_ratings if self.total_ratings > 0 else 0

        # Cost tracking
        self.total_cost_usd += cost
        self.average_cost_per_note = self.total_cost_usd / self.total_ratings

        # Token tracking
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.average_output_tokens = self.total_output_tokens / self.total_ratings

        # Content type tracking
        if content_type not in self.ratings_by_content_type:
            self.ratings_by_content_type[content_type] = []
        self.ratings_by_content_type[content_type].append(rating)


class RatingsDatabase:
    """Simple JSON-based ratings database.

    Stores all ratings in a JSON file in the vault's .claudsidian folder.
    Provides methods for querying and analyzing ratings.
    """

    def __init__(self, db_path: Path):
        """Initialize database.

        Args:
            db_path: Path to the ratings JSON file
        """
        self.db_path = db_path
        self._ratings: list[NoteRating] = []
        self._load()

    def _load(self) -> None:
        """Load ratings from file."""
        if self.db_path.exists():
            try:
                data = json.loads(self.db_path.read_text(encoding="utf-8"))
                self._ratings = [NoteRating.from_dict(r) for r in data.get("ratings", [])]
            except (json.JSONDecodeError, KeyError):
                self._ratings = []
        else:
            self._ratings = []

    def _save(self) -> None:
        """Save ratings to file."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": 1,
            "updated_at": datetime.now().isoformat(),
            "ratings": [r.to_dict() for r in self._ratings]
        }
        self.db_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def add_rating(self, rating: NoteRating) -> None:
        """Add a rating to the database."""
        # Check for duplicate (same note_path)
        self._ratings = [r for r in self._ratings if r.note_path != rating.note_path]
        self._ratings.append(rating)
        self._save()

    def get_all_ratings(self) -> list[NoteRating]:
        """Get all ratings."""
        return self._ratings.copy()

    def get_ratings_by_model(self, model_id: str, task_type: str = "summary") -> list[NoteRating]:
        """Get ratings for a specific model.

        Args:
            model_id: Model identifier
            task_type: Either 'summary' or 'tags'
        """
        if task_type == "summary":
            return [r for r in self._ratings if r.summary_model == model_id]
        else:
            return [r for r in self._ratings if r.tags_model == model_id]

    def get_model_stats(self) -> dict[str, ModelStats]:
        """Calculate statistics for all models.

        Returns:
            Dict mapping "model_id:task_type" to ModelStats
        """
        stats: dict[str, ModelStats] = {}

        for rating in self._ratings:
            # Summary model stats
            summary_key = f"{rating.summary_model}:summary"
            if summary_key not in stats:
                stats[summary_key] = ModelStats(
                    model_id=rating.summary_model,
                    backend=rating.summary_backend,
                    task_type="summary"
                )
            stats[summary_key].add_rating(
                rating=rating.user_rating,
                content_type=rating.content_type,
                cost=rating.total_cost_usd * 0.8,  # Estimate 80% of cost is summary
                input_tokens=rating.summary_input_tokens,
                output_tokens=rating.summary_output_tokens
            )

            # Tags model stats
            if rating.tags_model:
                tags_key = f"{rating.tags_model}:tags"
                if tags_key not in stats:
                    stats[tags_key] = ModelStats(
                        model_id=rating.tags_model,
                        backend=rating.tags_backend,
                        task_type="tags"
                    )
                stats[tags_key].add_rating(
                    rating=rating.user_rating,
                    content_type=rating.content_type,
                    cost=rating.total_cost_usd * 0.2,  # Estimate 20% of cost is tags
                    input_tokens=rating.tags_input_tokens,
                    output_tokens=rating.tags_output_tokens
                )

        return stats

    def get_quality_report(self) -> str:
        """Generate a human-readable quality report."""
        stats = self.get_model_stats()

        if not stats:
            return "No ratings collected yet."

        lines = ["# Model Quality Report", ""]

        # Sort by average rating (descending)
        sorted_stats = sorted(
            stats.values(),
            key=lambda s: (s.task_type, -s.average_rating)
        )

        current_task = None
        for s in sorted_stats:
            if s.task_type != current_task:
                current_task = s.task_type
                lines.append(f"## {current_task.title()} Models")
                lines.append("")

            stars = "★" * int(s.average_rating) + "☆" * (5 - int(s.average_rating))
            lines.append(f"### {s.model_id}")
            lines.append(f"- Rating: {stars} ({s.average_rating:.2f}/5 from {s.total_ratings} notes)")
            lines.append(f"- Cost: ${s.total_cost_usd:.4f} total (${s.average_cost_per_note:.4f}/note)")
            lines.append(f"- Tokens: {s.average_output_tokens:.0f} avg output")

            # Rating distribution
            dist_str = " | ".join(f"{r}★:{c}" for r, c in sorted(s.rating_distribution.items()) if c > 0)
            lines.append(f"- Distribution: {dist_str}")

            # Content type breakdown
            if s.ratings_by_content_type:
                ct_lines = []
                for ct, ratings in s.ratings_by_content_type.items():
                    avg = sum(ratings) / len(ratings) if ratings else 0
                    ct_lines.append(f"{ct}: {avg:.1f}")
                lines.append(f"- By type: {', '.join(ct_lines)}")

            lines.append("")

        return "\n".join(lines)

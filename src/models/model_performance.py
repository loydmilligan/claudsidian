"""Model performance tracking database.

Tracks historical performance metrics for AI models including:
- Quality scores across multiple dimensions
- Cost per token
- Response times
- OPUS efficiency metric

The OPUS metric is defined as: (avg_quality / 5) / avg_cost
Higher is better - represents quality-adjusted cost efficiency.
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class QualityScores:
    """Multi-dimensional quality scores for a capture.

    Each score is 0-5 where 5 is perfect.
    Scores are designed to be objective and verifiable against gold standards.
    """
    # Core content quality
    accuracy: float = 0.0  # Factual correctness vs gold standard
    completeness: float = 0.0  # Coverage of key points/steps
    structure: float = 0.0  # Organization, formatting, sections
    conciseness: float = 0.0  # Appropriate length, no fluff

    # Optional dimension scores (may not apply to all content types)
    code_quality: Optional[float] = None  # For technical content
    step_coverage: Optional[float] = None  # For walkthroughs (X of Y steps)

    @property
    def average(self) -> float:
        """Calculate average of non-None scores."""
        scores = [self.accuracy, self.completeness, self.structure, self.conciseness]
        if self.code_quality is not None:
            scores.append(self.code_quality)
        if self.step_coverage is not None:
            scores.append(self.step_coverage)
        return sum(scores) / len(scores) if scores else 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary, excluding None values."""
        result = {
            "accuracy": self.accuracy,
            "completeness": self.completeness,
            "structure": self.structure,
            "conciseness": self.conciseness,
        }
        if self.code_quality is not None:
            result["code_quality"] = self.code_quality
        if self.step_coverage is not None:
            result["step_coverage"] = self.step_coverage
        result["average"] = self.average
        return result


@dataclass
class CapturePerformance:
    """Performance record for a single capture."""
    # Identification
    capture_id: str
    timestamp: str  # ISO format
    fixture_name: str
    content_type: str
    url: str

    # Model info
    summary_model: str
    tags_model: str

    # Performance metrics
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    time_seconds: float = 0.0

    # Quality scores
    quality: Optional[QualityScores] = None
    quality_notes: str = ""  # Explanation of scores

    # Success flag
    success: bool = True
    error: Optional[str] = None


@dataclass
class ModelStats:
    """Aggregated statistics for a model."""
    model_id: str
    capture_count: int = 0
    success_count: int = 0

    # Token stats
    total_input_tokens: int = 0
    total_output_tokens: int = 0

    # Cost stats
    total_cost_usd: float = 0.0

    # Time stats
    total_time_seconds: float = 0.0

    # Quality stats (only from scored captures)
    scored_count: int = 0
    total_accuracy: float = 0.0
    total_completeness: float = 0.0
    total_structure: float = 0.0
    total_conciseness: float = 0.0

    @property
    def avg_cost_per_call(self) -> float:
        """Average cost per API call."""
        return self.total_cost_usd / self.capture_count if self.capture_count > 0 else 0.0

    @property
    def avg_time_seconds(self) -> float:
        """Average response time."""
        return self.total_time_seconds / self.capture_count if self.capture_count > 0 else 0.0

    @property
    def avg_quality(self) -> float:
        """Average quality score across all dimensions."""
        if self.scored_count == 0:
            return 0.0
        total = (self.total_accuracy + self.total_completeness +
                 self.total_structure + self.total_conciseness)
        return total / (self.scored_count * 4)

    @property
    def opus(self) -> float:
        """OPUS efficiency metric: (quality/5) / avg_cost.

        Represents quality-adjusted cost efficiency.
        Higher is better. A score of 1.0 means perfect quality at $1/call.
        """
        if self.avg_cost_per_call == 0:
            # Free models get infinite OPUS (capped at 1000 for display)
            return 1000.0 if self.avg_quality > 0 else 0.0
        return (self.avg_quality / 5.0) / self.avg_cost_per_call

    @property
    def cost_per_1k_input_tokens(self) -> float:
        """Cost per 1000 input tokens."""
        if self.total_input_tokens == 0:
            return 0.0
        return (self.total_cost_usd / self.total_input_tokens) * 1000

    @property
    def cost_per_1k_output_tokens(self) -> float:
        """Cost per 1000 output tokens."""
        if self.total_output_tokens == 0:
            return 0.0
        return (self.total_cost_usd / self.total_output_tokens) * 1000

    def to_dict(self) -> dict:
        """Convert to dictionary with computed properties."""
        return {
            "model_id": self.model_id,
            "capture_count": self.capture_count,
            "success_count": self.success_count,
            "success_rate": self.success_count / self.capture_count if self.capture_count > 0 else 0.0,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost_usd": self.total_cost_usd,
            "avg_cost_per_call": self.avg_cost_per_call,
            "total_time_seconds": self.total_time_seconds,
            "avg_time_seconds": self.avg_time_seconds,
            "scored_count": self.scored_count,
            "avg_quality": self.avg_quality,
            "opus": self.opus,
            "cost_per_1k_input": self.cost_per_1k_input_tokens,
            "cost_per_1k_output": self.cost_per_1k_output_tokens,
        }


class ModelPerformanceDB:
    """Database for tracking model performance over time.

    Stores capture-level records and provides aggregated statistics.
    Data is persisted to a JSON file in the vault's .claudsidian folder.
    """

    def __init__(self, db_path: Path):
        """Initialize the database.

        Args:
            db_path: Path to the JSON database file
        """
        self._db_path = db_path
        self._captures: list[dict] = []
        self._load()

    def _load(self) -> None:
        """Load database from disk."""
        if self._db_path.exists():
            try:
                with open(self._db_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._captures = data.get("captures", [])
                logger.info(f"Loaded {len(self._captures)} performance records")
            except Exception as e:
                logger.error(f"Failed to load performance DB: {e}")
                self._captures = []
        else:
            self._captures = []

    def _save(self) -> None:
        """Save database to disk."""
        try:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._db_path, "w", encoding="utf-8") as f:
                json.dump({
                    "version": 1,
                    "updated": datetime.now().isoformat(),
                    "captures": self._captures
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save performance DB: {e}")

    def add_capture(self, perf: CapturePerformance) -> None:
        """Add a capture performance record.

        Args:
            perf: Performance record to add
        """
        record = {
            "capture_id": perf.capture_id,
            "timestamp": perf.timestamp,
            "fixture_name": perf.fixture_name,
            "content_type": perf.content_type,
            "url": perf.url,
            "summary_model": perf.summary_model,
            "tags_model": perf.tags_model,
            "input_tokens": perf.input_tokens,
            "output_tokens": perf.output_tokens,
            "cost_usd": perf.cost_usd,
            "time_seconds": perf.time_seconds,
            "success": perf.success,
            "error": perf.error,
        }

        if perf.quality:
            record["quality"] = perf.quality.to_dict()
            record["quality_notes"] = perf.quality_notes

        self._captures.append(record)
        self._save()
        logger.debug(f"Added performance record for {perf.summary_model}")

    def get_model_stats(self, model_id: str) -> ModelStats:
        """Get aggregated statistics for a specific model.

        Args:
            model_id: The model identifier to get stats for

        Returns:
            ModelStats with aggregated performance data
        """
        stats = ModelStats(model_id=model_id)

        for capture in self._captures:
            # Check if this model was used for summary or tags
            if capture.get("summary_model") != model_id:
                continue

            stats.capture_count += 1
            if capture.get("success", False):
                stats.success_count += 1

            stats.total_input_tokens += capture.get("input_tokens", 0)
            stats.total_output_tokens += capture.get("output_tokens", 0)
            stats.total_cost_usd += capture.get("cost_usd", 0.0)
            stats.total_time_seconds += capture.get("time_seconds", 0.0)

            # Add quality scores if present
            quality = capture.get("quality")
            if quality:
                stats.scored_count += 1
                stats.total_accuracy += quality.get("accuracy", 0.0)
                stats.total_completeness += quality.get("completeness", 0.0)
                stats.total_structure += quality.get("structure", 0.0)
                stats.total_conciseness += quality.get("conciseness", 0.0)

        return stats

    def get_all_model_stats(self) -> list[ModelStats]:
        """Get statistics for all models in the database.

        Returns:
            List of ModelStats, sorted by OPUS score descending
        """
        # Collect unique model IDs
        model_ids = set()
        for capture in self._captures:
            if capture.get("summary_model"):
                model_ids.add(capture["summary_model"])

        # Get stats for each model
        stats_list = [self.get_model_stats(model_id) for model_id in model_ids]

        # Sort by OPUS score (higher is better)
        stats_list.sort(key=lambda s: s.opus, reverse=True)

        return stats_list

    def get_recent_captures(self, limit: int = 50) -> list[dict]:
        """Get most recent capture records.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of capture records, newest first
        """
        sorted_captures = sorted(
            self._captures,
            key=lambda c: c.get("timestamp", ""),
            reverse=True
        )
        return sorted_captures[:limit]

    @property
    def total_captures(self) -> int:
        """Total number of captures recorded."""
        return len(self._captures)

    @property
    def total_cost(self) -> float:
        """Total cost across all captures."""
        return sum(c.get("cost_usd", 0.0) for c in self._captures)

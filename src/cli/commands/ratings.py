"""Ratings command - process user ratings and generate quality reports."""

import sys
from datetime import datetime
from pathlib import Path

import click
import yaml

from src.core.config import config_exists, load_config
from src.models.ratings import NoteRating, RatingsDatabase
from src.models.model_performance import ModelPerformanceDB

# Exit codes
EXIT_SUCCESS = 0
EXIT_ERROR = 1


def parse_frontmatter(content: str) -> dict | None:
    """Parse YAML frontmatter from markdown content."""
    if not content.startswith("---"):
        return None

    parts = content.split("---", 2)
    if len(parts) < 3:
        return None

    try:
        return yaml.safe_load(parts[1].strip())
    except yaml.YAMLError:
        return None


@click.group()
def ratings():
    """Manage note ratings and quality analytics.

    Process user ratings from notes and generate quality reports
    to track AI model performance over time.
    """
    pass


@ratings.command("process")
@click.option("--dry-run", is_flag=True, help="Show what would be processed without saving")
def process_ratings(dry_run: bool) -> None:
    """Process unprocessed ratings from vault notes.

    Scans all notes for user_rating values where rating_processed is false,
    extracts the rating data, and stores it in the ratings database.

    After processing, marks each note's rating_processed as true.
    """
    if not config_exists():
        click.echo(click.style("Error: ", fg="red") + "No configuration found.")
        sys.exit(EXIT_ERROR)

    try:
        config = load_config()
        if config is None:
            click.echo(click.style("Error: ", fg="red") + "Failed to load config")
            sys.exit(EXIT_ERROR)
    except Exception as e:
        click.echo(click.style("Error: ", fg="red") + f"Config error: {e}")
        sys.exit(EXIT_ERROR)

    vault_path = Path(config.vault_path)
    db_path = vault_path / ".claudsidian" / "ratings.json"
    db = RatingsDatabase(db_path)

    # Find all notes with unprocessed ratings
    unprocessed: list[tuple[Path, dict, str]] = []

    click.echo("Scanning vault for unprocessed ratings...")

    for md_file in vault_path.rglob("*.md"):
        # Skip hidden folders and test notes
        if any(part.startswith(".") for part in md_file.parts):
            continue

        try:
            content = md_file.read_text(encoding="utf-8")
            frontmatter = parse_frontmatter(content)

            if not frontmatter:
                continue

            # Check for unprocessed rating
            user_rating = frontmatter.get("user_rating")
            rating_processed = frontmatter.get("rating_processed", False)

            if user_rating is not None and not rating_processed:
                unprocessed.append((md_file, frontmatter, content))

        except (OSError, UnicodeDecodeError):
            continue

    if not unprocessed:
        click.echo(click.style("No unprocessed ratings found.", fg="yellow"))
        sys.exit(EXIT_SUCCESS)

    click.echo(f"Found {len(unprocessed)} notes with unprocessed ratings:")

    processed_count = 0
    for note_path, fm, content in unprocessed:
        relative_path = str(note_path.relative_to(vault_path))
        rating = fm.get("user_rating")
        title = note_path.stem

        click.echo(f"  {click.style(str(rating) + '★', fg='yellow')} {title}")

        if dry_run:
            continue

        # Extract AI metadata
        ai_meta = fm.get("ai", {})
        summary_meta = ai_meta.get("summary", {})
        tags_meta = ai_meta.get("tags", {})

        # Create rating record
        note_rating = NoteRating(
            note_path=relative_path,
            note_title=title,
            source_url=str(fm.get("source", "")),
            user_rating=rating,
            rated_at=datetime.now(),
            content_type=fm.get("type", "article"),
            tags=fm.get("tags", []),
            summary_backend=summary_meta.get("backend", ""),
            summary_model=summary_meta.get("model", ""),
            summary_temperature=summary_meta.get("temperature"),
            summary_max_tokens=summary_meta.get("max_tokens"),
            tags_backend=tags_meta.get("backend", ""),
            tags_model=tags_meta.get("model", ""),
            tags_temperature=tags_meta.get("temperature"),
            tags_max_tokens=tags_meta.get("max_tokens"),
            captured_at=datetime.fromisoformat(fm["captured"]) if fm.get("captured") else None,
        )

        # Add to database
        db.add_rating(note_rating)

        # Update note to mark as processed
        updated_content = content.replace(
            "rating_processed: false",
            "rating_processed: true"
        )

        # Handle case where rating_processed might not exist
        if "rating_processed:" not in updated_content:
            # Add it after user_rating
            updated_content = updated_content.replace(
                f"user_rating: {rating}",
                f"user_rating: {rating}\nrating_processed: true"
            )

        note_path.write_text(updated_content, encoding="utf-8")
        processed_count += 1

    if dry_run:
        click.echo(click.style("\nDry run - no changes made.", fg="cyan"))
    else:
        click.echo(click.style(f"\nProcessed {processed_count} ratings.", fg="green"))


@ratings.command("report")
@click.option("--output", "-o", type=click.Path(), help="Output file for report")
def generate_report(output: str | None) -> None:
    """Generate a quality report from collected ratings."""
    if not config_exists():
        click.echo(click.style("Error: ", fg="red") + "No configuration found.")
        sys.exit(EXIT_ERROR)

    try:
        config = load_config()
        if config is None:
            click.echo(click.style("Error: ", fg="red") + "Failed to load config")
            sys.exit(EXIT_ERROR)
    except Exception as e:
        click.echo(click.style("Error: ", fg="red") + f"Config error: {e}")
        sys.exit(EXIT_ERROR)

    vault_path = Path(config.vault_path)
    db_path = vault_path / ".claudsidian" / "ratings.json"
    db = RatingsDatabase(db_path)

    report = db.get_quality_report()

    if output:
        output_path = Path(output)
        output_path.write_text(report, encoding="utf-8")
        click.echo(f"Report written to {output_path}")
    else:
        click.echo(report)


@ratings.command("stats")
def show_stats() -> None:
    """Show summary statistics for all models."""
    if not config_exists():
        click.echo(click.style("Error: ", fg="red") + "No configuration found.")
        sys.exit(EXIT_ERROR)

    try:
        config = load_config()
        if config is None:
            click.echo(click.style("Error: ", fg="red") + "Failed to load config")
            sys.exit(EXIT_ERROR)
    except Exception as e:
        click.echo(click.style("Error: ", fg="red") + f"Config error: {e}")
        sys.exit(EXIT_ERROR)

    vault_path = Path(config.vault_path)
    db_path = vault_path / ".claudsidian" / "ratings.json"
    db = RatingsDatabase(db_path)

    all_ratings = db.get_all_ratings()
    stats = db.get_model_stats()

    click.echo(click.style("\nRatings Database Stats", fg="cyan", bold=True))
    click.echo(f"  Total ratings: {len(all_ratings)}")

    if not stats:
        click.echo("  No model stats available yet.")
        return

    click.echo()

    # Summary models table
    click.echo(click.style("Summary Models:", bold=True))
    click.echo(f"  {'Model':<40} {'Avg':<6} {'Count':<6} {'Cost':<10}")
    click.echo("  " + "-" * 65)

    for key, s in sorted(stats.items()):
        if s.task_type == "summary":
            stars = "★" * int(s.average_rating)
            click.echo(
                f"  {s.model_id:<40} "
                f"{s.average_rating:.2f}  "
                f"{s.total_ratings:<6} "
                f"${s.average_cost_per_note:.4f}"
            )

    click.echo()

    # Tags models table
    click.echo(click.style("Tags Models:", bold=True))
    click.echo(f"  {'Model':<40} {'Avg':<6} {'Count':<6} {'Cost':<10}")
    click.echo("  " + "-" * 65)

    for key, s in sorted(stats.items()):
        if s.task_type == "tags":
            click.echo(
                f"  {s.model_id:<40} "
                f"{s.average_rating:.2f}  "
                f"{s.total_ratings:<6} "
                f"${s.average_cost_per_note:.4f}"
            )


@ratings.command("list")
@click.option("--limit", "-n", default=20, help="Number of ratings to show")
@click.option("--model", "-m", help="Filter by model ID")
def list_ratings(limit: int, model: str | None) -> None:
    """List recent ratings."""
    if not config_exists():
        click.echo(click.style("Error: ", fg="red") + "No configuration found.")
        sys.exit(EXIT_ERROR)

    try:
        config = load_config()
        if config is None:
            click.echo(click.style("Error: ", fg="red") + "Failed to load config")
            sys.exit(EXIT_ERROR)
    except Exception as e:
        click.echo(click.style("Error: ", fg="red") + f"Config error: {e}")
        sys.exit(EXIT_ERROR)

    vault_path = Path(config.vault_path)
    db_path = vault_path / ".claudsidian" / "ratings.json"
    db = RatingsDatabase(db_path)

    ratings_list = db.get_all_ratings()

    if model:
        ratings_list = [r for r in ratings_list if model in r.summary_model or model in r.tags_model]

    # Sort by rated_at descending
    ratings_list.sort(key=lambda r: r.rated_at, reverse=True)
    ratings_list = ratings_list[:limit]

    if not ratings_list:
        click.echo("No ratings found.")
        return

    click.echo(click.style(f"\nRecent Ratings ({len(ratings_list)}):", bold=True))
    click.echo(f"  {'Rating':<8} {'Title':<35} {'Model':<25} {'Type':<10}")
    click.echo("  " + "-" * 80)

    for r in ratings_list:
        stars = "★" * r.user_rating + "☆" * (5 - r.user_rating)
        title = r.note_title[:33] + ".." if len(r.note_title) > 35 else r.note_title
        model_short = r.summary_model.split("/")[-1][:23] if "/" in r.summary_model else r.summary_model[:23]

        click.echo(f"  {stars:<8} {title:<35} {model_short:<25} {r.content_type:<10}")


@ratings.command("performance")
@click.option("--model", "-m", help="Filter by model ID")
def show_performance(model: str | None) -> None:
    """Show model performance metrics from all captures.

    Displays cost, speed, and usage statistics for each model used.
    This data is automatically collected during captures.
    """
    if not config_exists():
        click.echo(click.style("Error: ", fg="red") + "No configuration found.")
        sys.exit(EXIT_ERROR)

    try:
        config = load_config()
        if config is None:
            click.echo(click.style("Error: ", fg="red") + "Failed to load config")
            sys.exit(EXIT_ERROR)
    except Exception as e:
        click.echo(click.style("Error: ", fg="red") + f"Config error: {e}")
        sys.exit(EXIT_ERROR)

    vault_path = Path(config.vault_path)
    db_path = vault_path / ".claudsidian" / "model_performance.json"
    db = ModelPerformanceDB(db_path)

    if model:
        # Show stats for specific model
        stats = db.get_model_stats(model)
        if stats.capture_count == 0:
            click.echo(f"No captures found for model: {model}")
            return

        click.echo(click.style(f"\nPerformance Stats: {model}", fg="cyan", bold=True))
        click.echo(f"  Captures: {stats.capture_count} ({stats.success_count} successful)")
        click.echo(f"  Total Cost: ${stats.total_cost_usd:.4f}")
        click.echo(f"  Avg Cost/Capture: ${stats.avg_cost_per_call:.4f}")
        click.echo(f"  Avg Time: {stats.avg_time_seconds:.2f}s")
        click.echo(f"  Total Tokens: {stats.total_input_tokens:,} in / {stats.total_output_tokens:,} out")
        if stats.scored_count > 0:
            click.echo(f"  Avg Quality: {stats.avg_quality:.2f}/5 ({stats.scored_count} scored)")
            click.echo(f"  OPUS Score: {stats.opus:.2f}")
        return

    # Show all models
    all_stats = db.get_all_model_stats()

    if not all_stats:
        click.echo("No performance data collected yet.")
        click.echo("Performance is tracked automatically when you capture URLs.")
        return

    click.echo(click.style("\nModel Performance Summary", fg="cyan", bold=True))
    click.echo(f"  Total Captures: {db.total_captures}")
    click.echo(f"  Total Spend: ${db.total_cost:.4f}")
    click.echo()

    # Header
    click.echo(f"  {'Model':<35} {'Captures':<10} {'Avg Cost':<12} {'Avg Time':<10} {'OPUS':<8}")
    click.echo("  " + "-" * 80)

    for s in all_stats:
        model_short = s.model_id.split("/")[-1][:33] if "/" in s.model_id else s.model_id[:33]
        opus_str = f"{s.opus:.1f}" if s.opus < 1000 else "∞"

        click.echo(
            f"  {model_short:<35} "
            f"{s.capture_count:<10} "
            f"${s.avg_cost_per_call:<11.4f} "
            f"{s.avg_time_seconds:<9.1f}s "
            f"{opus_str:<8}"
        )

    click.echo()
    click.echo("OPUS = (quality/5) / cost - higher is better")


@ratings.command("recent")
@click.option("--limit", "-n", default=10, help="Number of captures to show")
def show_recent_captures(limit: int) -> None:
    """Show recent capture performance data."""
    if not config_exists():
        click.echo(click.style("Error: ", fg="red") + "No configuration found.")
        sys.exit(EXIT_ERROR)

    try:
        config = load_config()
        if config is None:
            click.echo(click.style("Error: ", fg="red") + "Failed to load config")
            sys.exit(EXIT_ERROR)
    except Exception as e:
        click.echo(click.style("Error: ", fg="red") + f"Config error: {e}")
        sys.exit(EXIT_ERROR)

    vault_path = Path(config.vault_path)
    db_path = vault_path / ".claudsidian" / "model_performance.json"
    db = ModelPerformanceDB(db_path)

    recent = db.get_recent_captures(limit)

    if not recent:
        click.echo("No capture data yet.")
        return

    click.echo(click.style(f"\nRecent Captures ({len(recent)}):", bold=True))
    click.echo(f"  {'Time':<12} {'Title':<30} {'Model':<20} {'Cost':<10} {'Time':<8}")
    click.echo("  " + "-" * 85)

    for c in recent:
        # Parse timestamp
        ts = c.get("timestamp", "")[:16].replace("T", " ")
        title = c.get("fixture_name", "")[:28]
        if len(c.get("fixture_name", "")) > 28:
            title += ".."
        model = c.get("summary_model", "unknown").split("/")[-1][:18]
        cost = c.get("cost_usd", 0)
        time_s = c.get("time_seconds", 0)
        success = "✓" if c.get("success") else "✗"

        click.echo(
            f"  {ts:<12} "
            f"{title:<30} "
            f"{model:<20} "
            f"${cost:<9.4f} "
            f"{time_s:<6.1f}s {success}"
        )

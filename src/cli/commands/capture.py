"""Capture command - capture a URL and create a note."""

import asyncio
import sys
from datetime import datetime

import click

from src.core.config import config_exists, load_config
from src.core.capture import CaptureService, CaptureResult
from src.models.capture import CaptureRequest, CaptureSource, ForceType


# Exit codes
EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_INVALID_ARGS = 2
EXIT_DUPLICATE = 3
EXIT_QUEUED = 4

# Valid content types
VALID_TYPES = ["article", "video", "repo", "news", "walkthrough", "printable"]


@click.command()
@click.argument("url")
@click.option("--type", "-t", "force_type", type=click.Choice(VALID_TYPES), help="Force content type")
@click.option("--async", "-a", "run_async", is_flag=True, help="Return immediately, process in background")
@click.option("--quiet", "-q", is_flag=True, help="Suppress output except errors")
def capture(url: str, force_type: str | None, run_async: bool, quiet: bool) -> None:
    """Capture a URL and create a note in the vault.

    Examples:
        claudsidian capture https://example.com/article
        claudsidian capture https://youtube.com/watch?v=xxx -t video
        claudsidian capture https://github.com/user/repo --quiet
    """
    # Validate config
    if not config_exists():
        click.echo(click.style("✗ Error: ", fg="red") + "No configuration found.")
        click.echo("Run 'claudsidian config init' to set up configuration.")
        sys.exit(EXIT_ERROR)

    # Validate URL (basic check)
    if not url.startswith(("http://", "https://")):
        click.echo(click.style("✗ Error: ", fg="red") + "Invalid URL. Must start with http:// or https://")
        sys.exit(EXIT_INVALID_ARGS)

    # Load config
    try:
        config = load_config()
        if config is None:
            click.echo(click.style("✗ Error: ", fg="red") + "Failed to load configuration.")
            sys.exit(EXIT_ERROR)
    except Exception as e:
        click.echo(click.style("✗ Error: ", fg="red") + f"Failed to load config: {e}")
        sys.exit(EXIT_ERROR)

    if run_async:
        if not quiet:
            click.echo(click.style("⚠ Warning: ", fg="yellow") + "Async mode not yet implemented.")

    # Create capture request
    request = CaptureRequest(
        url=url,
        source=CaptureSource.CLI,
        timestamp=datetime.now(),
        force_type=ForceType(force_type) if force_type else None,
    )

    # Run capture
    result = asyncio.run(_do_capture(config, request))

    # Handle result
    _handle_result(result, quiet)


async def _do_capture(config, request: CaptureRequest) -> CaptureResult:
    """Execute the capture operation."""
    service = CaptureService(config)
    try:
        return await service.capture(request)
    finally:
        await service.close()


def _handle_result(result: CaptureResult, quiet: bool) -> None:
    """Handle capture result and set exit code."""
    if result.is_duplicate:
        if not quiet:
            click.echo(click.style("⚠ ", fg="yellow") + f"Note already exists: {result.existing_note}")
        sys.exit(EXIT_DUPLICATE)

    if result.queued:
        if not quiet:
            click.echo(click.style("⚠ ", fg="yellow") + f"Queued for retry: {result.queue_id}")
            click.echo(f"  Reason: {result.error}")
        sys.exit(EXIT_QUEUED)

    if not result.success:
        click.echo(click.style("✗ Error: ", fg="red") + (result.error or "Unknown error"))
        sys.exit(EXIT_ERROR)

    # Success
    if not quiet:
        click.echo(click.style("✓ ", fg="green") + f"Captured: {result.title}")
        click.echo(f"  Type: {result.content_type}")
        click.echo(f"  Path: {result.note_path}")
        if result.tags:
            click.echo(f"  Tags: {', '.join(result.tags)}")

    sys.exit(EXIT_SUCCESS)

"""Watch command for inbox file monitoring.

This module provides the `claudsidian watch` command which monitors an inbox
file for URLs and automatically captures them.

Usage:
    claudsidian watch                    # Watch default inbox.md in vault
    claudsidian watch --file inbox.md    # Watch specific file
    claudsidian watch --daemon           # Run as background daemon
"""

import asyncio
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import click

from src.core.config import config_exists, load_config
from src.core.inbox import InboxProcessor, ProcessingResult


@click.command()
@click.option(
    '--file', '-f',
    type=click.Path(),
    help='Path to inbox file (default: inbox.md in vault root)'
)
@click.option(
    '--daemon', '-d',
    is_flag=True,
    default=False,
    help='Run as background daemon (suppress interactive output)'
)
@click.option(
    '--once',
    is_flag=True,
    default=False,
    help='Process inbox once and exit (do not watch for changes)'
)
@click.option(
    '--quiet', '-q',
    is_flag=True,
    default=False,
    help='Suppress output except errors'
)
def watch(
    file: Optional[str],
    daemon: bool,
    once: bool,
    quiet: bool
) -> None:
    """Watch inbox file and automatically capture URLs.

    Monitors an inbox markdown file for URLs and processes them through
    the capture pipeline. Successfully captured URLs are removed from
    the inbox file.

    The inbox file can contain URLs in various formats:
    - Plain URLs on their own line
    - Markdown links [text](url)
    - URLs in bullet points

    Examples:

        # Watch default inbox.md in vault
        claudsidian watch

        # Watch a specific file
        claudsidian watch --file ~/notes/inbox.md

        # Process once and exit
        claudsidian watch --once

        # Run as daemon (background)
        claudsidian watch --daemon
    """
    # Check configuration
    if not config_exists():
        click.secho(
            "Error: Claudsidian is not configured. Run 'claudsidian config --init' first.",
            fg='red',
            err=True
        )
        sys.exit(1)

    try:
        config = load_config()
    except Exception as e:
        click.secho(f"Error loading configuration: {e}", fg='red', err=True)
        sys.exit(1)

    # Determine inbox path
    if file:
        inbox_path = Path(file).expanduser().resolve()
    else:
        # Default to inbox.md in vault root
        inbox_path = Path(config.vault_path) / "inbox.md"

    # Output handler
    def on_result(result: ProcessingResult) -> None:
        """Handle processing result output."""
        if quiet and result.success:
            return

        timestamp = result.timestamp.strftime("%H:%M:%S")

        if result.success:
            click.secho(
                f"[{timestamp}] ✓ Captured: {result.entry.url}",
                fg='green'
            )
            if result.note_path:
                click.echo(f"           → {result.note_path}")
        else:
            click.secho(
                f"[{timestamp}] ✗ Failed: {result.entry.url}",
                fg='red'
            )
            if result.error:
                click.echo(f"           Error: {result.error}")

    # Create processor
    processor = InboxProcessor(
        config=config,
        inbox_path=inbox_path,
        on_result=None if daemon else on_result
    )

    if not quiet and not daemon:
        click.echo(f"Inbox file: {inbox_path}")

    if once:
        # Process once and exit
        if not quiet:
            click.echo("Processing inbox (one-time)...")

        results = asyncio.run(processor.process_once())

        if not quiet:
            success_count = sum(1 for r in results if r.success)
            fail_count = len(results) - success_count
            click.echo(f"\nProcessed {len(results)} URLs: {success_count} succeeded, {fail_count} failed")

        sys.exit(0 if all(r.success for r in results) else 1)

    # Set up signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        if not quiet:
            click.echo("\nStopping inbox watcher...")
        processor.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run continuously
    if not quiet and not daemon:
        click.echo("Watching for changes (Ctrl+C to stop)...")
        click.echo("─" * 50)

    try:
        asyncio.run(processor.run())
    except KeyboardInterrupt:
        pass

    if not quiet:
        click.echo("Inbox watcher stopped.")


def format_result_line(result: ProcessingResult) -> str:
    """Format a processing result as a single line for logging.

    Args:
        result: The processing result

    Returns:
        Formatted string
    """
    timestamp = result.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    status = "OK" if result.success else "FAIL"

    line = f"[{timestamp}] [{status}] {result.entry.url}"

    if result.success and result.note_path:
        line += f" -> {result.note_path}"
    elif result.error:
        line += f" - {result.error}"

    return line

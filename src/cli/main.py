"""Claudsidian CLI - AI-powered knowledge capture for Obsidian."""

import click

from src.cli.commands.capture import capture
from src.cli.commands.config import config
from src.cli.commands.serve import serve
from src.cli.commands.status import status


@click.group()
@click.version_option(version="0.1.0", prog_name="claudsidian")
def cli() -> None:
    """Claudsidian - AI-powered knowledge capture for Obsidian."""
    pass


# Add capture command to CLI
cli.add_command(capture)

# Add config command group to CLI
cli.add_command(config)

# Add status command to CLI
cli.add_command(status)

# Add serve command to CLI
cli.add_command(serve)


@cli.group()
def queue() -> None:
    """Manage capture queue.

    View and manage the queue of pending, failed, and completed captures.
    The queue allows for asynchronous processing and retry of failed captures.
    """
    pass


@queue.command("list")
@click.option("--status", "-s", type=click.Choice(["pending", "processing", "completed", "failed"]),
              default=None, help="Filter by status")
def queue_list(status: str | None) -> None:
    """List items in the capture queue.

    Shows all queued captures with their current status. Can be filtered
    by status to show only pending, processing, completed, or failed items.

    Examples:
        claudsidian queue list
        claudsidian queue list --status failed
    """
    if status:
        click.echo(f"Queue items with status: {status}")
    else:
        click.echo("All queue items:")
    # TODO: Implement queue list logic


@queue.command("retry")
@click.argument("item_id", required=False)
@click.option("--all", "retry_all", is_flag=True, help="Retry all failed items")
def queue_retry(item_id: str | None, retry_all: bool) -> None:
    """Retry failed queue items.

    Retry processing of a specific failed capture by ID, or retry all
    failed captures using the --all flag.

    Examples:
        claudsidian queue retry abc123
        claudsidian queue retry --all
    """
    if retry_all:
        click.echo("Retrying all failed items...")
    elif item_id:
        click.echo(f"Retrying item: {item_id}")
    else:
        click.echo("Error: Specify an item ID or use --all flag")
    # TODO: Implement queue retry logic


@queue.command("clear")
@click.option("--status", "-s", type=click.Choice(["completed", "failed", "all"]),
              default="completed", help="Clear items with this status")
@click.confirmation_option(prompt="Are you sure you want to clear queue items?")
def queue_clear(status: str) -> None:
    """Clear items from the queue.

    Remove completed or failed items from the queue. Use with caution as
    this operation cannot be undone.

    Examples:
        claudsidian queue clear
        claudsidian queue clear --status failed
        claudsidian queue clear --status all
    """
    click.echo(f"Clearing {status} items...")
    # TODO: Implement queue clear logic




if __name__ == "__main__":
    cli()

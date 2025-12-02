"""Claudsidian CLI - AI-powered knowledge capture for Obsidian."""

import logging
import sys
from pathlib import Path

import click

from src.cli.commands.capture import capture
from src.cli.commands.config import config
from src.cli.commands.serve import serve
from src.cli.commands.status import status
from src.cli.commands.watch import watch
from src.core.config import config_exists, load_config
from src.core.queue import CaptureQueue
from src.models.queue import QueueStatus


def setup_logging(verbose: bool = False, debug: bool = False) -> None:
    """Configure logging based on verbosity level.

    Args:
        verbose: Enable verbose output (INFO level)
        debug: Enable debug output (DEBUG level)
    """
    if debug:
        level = logging.DEBUG
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    elif verbose:
        level = logging.INFO
        log_format = "%(levelname)s - %(name)s - %(message)s"
    else:
        level = logging.WARNING
        log_format = "%(levelname)s - %(message)s"

    logging.basicConfig(
        level=level,
        format=log_format,
        stream=sys.stderr,
    )

    # Suppress noisy third-party loggers unless in debug mode
    if not debug:
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("openai").setLevel(logging.WARNING)
        logging.getLogger("anthropic").setLevel(logging.WARNING)


# Use context object to pass options to subcommands
class Context:
    """Context object for passing options to subcommands."""

    def __init__(self) -> None:
        self.verbose: bool = False
        self.debug: bool = False


pass_context = click.make_pass_decorator(Context, ensure=True)


@click.group()
@click.version_option(version="0.1.0", prog_name="claudsidian")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--debug", "-d", is_flag=True, help="Enable debug output (very verbose)")
@click.pass_context
def cli(ctx: click.Context, verbose: bool, debug: bool) -> None:
    """Claudsidian - AI-powered knowledge capture for Obsidian."""
    ctx.ensure_object(Context)
    ctx.obj.verbose = verbose
    ctx.obj.debug = debug
    setup_logging(verbose=verbose, debug=debug)


# Add capture command to CLI
cli.add_command(capture)

# Add config command group to CLI
cli.add_command(config)

# Add status command to CLI
cli.add_command(status)

# Add serve command to CLI
cli.add_command(serve)

# Add watch command to CLI
cli.add_command(watch)


def _get_queue() -> CaptureQueue:
    """Get the capture queue.

    Returns:
        CaptureQueue instance

    Raises:
        SystemExit: If configuration is not set up
    """
    if not config_exists():
        click.secho("Error: Configuration not found. Run 'claudsidian config init' first.", fg="red")
        sys.exit(1)

    cfg = load_config()
    if cfg is None:
        click.secho("Error: Failed to load configuration.", fg="red")
        sys.exit(1)

    queue_path = Path(cfg.vault_path) / ".claudsidian" / "queue.json"
    return CaptureQueue(queue_path)


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
    capture_queue = _get_queue()
    items = capture_queue.get_all()

    # Filter by status if specified
    if status:
        status_enum = QueueStatus(status)
        items = [item for item in items if item.status == status_enum]

    if not items:
        if status:
            click.echo(f"No items with status '{status}' in queue.")
        else:
            click.echo("Queue is empty.")
        return

    # Display items
    click.echo(f"\nQueue items ({len(items)}):\n")
    click.echo(f"{'ID':<36} {'Status':<12} {'URL':<50} {'Attempts'}")
    click.echo("-" * 110)

    for item in items:
        url_display = str(item.request.url)[:50]
        if len(str(item.request.url)) > 50:
            url_display = url_display[:47] + "..."

        status_color = {
            QueueStatus.PENDING: "yellow",
            QueueStatus.PROCESSING: "blue",
            QueueStatus.COMPLETED: "green",
            QueueStatus.FAILED: "red",
        }.get(item.status, "white")

        click.echo(
            f"{str(item.id):<36} "
            f"{click.style(item.status.value, fg=status_color):<22} "
            f"{url_display:<50} "
            f"{item.attempts}"
        )

        if item.error:
            click.echo(f"  └─ Error: {item.error[:70]}...")


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
    capture_queue = _get_queue()

    if retry_all:
        # Get all failed items
        items = [item for item in capture_queue.get_all() if item.status == QueueStatus.FAILED]

        if not items:
            click.echo("No failed items to retry.")
            return

        count = 0
        for item in items:
            item.status = QueueStatus.PENDING
            capture_queue.update(item)
            count += 1

        click.secho(f"Reset {count} items to pending status.", fg="green")
        click.echo("Run 'claudsidian serve' to process them.")

    elif item_id:
        item = capture_queue.get_by_id(item_id)

        if not item:
            click.secho(f"Error: Item with ID '{item_id}' not found.", fg="red")
            sys.exit(1)

        if item.status == QueueStatus.COMPLETED:
            click.echo("Item already completed.")
            return

        item.status = QueueStatus.PENDING
        capture_queue.update(item)
        click.secho(f"Reset item {item_id} to pending status.", fg="green")

    else:
        click.secho("Error: Specify an item ID or use --all flag.", fg="red")
        sys.exit(1)


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
    else:  # all
        count = 0
        for item in items:
            if capture_queue.remove(str(item.id)):
                count += 1

    click.secho(f"Cleared {count} items from queue.", fg="green")


@queue.command("remove")
@click.argument("item_id")
def queue_remove(item_id: str) -> None:
    """Remove a specific item from the queue.

    Examples:
        claudsidian queue remove abc123
    """
    capture_queue = _get_queue()

    if capture_queue.remove(item_id):
        click.secho(f"Removed item {item_id} from queue.", fg="green")
    else:
        click.secho(f"Error: Item with ID '{item_id}' not found.", fg="red")
        sys.exit(1)




if __name__ == "__main__":
    cli()

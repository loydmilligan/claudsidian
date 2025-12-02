"""Status command - show system status."""

from pathlib import Path

import click
import httpx

from src.core.config import config_exists, get_config_path, load_config
from src.core.queue import CaptureQueue
from src.models.queue import QueueStatus


@click.command()
def status() -> None:
    """Show Claudsidian system status."""
    click.echo("Claudsidian Status")
    click.echo("=" * 18)
    click.echo()

    _show_config_status()
    _show_server_status()
    _show_queue_status()


def _show_config_status() -> None:
    """Display configuration status."""
    click.echo("Configuration:")

    # Check if config exists
    if not config_exists():
        click.echo("  " + click.style("\u2717", fg="red") + " Config file: not found")
        click.echo()
        return

    config_path = get_config_path()
    click.echo(f"  " + click.style("\u2713", fg="green") + f" Config file: {config_path}")

    # Load and check config details
    try:
        config = load_config()
        if config is None:
            click.echo("  " + click.style("\u2717", fg="red") + " Failed to load config")
            click.echo()
            return

        # Check vault path
        vault_path = Path(config.vault_path)
        if vault_path.exists():
            click.echo(f"  " + click.style("\u2713", fg="green") + f" Vault path: {config.vault_path}")
        else:
            click.echo(f"  " + click.style("\u26a0", fg="yellow") + f" Vault path: {config.vault_path} (not found)")

        # Check API keys
        if config.openrouter_api_key:
            click.echo("  " + click.style("\u2713", fg="green") + " OpenRouter API key: configured")
        else:
            click.echo("  " + click.style("\u2717", fg="red") + " OpenRouter API key: not configured")

        if config.claude_api_key:
            click.echo("  " + click.style("\u2713", fg="green") + " Claude API key: configured")
        else:
            click.echo("  " + click.style("\u2717", fg="red") + " Claude API key: not configured")

    except Exception as e:
        click.echo("  " + click.style("\u2717", fg="red") + f" Error loading config: {e}")

    click.echo()


def _show_server_status() -> None:
    """Display server status."""
    click.echo("Server:")

    # Try to connect to the server
    try:
        config = load_config()
        port = config.server_port if config else 8765

        response = httpx.get(f"http://localhost:{port}/status", timeout=2.0)
        if response.status_code == 200:
            click.echo(f"  " + click.style("\u2713", fg="green") + f" HTTP server: running (port {port})")
        else:
            click.echo(f"  " + click.style("\u2717", fg="red") + f" HTTP server: responding with status {response.status_code} (port {port})")
    except httpx.ConnectError:
        port = config.server_port if config and load_config() else 8765
        click.echo(f"  " + click.style("\u2717", fg="red") + f" HTTP server: not running (port {port})")
    except httpx.TimeoutException:
        port = config.server_port if config and load_config() else 8765
        click.echo(f"  " + click.style("\u26a0", fg="yellow") + f" HTTP server: timeout (port {port})")
    except Exception as e:
        click.echo(f"  " + click.style("\u2717", fg="red") + f" HTTP server: error ({e})")

    click.echo()


def _show_queue_status() -> None:
    """Display queue status."""
    click.echo("Queue:")

    # Get queue path
    queue_path = Path.home() / ".config" / "claudsidian" / "queue.json"

    # Check if queue file exists
    if not queue_path.exists():
        click.echo("  " + click.style("\u2022", fg="white") + " Pending: 0")
        click.echo("  " + click.style("\u2022", fg="white") + " Failed: 0")
        click.echo("  " + click.style("\u2022", fg="white") + " Completed: 0")
        click.echo()
        return

    # Load queue and count items by status
    try:
        queue = CaptureQueue(queue_path)
        all_items = queue.get_all()

        pending_count = sum(1 for item in all_items if item.status == QueueStatus.PENDING)
        failed_count = sum(1 for item in all_items if item.status == QueueStatus.FAILED)
        completed_count = sum(1 for item in all_items if item.status == QueueStatus.COMPLETED)

        click.echo(f"  " + click.style("\u2022", fg="white") + f" Pending: {pending_count}")
        click.echo(f"  " + click.style("\u2022", fg="white") + f" Failed: {failed_count}")
        click.echo(f"  " + click.style("\u2022", fg="white") + f" Completed: {completed_count}")

    except Exception as e:
        click.echo("  " + click.style("\u2717", fg="red") + f" Error loading queue: {e}")

    click.echo()

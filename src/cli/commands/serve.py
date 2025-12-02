"""Serve command - start the HTTP server."""

from pathlib import Path

import click

from src.core.config import config_exists, load_config
from src.server.app import run_server


@click.command()
@click.option("--port", "-p", default=8765, help="Port to listen on")
@click.option("--host", default="127.0.0.1", help="Host to bind to (use 0.0.0.0 for LAN access)")
@click.option("--daemon", "-d", is_flag=True, help="Run in background (not implemented)")
def serve(port: int, host: str, daemon: bool) -> None:
    """Start the Claudsidian HTTP server.

    The server provides the API for browser extension and other clients
    to submit URLs for capture.

    Examples:
        claudsidian serve                    # Start on localhost:8765
        claudsidian serve -p 9000            # Start on port 9000
        claudsidian serve --host 0.0.0.0     # Allow LAN connections
    """
    # Check configuration
    if not config_exists():
        click.echo(click.style("Error: ", fg="red") + "No configuration found.")
        click.echo("Run 'claudsidian config init' to set up configuration.")
        raise SystemExit(1)

    config = load_config()

    if config is None:
        click.echo(click.style("Error: ", fg="red") + "Failed to load configuration.")
        raise SystemExit(1)

    # Validate vault path
    if not config.vault_path:
        click.echo(click.style("Error: ", fg="red") + "Vault path not configured.")
        raise SystemExit(1)

    vault_path = Path(config.vault_path)
    if not vault_path.exists():
        click.echo(click.style("Warning: ", fg="yellow") + f"Vault path does not exist: {config.vault_path}")
        click.echo("Server will start but may not function correctly.")

    # Warn if no API keys configured
    if not config.claude_api_key and not config.openrouter_api_key:
        click.echo(click.style("Warning: ", fg="yellow") + "No API keys configured.")
        click.echo("AI features will not work without API keys.")
        click.echo()

    # Daemon mode warning
    if daemon:
        click.echo(click.style("Warning: ", fg="yellow") + "Daemon mode not yet implemented.")
        click.echo("Server will run in foreground.")
        click.echo()

    # Start server
    click.echo(f"Starting Claudsidian server at http://{host}:{port}")
    click.echo("Press Ctrl+C to stop")
    click.echo()

    try:
        run_server(host=host, port=port)
    except KeyboardInterrupt:
        click.echo("\nServer stopped.")

"""Configuration management CLI commands."""

import click
from pathlib import Path
from typing import Any, Dict

from src.core.config import load_config, save_config, config_exists, get_config_path
from src.models.config import Configuration, FolderConfig


@click.group()
def config() -> None:
    """Manage Claudsidian configuration."""
    pass


@config.command("show")
def show() -> None:
    """Display current configuration.

    Shows all current configuration settings including API keys (masked),
    vault location, template settings, and queue configuration.
    """
    if not config_exists():
        click.echo("Configuration not found.")
        click.echo(f"Run 'claudsidian config init' to set up your configuration.")
        click.echo(f"Config location: {get_config_path()}")
        return

    try:
        cfg = load_config()
        if cfg is None:
            click.echo("Error: Unable to load configuration.")
            return

        click.echo(click.style("Current Configuration:", bold=True, fg="green"))
        click.echo(f"Config file: {get_config_path()}")
        click.echo()

        # Display vault configuration
        click.echo(click.style("Vault Settings:", bold=True))
        click.echo(f"  vault_path: {cfg.vault_path}")
        click.echo(f"  inbox_file: {cfg.inbox_file}")
        click.echo()

        # Display API keys (masked)
        click.echo(click.style("API Keys:", bold=True))
        if cfg.claude_api_key:
            masked_key = cfg.claude_api_key[:8] + "..." + cfg.claude_api_key[-4:] if len(cfg.claude_api_key) > 12 else "***"
            click.echo(f"  claude_api_key: {masked_key}")
        else:
            click.echo("  claude_api_key: Not set")

        if cfg.openrouter_api_key:
            masked_key = cfg.openrouter_api_key[:8] + "..." + cfg.openrouter_api_key[-4:] if len(cfg.openrouter_api_key) > 12 else "***"
            click.echo(f"  openrouter_api_key: {masked_key}")
        else:
            click.echo("  openrouter_api_key: Not set")
        click.echo()

        # Display server configuration
        click.echo(click.style("Server Settings:", bold=True))
        click.echo(f"  server_port: {cfg.server_port}")
        click.echo()

        # Display folder mappings
        click.echo(click.style("Folder Mappings:", bold=True))
        click.echo(f"  folders.article: {cfg.folders.article}")
        click.echo(f"  folders.video: {cfg.folders.video}")
        click.echo(f"  folders.repo: {cfg.folders.repo}")
        click.echo(f"  folders.news: {cfg.folders.news}")
        click.echo(f"  folders.walkthrough: {cfg.folders.walkthrough}")
        click.echo(f"  folders.printable: {cfg.folders.printable}")

    except Exception as e:
        click.echo(click.style(f"Error loading configuration: {e}", fg="red"), err=True)


@config.command("set")
@click.argument("key")
@click.argument("value")
def set_value(key: str, value: str) -> None:
    """Set a configuration value.

    Update a single configuration key with a new value. Use dot notation
    for nested keys (e.g., 'folders.article', 'vault_path').

    Examples:
        claudsidian config set vault_path ~/Documents/MyVault
        claudsidian config set folders.article Learning
        claudsidian config set server_port 8080
    """
    if not config_exists():
        click.echo(click.style("Configuration not found.", fg="red"), err=True)
        click.echo("Run 'claudsidian config init' first.")
        return

    try:
        cfg = load_config()
        if cfg is None:
            click.echo(click.style("Error: Unable to load configuration.", fg="red"), err=True)
            return

        # Parse the key (support dot notation)
        key_parts = key.split(".")

        # Convert config to dict for manipulation
        config_dict = cfg.model_dump()

        # Navigate to the correct location and set the value
        if len(key_parts) == 1:
            # Top-level key
            if key_parts[0] not in config_dict:
                click.echo(click.style(f"Error: Invalid configuration key '{key}'", fg="red"), err=True)
                click.echo("Valid top-level keys: vault_path, claude_api_key, openrouter_api_key, server_port, inbox_file, folders")
                return

            # Type conversion for specific keys
            if key_parts[0] == "server_port":
                try:
                    value = int(value)
                except ValueError:
                    click.echo(click.style(f"Error: server_port must be an integer", fg="red"), err=True)
                    return

            config_dict[key_parts[0]] = value

        elif len(key_parts) == 2:
            # Nested key (currently only 'folders' is supported)
            if key_parts[0] != "folders":
                click.echo(click.style(f"Error: Invalid nested key '{key}'", fg="red"), err=True)
                click.echo("Valid nested keys start with 'folders.' (e.g., folders.article)")
                return

            if key_parts[1] not in config_dict["folders"]:
                click.echo(click.style(f"Error: Invalid folder key '{key_parts[1]}'", fg="red"), err=True)
                click.echo("Valid folder keys: article, video, repo, news, walkthrough, printable")
                return

            config_dict["folders"][key_parts[1]] = value
        else:
            click.echo(click.style(f"Error: Invalid key format '{key}'", fg="red"), err=True)
            click.echo("Use simple keys (e.g., 'vault_path') or dot notation (e.g., 'folders.article')")
            return

        # Validate and save the updated configuration
        try:
            updated_config = Configuration(**config_dict)
            save_config(updated_config)
            click.echo(click.style(f"Successfully set {key} = {value}", fg="green"))
        except ValueError as ve:
            click.echo(click.style(f"Validation error: {ve}", fg="red"), err=True)

    except Exception as e:
        click.echo(click.style(f"Error updating configuration: {e}", fg="red"), err=True)


@config.command("init")
def init() -> None:
    """Initialize configuration interactively.

    Runs an interactive setup wizard to configure Claudsidian for first use.
    Prompts for essential settings like Obsidian vault location, AI provider,
    and API keys.
    """
    click.echo(click.style("Claudsidian Configuration Setup", bold=True, fg="cyan"))
    click.echo()

    if config_exists():
        click.echo("Configuration file already exists.")
        if not click.confirm("Do you want to overwrite it?"):
            click.echo("Configuration unchanged.")
            return
        click.echo()

    # Prompt for vault path
    click.echo(click.style("Obsidian Vault:", bold=True))
    vault_path_input = click.prompt(
        "Enter the absolute path to your Obsidian vault",
        type=str
    )
    # Clean up the input
    vault_path_input = vault_path_input.strip().strip('"').strip("'")

    # Handle Windows paths in WSL - convert C:\... to /mnt/c/...
    if len(vault_path_input) >= 2 and vault_path_input[1] == ':':
        # Windows absolute path detected (e.g., C:\Users\...)
        drive_letter = vault_path_input[0].lower()
        rest_of_path = vault_path_input[2:].replace('\\', '/')
        vault_path = f"/mnt/{drive_letter}{rest_of_path}"
        click.echo(f"Converted Windows path to WSL: {vault_path}")
    else:
        # Unix path - normalize it
        vault_path = str(Path(vault_path_input).expanduser().resolve())

    # Verify the path exists
    if not Path(vault_path).is_dir():
        click.echo(click.style(f"Error: Directory does not exist: {vault_path}", fg="red"), err=True)
        return

    click.echo(f"Using vault path: {vault_path}")
    click.echo()

    # Prompt for API keys
    click.echo(click.style("API Keys:", bold=True))
    click.echo("You need at least one API key to use Claudsidian.")
    click.echo()

    claude_api_key = click.prompt(
        "Anthropic Claude API key (press Enter to skip)",
        default="",
        show_default=False,
        hide_input=True
    )
    claude_api_key = claude_api_key.strip() or None

    openrouter_api_key = click.prompt(
        "OpenRouter API key (press Enter to skip)",
        default="",
        show_default=False,
        hide_input=True
    )
    openrouter_api_key = openrouter_api_key.strip() or None

    # Validate that at least one API key is provided
    if not claude_api_key and not openrouter_api_key:
        click.echo(click.style("Error: At least one API key is required.", fg="red"), err=True)
        click.echo("Please run 'claudsidian config init' again and provide an API key.")
        return

    click.echo()

    # Optional: prompt for server port
    click.echo(click.style("Server Settings:", bold=True))
    server_port = click.prompt(
        "HTTP server port",
        default=8765,
        type=int
    )
    click.echo()

    # Optional: prompt for inbox file
    inbox_file = click.prompt(
        "Inbox file name",
        default="inbox.md"
    )
    click.echo()

    # Create configuration with default folder mappings
    try:
        config_dict: Dict[str, Any] = {
            "vault_path": vault_path,
            "server_port": server_port,
            "inbox_file": inbox_file,
        }

        if claude_api_key:
            config_dict["claude_api_key"] = claude_api_key

        if openrouter_api_key:
            config_dict["openrouter_api_key"] = openrouter_api_key

        cfg = Configuration(**config_dict)
        save_config(cfg)

        click.echo(click.style("Configuration saved successfully!", fg="green", bold=True))
        click.echo(f"Config location: {get_config_path()}")
        click.echo()
        click.echo("You can now use Claudsidian to capture content.")
        click.echo("Run 'claudsidian config show' to view your configuration.")
        click.echo("Run 'claudsidian config set KEY VALUE' to modify settings.")

    except ValueError as ve:
        click.echo(click.style(f"Configuration error: {ve}", fg="red"), err=True)
    except Exception as e:
        click.echo(click.style(f"Error saving configuration: {e}", fg="red"), err=True)

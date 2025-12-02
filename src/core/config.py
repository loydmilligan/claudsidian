"""Configuration management for Claudsidian.

This module provides functions to load, save, and manage the application configuration.
Configuration is stored as JSON in ~/.config/claudsidian/config.json
"""

import json
from pathlib import Path
from typing import Optional

from src.models.config import Configuration


def get_config_path() -> Path:
    """Get the path to the configuration file.

    Returns:
        Path to the configuration file at ~/.config/claudsidian/config.json
    """
    return Path.home() / ".config" / "claudsidian" / "config.json"


def load_config() -> Optional[Configuration]:
    """Load configuration from the JSON file.

    Returns:
        Configuration object if the file exists and is valid, None otherwise

    Raises:
        json.JSONDecodeError: If the config file contains invalid JSON
        ValidationError: If the config data doesn't match the Configuration schema
    """
    config_path = get_config_path()

    if not config_path.exists():
        return None

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)

        return Configuration(**config_data)
    except FileNotFoundError:
        return None


def save_config(config: Configuration) -> None:
    """Save configuration to the JSON file.

    Creates the configuration directory if it doesn't exist.

    Args:
        config: Configuration object to save

    Raises:
        OSError: If unable to create directories or write the file
    """
    config_path = get_config_path()

    # Create parent directories if they don't exist
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Serialize the configuration to JSON
    config_data = config.model_dump(mode='json')

    # Write to file with pretty formatting
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=2, ensure_ascii=False)


def config_exists() -> bool:
    """Check if the configuration file exists.

    Returns:
        True if the config file exists, False otherwise
    """
    return get_config_path().exists()

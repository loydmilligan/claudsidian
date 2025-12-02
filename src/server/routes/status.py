"""Status endpoint for server health and configuration."""

from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

from src.core.config import config_exists, load_config

router = APIRouter()


class APIStatus(BaseModel):
    """API key configuration status.

    Attributes:
        claude: Whether Claude API key is configured
        openrouter: Whether OpenRouter API key is configured
    """

    claude: bool
    openrouter: bool


class StatusResponseBody(BaseModel):
    """Server and configuration status response.

    Attributes:
        status: Overall status - "ok", "degraded", or "error"
        version: Server version string
        vault_path: Path to Obsidian vault if configured
        apis: API key configuration status
    """

    status: str
    version: str
    vault_path: str | None
    apis: APIStatus


@router.get("/status", response_model=StatusResponseBody)
async def get_status():
    """Get server and configuration status.

    Returns status based on configuration state:
    - "ok": Config exists, vault path valid, at least one API key configured
    - "degraded": Config exists but missing some settings
    - "error": No config or critical issues

    Returns:
        StatusResponseBody: Server status information
    """
    version = "0.1.0"

    # Check if configuration exists
    if not config_exists():
        return StatusResponseBody(
            status="error",
            version=version,
            vault_path=None,
            apis=APIStatus(claude=False, openrouter=False),
        )

    # Load configuration
    config = load_config()

    # Handle case where config file exists but is invalid
    if config is None:
        return StatusResponseBody(
            status="error",
            version=version,
            vault_path=None,
            apis=APIStatus(claude=False, openrouter=False),
        )

    # Check vault path validity
    vault_path_valid = False
    if config.vault_path:
        vault_path = Path(config.vault_path)
        vault_path_valid = vault_path.exists() and vault_path.is_dir()

    # Check API key configuration
    has_claude = bool(config.claude_api_key)
    has_openrouter = bool(config.openrouter_api_key)
    has_api_key = has_claude or has_openrouter

    # Determine overall status
    if vault_path_valid and has_api_key:
        status = "ok"
    elif not config.vault_path or not vault_path_valid or not has_api_key:
        status = "degraded"
    else:
        status = "error"

    return StatusResponseBody(
        status=status,
        version=version,
        vault_path=config.vault_path,
        apis=APIStatus(
            claude=has_claude,
            openrouter=has_openrouter,
        ),
    )

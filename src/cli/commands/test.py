"""Test command - verify API keys and configuration."""

import asyncio
import sys

import click

from src.core.config import config_exists, load_config


@click.command()
@click.option("--claude", "test_claude", is_flag=True, help="Test Claude API only")
@click.option("--openrouter", "test_openrouter", is_flag=True, help="Test OpenRouter API only")
def test(test_claude: bool, test_openrouter: bool) -> None:
    """Test API keys and configuration.

    Sends a simple request to each configured API to verify keys are valid.

    Examples:
        claudsidian test              # Test all configured APIs
        claudsidian test --claude     # Test Claude API only
        claudsidian test --openrouter # Test OpenRouter API only
    """
    if not config_exists():
        click.echo(click.style("Error: ", fg="red") + "No configuration found.")
        click.echo("Run 'claudsidian config init' first.")
        sys.exit(1)

    config = load_config()
    if config is None:
        click.echo(click.style("Error: ", fg="red") + "Failed to load configuration.")
        sys.exit(1)

    # Determine which APIs to test
    test_both = not test_claude and not test_openrouter

    results = asyncio.run(_run_tests(config, test_claude or test_both, test_openrouter or test_both))

    # Summary
    click.echo()
    if all(results.values()):
        click.echo(click.style("All tests passed!", fg="green", bold=True))
    else:
        failed = [k for k, v in results.items() if not v]
        click.echo(click.style(f"Failed: {', '.join(failed)}", fg="red", bold=True))
        sys.exit(1)


async def _run_tests(config, test_claude: bool, test_openrouter: bool) -> dict:
    """Run API tests."""
    results = {}

    if test_claude:
        click.echo(click.style("Testing Claude API...", bold=True))
        if not config.claude_api_key:
            click.echo("  " + click.style("SKIP", fg="yellow") + " - No API key configured")
            results["claude"] = True  # Not a failure, just not configured
        else:
            results["claude"] = await _test_claude(config.claude_api_key)

    if test_openrouter:
        click.echo(click.style("Testing OpenRouter API...", bold=True))
        if not config.openrouter_api_key:
            click.echo("  " + click.style("SKIP", fg="yellow") + " - No API key configured")
            results["openrouter"] = True  # Not a failure, just not configured
        else:
            results["openrouter"] = await _test_openrouter(config.openrouter_api_key)

    return results


async def _test_claude(api_key: str) -> bool:
    """Test Claude API connection."""
    from src.core.ai.claude import ClaudeClient, ClaudeAPIError

    try:
        client = ClaudeClient(api_key=api_key)
        response = await client.complete(
            prompt="Say 'API test successful' and nothing else.",
            max_tokens=20,
            temperature=0
        )
        click.echo("  " + click.style("OK", fg="green") + f" - Model: {client.default_model}")
        click.echo(f"  Response: {response.strip()}")
        return True
    except ClaudeAPIError as e:
        click.echo("  " + click.style("FAIL", fg="red") + f" - {e}")
        return False
    except Exception as e:
        click.echo("  " + click.style("FAIL", fg="red") + f" - Unexpected error: {e}")
        return False


async def _test_openrouter(api_key: str) -> bool:
    """Test OpenRouter API connection."""
    from src.core.ai.openrouter import OpenRouterClient, OpenRouterError

    try:
        client = OpenRouterClient(api_key=api_key)
        response = await client.complete(
            prompt="Say 'API test successful' and nothing else.",
            max_tokens=20,
            temperature=0
        )
        await client.close()
        click.echo("  " + click.style("OK", fg="green") + f" - Model: {client.model}")
        click.echo(f"  Response: {response.strip()}")
        return True
    except OpenRouterError as e:
        click.echo("  " + click.style("FAIL", fg="red") + f" - {e}")
        return False
    except Exception as e:
        click.echo("  " + click.style("FAIL", fg="red") + f" - Unexpected error: {e}")
        return False

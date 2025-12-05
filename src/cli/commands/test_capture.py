"""Test capture command - test captures with sample URLs and cleanup."""

import asyncio
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import click

from src.core.config import config_exists, load_config
from src.core.capture import CaptureService, CaptureResult, AIUsageMetrics
from src.models.capture import CaptureRequest, CaptureSource
from src.models.config import ModelConfig, Configuration

# Exit codes
EXIT_SUCCESS = 0
EXIT_ERROR = 1

# Valid content types
VALID_CONTENT_TYPES = ["article", "video", "repo", "news", "walkthrough", "printable"]

# Content types that work with standard HTTP extraction
STANDARD_CONTENT_TYPES = ["article", "video", "repo", "news", "walkthrough"]

# Content types that require Playwright browser automation
PLAYWRIGHT_CONTENT_TYPES = ["printable"]

# Default test fixtures file name
TEST_FIXTURES_FILE = "test-captures.md"


def load_fixtures_from_file(vault_path: Path) -> dict[str, list[dict[str, str]]]:
    """Load test fixtures from a markdown file in the vault.

    The file should have sections for each content type with URLs listed as
    markdown links or bare URLs.

    Example format for test-captures.md:
    ```
    # Test Captures

    ## article
    - [Paul Graham - Wealth](https://www.paulgraham.com/wealth.html) - Classic essay
    - https://example.com/another-article

    ## video
    - [Cool Video](https://youtube.com/watch?v=xxx) - Description here
    - https://youtube.com/watch?v=yyy

    ## repo
    - https://github.com/user/repo
    ```

    Args:
        vault_path: Path to the vault root

    Returns:
        Dictionary mapping content types to lists of fixture dicts
    """
    fixtures: dict[str, list[dict[str, str]]] = {ct: [] for ct in VALID_CONTENT_TYPES}

    test_file = vault_path / TEST_FIXTURES_FILE
    if not test_file.exists():
        return fixtures

    try:
        content = test_file.read_text(encoding="utf-8")
    except Exception:
        return fixtures

    current_type: str | None = None

    # Patterns for parsing
    # Match ## type headers
    section_pattern = re.compile(r"^##\s+(\w+)\s*$", re.IGNORECASE)
    # Match markdown links: [name](url) or [name](url) - description
    md_link_pattern = re.compile(
        r"[-*]\s*\[([^\]]+)\]\(([^)]+)\)(?:\s*[-–—]\s*(.+))?$"
    )
    # Match bare URLs: - https://...
    bare_url_pattern = re.compile(r"[-*]\s*(https?://\S+)")

    for line in content.splitlines():
        line = line.strip()

        # Check for section header
        section_match = section_pattern.match(line)
        if section_match:
            type_name = section_match.group(1).lower()
            if type_name in VALID_CONTENT_TYPES:
                current_type = type_name
            else:
                current_type = None
            continue

        # Skip if not in a valid section
        if not current_type:
            continue

        # Try to match markdown link
        md_match = md_link_pattern.match(line)
        if md_match:
            name = md_match.group(1).strip()
            url = md_match.group(2).strip()
            description = md_match.group(3).strip() if md_match.group(3) else ""
            fixtures[current_type].append({
                "url": url,
                "name": name,
                "description": description
            })
            continue

        # Try to match bare URL
        bare_match = bare_url_pattern.match(line)
        if bare_match:
            url = bare_match.group(1).strip()
            fixtures[current_type].append({
                "url": url,
                "name": "",  # No name for bare URLs
                "description": ""
            })

    return fixtures


def create_template_file(vault_path: Path) -> Path:
    """Create a template test-captures.md file in the vault.

    Args:
        vault_path: Path to the vault root

    Returns:
        Path to the created file
    """
    template = """# Test Captures

Add URLs below to test the capture system. Organize by content type.
Run `claudsidian test-capture run` to capture these URLs.

## article
- [Example Article](https://example.com/article) - Description here

## video
- [Example Video](https://www.youtube.com/watch?v=dQw4w9WgXcQ) - YouTube video

## repo
- https://github.com/anthropics/claude-code

## news
- https://news.ycombinator.com

## walkthrough
- https://docs.python.org/3/tutorial/

## printable
- https://www.thingiverse.com/thing:763622
"""
    test_file = vault_path / TEST_FIXTURES_FILE
    test_file.write_text(template, encoding="utf-8")
    return test_file


def get_fixtures(config: Configuration) -> dict[str, list[dict[str, str]]]:
    """Get test fixtures, loading from file if available.

    Args:
        config: Application configuration

    Returns:
        Dictionary of fixtures by content type
    """
    vault_path = Path(config.vault_path)
    return load_fixtures_from_file(vault_path)


def generate_html_report(
    results: list[dict[str, Any]],
    output_path: Path,
    cheap_mode: bool = False
) -> None:
    """Generate an HTML report of test capture results.

    Args:
        results: List of result dictionaries from test captures
        output_path: Path to write the HTML report
        cheap_mode: Whether cheap mode was used
    """
    # Calculate totals
    total_input_tokens = 0
    total_output_tokens = 0
    total_cost = 0.0
    success_count = 0
    failed_count = 0

    for r in results:
        if r.get('status') == 'success' and r.get('ai_metrics'):
            m = r['ai_metrics']
            total_input_tokens += m.total_input_tokens
            total_output_tokens += m.total_output_tokens
            total_cost += m.total_cost_usd
            success_count += 1
        elif r.get('status') == 'failed':
            failed_count += 1

    # Group results by content type
    by_type: dict[str, list[dict[str, Any]]] = {}
    for r in results:
        ctype = r.get('type', 'unknown')
        if ctype not in by_type:
            by_type[ctype] = []
        by_type[ctype].append(r)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Claudsidian Test Capture Report</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
            color: #333;
        }}
        h1 {{ color: #6b46c1; border-bottom: 3px solid #6b46c1; padding-bottom: 10px; }}
        h2 {{ color: #553c9a; margin-top: 30px; }}
        .summary-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .card h3 {{ margin: 0 0 10px 0; font-size: 14px; color: #666; text-transform: uppercase; }}
        .card .value {{ font-size: 28px; font-weight: bold; color: #333; }}
        .card .value.cost {{ color: #d69e2e; }}
        .card .value.success {{ color: #38a169; }}
        .card .value.failed {{ color: #e53e3e; }}
        .card .subtext {{ font-size: 12px; color: #888; margin-top: 5px; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin: 15px 0;
        }}
        th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #eee; }}
        th {{ background: #6b46c1; color: white; font-weight: 600; }}
        tr:hover {{ background: #f9f9f9; }}
        .status-success {{ color: #38a169; font-weight: bold; }}
        .status-failed {{ color: #e53e3e; font-weight: bold; }}
        .status-duplicate {{ color: #d69e2e; font-weight: bold; }}
        .status-skipped {{ color: #888; }}
        .model-tag {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-family: monospace;
        }}
        .model-claude {{ background: #fef3c7; color: #92400e; }}
        .model-openrouter {{ background: #d1fae5; color: #065f46; }}
        .cost {{ font-family: monospace; color: #d69e2e; }}
        .tokens {{ font-family: monospace; color: #666; font-size: 12px; }}
        .note-path {{ font-family: monospace; font-size: 12px; color: #666; }}
        .type-header {{ background: #f0f0f0; padding: 10px 15px; font-weight: bold; }}
        .mode-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
        }}
        .mode-cheap {{ background: #d1fae5; color: #065f46; }}
        .mode-default {{ background: #e9d8fd; color: #553c9a; }}
        footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #888; font-size: 12px; }}
    </style>
</head>
<body>
    <h1>Claudsidian Test Capture Report</h1>
    <p>Generated: {timestamp} &nbsp;
        <span class="mode-badge {'mode-cheap' if cheap_mode else 'mode-default'}">
            {'Cheap Mode (Haiku)' if cheap_mode else 'Default Mode (Claude + Haiku)'}
        </span>
    </p>

    <div class="summary-cards">
        <div class="card">
            <h3>Total Cost</h3>
            <div class="value cost">${total_cost:.4f}</div>
            <div class="subtext">Estimated USD</div>
        </div>
        <div class="card">
            <h3>Captures</h3>
            <div class="value success">{success_count}</div>
            <div class="subtext">{failed_count} failed</div>
        </div>
        <div class="card">
            <h3>Input Tokens</h3>
            <div class="value">{total_input_tokens:,}</div>
            <div class="subtext">Prompt tokens</div>
        </div>
        <div class="card">
            <h3>Output Tokens</h3>
            <div class="value">{total_output_tokens:,}</div>
            <div class="subtext">Completion tokens</div>
        </div>
    </div>

    <h2>Detailed Results</h2>
"""

    for ctype, type_results in by_type.items():
        html += f"""
    <h3 style="margin-top: 25px; color: #553c9a;">{ctype.upper()}</h3>
    <table>
        <tr>
            <th>Status</th>
            <th>Title / URL</th>
            <th>Summary Model</th>
            <th>Tags Model</th>
            <th>Tokens</th>
            <th>Cost</th>
        </tr>
"""
        for r in type_results:
            status = r.get('status', 'unknown')
            status_class = f"status-{status}"
            status_display = status.upper()

            name = r.get('name') or r.get('url', 'Unknown')
            url = r.get('url', '')
            note_path = r.get('note_path', '')

            # AI metrics
            m = r.get('ai_metrics')
            if m:
                summary_model = m.summary_model.split('/')[-1][:20]
                summary_class = "model-claude" if m.summary_backend == "claude" else "model-openrouter"
                tags_model = m.tags_model.split('/')[-1][:20]
                tags_class = "model-claude" if m.tags_backend == "claude" else "model-openrouter"
                tokens = f"{m.total_input_tokens:,} / {m.total_output_tokens:,}"
                cost = f"${m.total_cost_usd:.4f}"
            else:
                summary_model = "-"
                summary_class = ""
                tags_model = "-"
                tags_class = ""
                tokens = "-"
                cost = "-"

            error = r.get('error', '')
            if error:
                name = f"{name}<br><small style='color:#e53e3e'>{error[:50]}...</small>"

            html += f"""
        <tr>
            <td><span class="{status_class}">{status_display}</span></td>
            <td>
                <strong>{name}</strong>
                {f'<br><span class="note-path">{note_path}</span>' if note_path else ''}
            </td>
            <td><span class="model-tag {summary_class}">{summary_model}</span></td>
            <td><span class="model-tag {tags_class}">{tags_model}</span></td>
            <td class="tokens">{tokens}</td>
            <td class="cost">{cost}</td>
        </tr>
"""
        html += "    </table>\n"

    # Cost breakdown by model
    model_costs: dict[str, dict[str, float]] = {}
    for r in results:
        m = r.get('ai_metrics')
        if m:
            # Summary model
            if m.summary_model not in model_costs:
                model_costs[m.summary_model] = {'cost': 0.0, 'calls': 0}
            model_costs[m.summary_model]['cost'] += m.summary_cost_usd
            model_costs[m.summary_model]['calls'] += 1

            # Tags model
            if m.tags_model not in model_costs:
                model_costs[m.tags_model] = {'cost': 0.0, 'calls': 0}
            model_costs[m.tags_model]['cost'] += m.tags_cost_usd
            model_costs[m.tags_model]['calls'] += 1

    if model_costs:
        html += """
    <h2>Cost by Model</h2>
    <table>
        <tr>
            <th>Model</th>
            <th>Calls</th>
            <th>Total Cost</th>
            <th>Avg Cost/Call</th>
        </tr>
"""
        for model, data in sorted(model_costs.items(), key=lambda x: -x[1]['cost']):
            avg_cost = data['cost'] / data['calls'] if data['calls'] > 0 else 0
            model_short = model.split('/')[-1]
            html += f"""
        <tr>
            <td><code>{model_short}</code></td>
            <td>{data['calls']}</td>
            <td class="cost">${data['cost']:.4f}</td>
            <td class="cost">${avg_cost:.4f}</td>
        </tr>
"""
        html += "    </table>\n"

    html += f"""
    <footer>
        <p>Report generated by Claudsidian test-capture command</p>
    </footer>
</body>
</html>
"""

    output_path.write_text(html, encoding='utf-8')


@click.group()
def test_capture():
    """Test capture functionality with sample URLs.

    URLs are loaded from test-captures.md in your vault root.
    Run 'claudsidian test-capture init' to create the template file.
    """
    pass


@test_capture.command("init")
@click.option("--force", "-f", is_flag=True, help="Overwrite existing file")
def init_fixtures(force: bool) -> None:
    """Create test-captures.md template in the vault.

    Examples:
        claudsidian test-capture init
        claudsidian test-capture init --force
    """
    if not config_exists():
        click.echo(click.style("✗ Error: ", fg="red") + "No configuration found.")
        sys.exit(EXIT_ERROR)

    try:
        config = load_config()
        if config is None:
            click.echo(click.style("✗ Error: ", fg="red") + "Failed to load config")
            sys.exit(EXIT_ERROR)
    except Exception as e:
        click.echo(click.style("✗ Error: ", fg="red") + f"Config error: {e}")
        sys.exit(EXIT_ERROR)

    vault_path = Path(config.vault_path)
    test_file = vault_path / TEST_FIXTURES_FILE

    if test_file.exists() and not force:
        click.echo(click.style("⚠ ", fg="yellow") + f"File already exists: {TEST_FIXTURES_FILE}")
        click.echo("Use --force to overwrite")
        sys.exit(EXIT_ERROR)

    created_path = create_template_file(vault_path)
    click.echo(click.style("✓ ", fg="green") + f"Created: {created_path}")
    click.echo("\nEdit this file to add your test URLs, then run:")
    click.echo("  claudsidian test-capture list")
    click.echo("  claudsidian test-capture run")


@test_capture.command("list")
@click.option("--type", "-t", "content_type", help="Filter by content type")
def list_fixtures(content_type: str | None) -> None:
    """List available test fixtures from test-captures.md.

    Examples:
        claudsidian test-capture list
        claudsidian test-capture list --type article
    """
    if not config_exists():
        click.echo(click.style("✗ Error: ", fg="red") + "No configuration found.")
        sys.exit(EXIT_ERROR)

    try:
        config = load_config()
        if config is None:
            click.echo(click.style("✗ Error: ", fg="red") + "Failed to load config")
            sys.exit(EXIT_ERROR)
    except Exception as e:
        click.echo(click.style("✗ Error: ", fg="red") + f"Config error: {e}")
        sys.exit(EXIT_ERROR)

    fixtures = get_fixtures(config)

    if content_type and content_type not in VALID_CONTENT_TYPES:
        click.echo(click.style("✗ Error: ", fg="red") + f"Unknown type: {content_type}")
        click.echo(f"Valid types: {', '.join(VALID_CONTENT_TYPES)}")
        sys.exit(EXIT_ERROR)

    # Check if file exists
    vault_path = Path(config.vault_path)
    test_file = vault_path / TEST_FIXTURES_FILE
    if not test_file.exists():
        click.echo(click.style("⚠ ", fg="yellow") + f"No {TEST_FIXTURES_FILE} found in vault")
        click.echo("Run 'claudsidian test-capture init' to create it")
        sys.exit(EXIT_ERROR)

    types_to_show = [content_type] if content_type else VALID_CONTENT_TYPES
    total_count = 0

    for ctype in types_to_show:
        type_fixtures = fixtures.get(ctype, [])
        if type_fixtures:
            click.echo(click.style(f"\n{ctype.upper()}", fg="cyan", bold=True))
            for i, fixture in enumerate(type_fixtures, 1):
                # If name is different from URL, show both; otherwise just URL
                if fixture['name'] and fixture['name'] != fixture['url']:
                    click.echo(f"  {i}. {fixture['name']}")
                    click.echo(f"     {fixture['url']}")
                else:
                    click.echo(f"  {i}. {fixture['url']}")
                if fixture['description']:
                    click.echo(f"     {fixture['description']}")
                total_count += 1

    if total_count == 0:
        click.echo(click.style("⚠ ", fg="yellow") + "No fixtures found")
        click.echo(f"Add URLs to {TEST_FIXTURES_FILE} in your vault")
    else:
        click.echo(f"\n{total_count} fixture(s) found")


@test_capture.command("run")
@click.option("--type", "-t", "content_type", help="Only test this content type")
@click.option("--count", "-n", default=0, help="Max fixtures per type (0=all)")
@click.option("--cheap", "-c", is_flag=True, help="Use cheap mode (Haiku for all)")
@click.option("--dry-run", "-d", is_flag=True, help="Show what would be captured without doing it")
@click.option("--prefix", "-p", default="_TEST_", help="Prefix for test note titles")
def run_tests(
    content_type: str | None,
    count: int,
    cheap: bool,
    dry_run: bool,
    prefix: str
) -> None:
    """Run test captures with URLs from test-captures.md.

    Creates notes with a prefix (default: _TEST_) so they can be easily
    identified and cleaned up.

    Examples:
        claudsidian test-capture run
        claudsidian test-capture run --type article
        claudsidian test-capture run --cheap --dry-run
        claudsidian test-capture run --count 2
    """
    if not config_exists():
        click.echo(click.style("✗ Error: ", fg="red") + "No configuration found.")
        sys.exit(EXIT_ERROR)

    if content_type and content_type not in VALID_CONTENT_TYPES:
        click.echo(click.style("✗ Error: ", fg="red") + f"Unknown type: {content_type}")
        sys.exit(EXIT_ERROR)

    try:
        config = load_config()
        if config is None:
            click.echo(click.style("✗ Error: ", fg="red") + "Failed to load config")
            sys.exit(EXIT_ERROR)
    except Exception as e:
        click.echo(click.style("✗ Error: ", fg="red") + f"Config error: {e}")
        sys.exit(EXIT_ERROR)

    # Load fixtures from file
    fixtures = get_fixtures(config)

    # Check if file exists
    vault_path = Path(config.vault_path)
    test_file = vault_path / TEST_FIXTURES_FILE
    if not test_file.exists():
        click.echo(click.style("⚠ ", fg="yellow") + f"No {TEST_FIXTURES_FILE} found in vault")
        click.echo("Run 'claudsidian test-capture init' to create it")
        sys.exit(EXIT_ERROR)

    # Build model config
    model_config = ModelConfig(cheap_mode=True) if cheap else None

    types_to_test = [content_type] if content_type else VALID_CONTENT_TYPES

    # Count total fixtures
    total_tests = 0
    for ctype in types_to_test:
        type_fixtures = fixtures.get(ctype, [])
        if count > 0:
            type_fixtures = type_fixtures[:count]
        total_tests += len(type_fixtures)

    if total_tests == 0:
        click.echo(click.style("⚠ ", fg="yellow") + "No fixtures to run")
        click.echo(f"Add URLs to {TEST_FIXTURES_FILE} in your vault")
        sys.exit(EXIT_ERROR)

    results: list[dict[str, Any]] = []

    click.echo(click.style(f"\nRunning {total_tests} test capture(s)", fg="cyan", bold=True))
    click.echo(f"Source: {TEST_FIXTURES_FILE}")
    if cheap:
        click.echo(click.style("$ ", fg="yellow") + "Using cheap mode (Haiku for all)")
    if dry_run:
        click.echo(click.style("$ ", fg="yellow") + "Dry run - no captures will be made")
    click.echo(f"Note prefix: {prefix}")
    click.echo()

    for ctype in types_to_test:
        type_fixtures = fixtures.get(ctype, [])
        if count > 0:
            type_fixtures = type_fixtures[:count]

        for fixture in type_fixtures:
            click.echo(f"  [{ctype}] {fixture['name']}...")

            if dry_run:
                click.echo(click.style("    → ", fg="yellow") + "Would capture: " + fixture['url'])
                results.append({
                    "type": ctype,
                    "name": fixture['name'],
                    "status": "skipped",
                    "note_path": None
                })
                continue

            # Run the capture
            result = asyncio.run(_run_test_capture(
                config, fixture['url'], model_config, prefix
            ))

            if result.success:
                cost_str = ""
                if result.ai_metrics:
                    cost_str = f" (${result.ai_metrics.total_cost_usd:.4f})"
                click.echo(click.style("    ✓ ", fg="green") + f"Created: {result.note_path}{cost_str}")
                results.append({
                    "type": ctype,
                    "name": fixture['name'],
                    "url": fixture['url'],
                    "status": "success",
                    "note_path": result.note_path,
                    "ai_metrics": result.ai_metrics
                })
            elif result.is_duplicate:
                click.echo(click.style("    ⚠ ", fg="yellow") + f"Duplicate: {result.existing_note}")
                results.append({
                    "type": ctype,
                    "name": fixture['name'],
                    "url": fixture['url'],
                    "status": "duplicate",
                    "note_path": result.existing_note,
                    "ai_metrics": None
                })
            else:
                click.echo(click.style("    ✗ ", fg="red") + f"Failed: {result.error}")
                results.append({
                    "type": ctype,
                    "name": fixture['name'],
                    "url": fixture['url'],
                    "status": "failed",
                    "note_path": None,
                    "error": result.error,
                    "ai_metrics": None
                })

    # Summary
    click.echo()
    success_count = sum(1 for r in results if r['status'] == 'success')
    failed_count = sum(1 for r in results if r['status'] == 'failed')
    dup_count = sum(1 for r in results if r['status'] == 'duplicate')
    skipped_count = sum(1 for r in results if r['status'] == 'skipped')

    # Calculate total cost
    total_cost = sum(
        r['ai_metrics'].total_cost_usd
        for r in results
        if r.get('ai_metrics')
    )
    total_tokens = sum(
        r['ai_metrics'].total_input_tokens + r['ai_metrics'].total_output_tokens
        for r in results
        if r.get('ai_metrics')
    )

    click.echo(click.style("Summary:", bold=True))
    if success_count:
        click.echo(click.style(f"  ✓ Success: {success_count}", fg="green"))
    if failed_count:
        click.echo(click.style(f"  ✗ Failed: {failed_count}", fg="red"))
    if dup_count:
        click.echo(click.style(f"  ⚠ Duplicates: {dup_count}", fg="yellow"))
    if skipped_count:
        click.echo(click.style(f"  → Skipped: {skipped_count}", fg="yellow"))

    if total_cost > 0:
        click.echo()
        click.echo(click.style("Cost:", bold=True))
        click.echo(f"  Total: ${total_cost:.4f}")
        click.echo(f"  Tokens: {total_tokens:,}")
        if success_count > 0:
            click.echo(f"  Avg per capture: ${total_cost / success_count:.4f}")

    # Generate HTML report (skip for dry runs with no real results)
    if not dry_run and success_count > 0:
        report_path = vault_path / ".claudsidian" / "test-capture-report.html"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        generate_html_report(results, report_path, cheap_mode=cheap)
        click.echo()
        click.echo(click.style("Report:", bold=True))
        click.echo(f"  {report_path}")


@test_capture.command("cleanup")
@click.option("--prefix", "-p", default="_TEST_", help="Prefix of test notes to remove")
@click.option("--dry-run", "-d", is_flag=True, help="Show what would be deleted")
@click.option("--force", "-f", is_flag=True, help="Don't ask for confirmation")
def cleanup_tests(prefix: str, dry_run: bool, force: bool) -> None:
    """Remove test notes from the vault.

    Finds and removes notes that start with the test prefix.

    Examples:
        claudsidian test-capture cleanup
        claudsidian test-capture cleanup --dry-run
        claudsidian test-capture cleanup --prefix "_TEST_" --force
    """
    if not config_exists():
        click.echo(click.style("✗ Error: ", fg="red") + "No configuration found.")
        sys.exit(EXIT_ERROR)

    try:
        config = load_config()
        if config is None:
            click.echo(click.style("✗ Error: ", fg="red") + "Failed to load config")
            sys.exit(EXIT_ERROR)
    except Exception as e:
        click.echo(click.style("✗ Error: ", fg="red") + f"Config error: {e}")
        sys.exit(EXIT_ERROR)

    vault_path = Path(config.vault_path)

    # Find test notes
    test_notes: list[Path] = []
    for md_file in vault_path.rglob("*.md"):
        if md_file.name.startswith(prefix):
            test_notes.append(md_file)

    if not test_notes:
        click.echo(click.style("✓ ", fg="green") + f"No test notes found with prefix '{prefix}'")
        sys.exit(EXIT_SUCCESS)

    click.echo(click.style(f"Found {len(test_notes)} test notes:", fg="cyan"))
    for note in test_notes:
        relative = note.relative_to(vault_path)
        click.echo(f"  {relative}")

    if dry_run:
        click.echo(click.style("\n→ ", fg="yellow") + "Dry run - no files deleted")
        sys.exit(EXIT_SUCCESS)

    if not force:
        click.confirm("\nDelete these files?", abort=True)

    # Delete the files
    deleted = 0
    for note in test_notes:
        try:
            note.unlink()
            deleted += 1
        except Exception as e:
            click.echo(click.style("✗ ", fg="red") + f"Failed to delete {note.name}: {e}")

    click.echo(click.style(f"\n✓ ", fg="green") + f"Deleted {deleted} test notes")


@test_capture.command("revert")
@click.argument("note_path")
def revert_note(note_path: str) -> None:
    """Remove a specific note by path.

    Examples:
        claudsidian test-capture revert "Learning/_TEST_Some Article.md"
    """
    if not config_exists():
        click.echo(click.style("✗ Error: ", fg="red") + "No configuration found.")
        sys.exit(EXIT_ERROR)

    try:
        config = load_config()
        if config is None:
            click.echo(click.style("✗ Error: ", fg="red") + "Failed to load config")
            sys.exit(EXIT_ERROR)
    except Exception as e:
        click.echo(click.style("✗ Error: ", fg="red") + f"Config error: {e}")
        sys.exit(EXIT_ERROR)

    vault_path = Path(config.vault_path)
    full_path = vault_path / note_path

    if not full_path.exists():
        click.echo(click.style("✗ Error: ", fg="red") + f"Note not found: {note_path}")
        sys.exit(EXIT_ERROR)

    if not full_path.is_file():
        click.echo(click.style("✗ Error: ", fg="red") + f"Not a file: {note_path}")
        sys.exit(EXIT_ERROR)

    try:
        full_path.unlink()
        click.echo(click.style("✓ ", fg="green") + f"Deleted: {note_path}")
    except Exception as e:
        click.echo(click.style("✗ Error: ", fg="red") + f"Failed to delete: {e}")
        sys.exit(EXIT_ERROR)


async def _run_test_capture(
    config,
    url: str,
    model_config: ModelConfig | None,
    prefix: str
) -> CaptureResult:
    """Execute a test capture."""
    request = CaptureRequest(
        url=url,
        source=CaptureSource.CLI,
        timestamp=datetime.now()
    )

    service = CaptureService(config)
    try:
        result = await service.capture(request, model_config=model_config)

        # If successful, rename the note to add prefix
        if result.success and result.note_path:
            vault_path = Path(config.vault_path)
            old_path = vault_path / result.note_path
            if old_path.exists():
                new_name = prefix + old_path.name
                new_path = old_path.parent / new_name
                old_path.rename(new_path)
                result.note_path = str(new_path.relative_to(vault_path))

        return result
    finally:
        await service.close()

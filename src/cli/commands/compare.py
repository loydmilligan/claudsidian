"""Compare command - compare AI models for capture quality and cost."""

import asyncio
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import click
import yaml

from src.core.config import config_exists, load_config
from src.core.capture import CaptureService, CaptureResult, AIUsageMetrics
from src.core.ai.router import AIRouter
from src.models.capture import CaptureRequest, CaptureSource
from src.models.config import ModelConfig, Configuration, AVAILABLE_MODELS
from src.cli.commands.test_capture import (
    get_fixtures, VALID_CONTENT_TYPES, STANDARD_CONTENT_TYPES,
    PLAYWRIGHT_CONTENT_TYPES, TEST_FIXTURES_FILE
)
from src.core.extractors.printable_playwright import PLAYWRIGHT_AVAILABLE
from src.models.model_performance import ModelPerformanceDB, CapturePerformance, QualityScores

# Exit codes
EXIT_SUCCESS = 0
EXIT_ERROR = 1

# Default comparison model (for analyzing quality differences)
DEFAULT_COMPARISON_MODEL = "google/gemini-2.0-flash-exp:free"


@dataclass
class ModelRun:
    """Configuration for a single model run."""
    name: str  # Display name for the run (e.g., "Default", "Cheap")
    summary_model: str  # Model ID for summarization
    tags_model: str  # Model ID for tagging


@dataclass
class CaptureComparison:
    """Stores captures from multiple model runs for the same URL."""
    url: str
    content_type: str
    fixture_name: str
    results: dict[str, CaptureResult] = field(default_factory=dict)  # run_name -> result
    note_contents: dict[str, str] = field(default_factory=dict)  # run_name -> markdown content
    quality_analysis: str = ""  # AI-generated quality comparison


@dataclass
class ComparisonReport:
    """Full comparison report data."""
    runs: list[ModelRun]
    comparisons: list[CaptureComparison]
    timestamp: datetime
    comparison_model: str


def resolve_model(model_spec: str) -> tuple[str, str]:
    """Resolve a model spec to (backend, model_id).

    Args:
        model_spec: Either a preset name (e.g., 'openrouter-haiku') or
                   raw model ID (e.g., 'anthropic/claude-3-haiku')

    Returns:
        Tuple of (backend, model_id)
    """
    # Check if it's a preset
    if model_spec in AVAILABLE_MODELS:
        model_id = AVAILABLE_MODELS[model_spec]
    else:
        model_id = model_spec

    # Determine backend from model ID
    if model_spec.startswith("claude-") and "/" not in model_spec:
        return ("claude", model_id)
    elif "/" in model_id:
        return ("openrouter", model_id)
    else:
        # Assume claude for non-slash model IDs
        return ("claude", model_id)


# Default folder for test/comparison notes
TEST_NOTES_FOLDER = "_test_notes"


async def run_capture_with_config(
    config: Configuration,
    url: str,
    summary_model: str,
    tags_model: str,
    prefix: str = "_CMP_",
    output_folder: str = TEST_NOTES_FOLDER
) -> CaptureResult:
    """Run a single capture with specific model configuration.

    Skips duplicate checking to allow multiple runs capturing the same URL.
    All test/comparison notes go to _test_notes folder for easy cleanup.
    """
    # Resolve models
    summary_backend, summary_model_id = resolve_model(summary_model)
    tags_backend, tags_model_id = resolve_model(tags_model)

    # Create model config that forces specific models
    model_config = ModelConfig(
        summary_model=summary_model if summary_model in AVAILABLE_MODELS else "openrouter-haiku",
        tags_model=tags_model if tags_model in AVAILABLE_MODELS else "openrouter-haiku",
        cheap_mode=False
    )

    # Override the resolution to use our specific models
    # We need to patch the model config's resolution
    class CustomModelConfig(ModelConfig):
        def get_summary_model(self) -> tuple[str, str]:
            return (summary_backend, summary_model_id)

        def get_tags_model(self) -> tuple[str, str]:
            return (tags_backend, tags_model_id)

    custom_config = CustomModelConfig()

    request = CaptureRequest(
        url=url,
        source=CaptureSource.CLI,
        timestamp=datetime.now()
    )

    service = CaptureService(config)
    try:
        # Skip duplicate check for comparison runs - we want to capture same URL multiple times
        # Route all test notes to _test_notes folder for easy cleanup
        result = await service.capture(
            request,
            model_config=custom_config,
            skip_duplicate_check=True,
            target_folder=output_folder
        )

        # Rename note with prefix if successful
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


# Gold standard notes folder
GOLD_STANDARDS_FOLDER = "_test_notes/_gold_standards"


def find_gold_standard(vault_path: Path, fixture_name: str) -> str | None:
    """Find a gold standard note for a fixture.

    Args:
        vault_path: Path to vault
        fixture_name: Name of the fixture to find gold standard for

    Returns:
        Content of gold standard note, or None if not found
    """
    gold_folder = vault_path / GOLD_STANDARDS_FOLDER

    if not gold_folder.exists():
        return None

    # Try exact match first
    gold_file = gold_folder / f"_GOLD_{fixture_name}.md"
    if gold_file.exists():
        return gold_file.read_text(encoding="utf-8")

    # Try fuzzy match (fixture_name might be URL-sanitized differently)
    for md_file in gold_folder.glob("_GOLD_*.md"):
        # Check if fixture_name is a substring
        if fixture_name.lower() in md_file.stem.lower():
            return md_file.read_text(encoding="utf-8")

    return None


def _extract_summary_section(content: str, max_length: int = 2000) -> str:
    """Extract the summary section from note content."""
    summary_start = content.find("## Summary")
    summary_end = content.find("##", summary_start + 10) if summary_start >= 0 else -1

    if summary_start >= 0 and summary_end > summary_start:
        return content[summary_start:summary_end].strip()
    elif summary_start >= 0:
        return content[summary_start:summary_start + max_length].strip()
    else:
        return content[:max_length].strip()


async def analyze_quality(
    config: Configuration,
    contents: dict[str, str],
    comparison_model: str,
    gold_standard: str | None = None
) -> str:
    """Use AI to compare quality of different model outputs.

    When a gold standard is provided, does TWO analyses:
    1. Quality scores for each model vs gold standard (1-5)
    2. Difference analysis between models + which is closer to gold

    Args:
        config: Application configuration
        contents: Dict mapping run names to markdown note contents
        comparison_model: Model to use for comparison analysis
        gold_standard: Optional gold standard content to compare against

    Returns:
        AI-generated quality comparison analysis
    """
    if len(contents) < 2 and not gold_standard:
        return "Not enough outputs to compare."

    # Build comparison prompt
    prompt_parts = []

    if gold_standard:
        prompt_parts.append("You are evaluating AI-generated summaries. Perform TWO analyses:\n\n")

        prompt_parts.append("## ANALYSIS 1: Quality vs Gold Standard\n")
        prompt_parts.append("Score each output 1-5 based on how close it matches the gold standard.\n")
        prompt_parts.append("- 5 = Nearly identical quality and coverage\n")
        prompt_parts.append("- 4 = Minor omissions or differences\n")
        prompt_parts.append("- 3 = Captures main points but missing depth\n")
        prompt_parts.append("- 2 = Significant gaps or inaccuracies\n")
        prompt_parts.append("- 1 = Poor quality or mostly wrong\n\n")

        prompt_parts.append("## ANALYSIS 2: Model Comparison\n")
        prompt_parts.append("Compare the outputs to each other. Note specific differences.\n")
        prompt_parts.append("State which model output is CLOSER to the gold standard and why.\n\n")

        # Extract gold standard summary
        gold_summary = _extract_summary_section(gold_standard, max_length=3000)
        prompt_parts.append(f"### GOLD STANDARD (Reference):\n```\n{gold_summary}\n```\n\n")
    else:
        prompt_parts.append("Compare the following AI-generated note summaries for the same content.\n")
        prompt_parts.append("Evaluate each on: completeness, accuracy, readability, and usefulness.\n")
        prompt_parts.append("Note which is better overall and why. Be concise but specific.\n\n")

    for name, content in contents.items():
        summary = _extract_summary_section(content)
        prompt_parts.append(f"### {name} Output:\n```\n{summary}\n```\n\n")

    if gold_standard:
        prompt_parts.append("---\n")
        prompt_parts.append("Respond in this format:\n")
        prompt_parts.append("**Quality Scores:**\n")
        prompt_parts.append("- [Model A]: X/5 - [brief reason]\n")
        prompt_parts.append("- [Model B]: X/5 - [brief reason]\n\n")
        prompt_parts.append("**Key Differences:**\n")
        prompt_parts.append("[2-3 bullet points noting specific differences between model outputs]\n\n")
        prompt_parts.append("**Closer to Gold Standard:** [Model name] because [1 sentence reason]\n")
    else:
        prompt_parts.append("\nProvide a brief comparison (3-5 sentences) noting key differences and which is better.")

    prompt = "".join(prompt_parts)

    # Use AIRouter to make the comparison call
    router = AIRouter(config)
    try:
        # Resolve comparison model
        backend, model_id = resolve_model(comparison_model)

        response = await router.route_with_model(
            backend=backend,
            model=model_id,
            prompt=prompt,
            system_prompt="You are a quality analyst comparing AI-generated content. Be objective and concise.",
            temperature=0.3
        )
        return response.content
    except Exception as e:
        return f"Error during quality analysis: {str(e)}"
    finally:
        await router.close()


import re


def extract_quality_scores(analysis: str, run_names: list[str]) -> dict[str, float]:
    """Extract quality scores from AI analysis text.

    Looks for patterns like "Run A: 4/5" or "[Model A]: 4/5" in the analysis.

    Args:
        analysis: The quality analysis text
        run_names: List of run names to look for

    Returns:
        Dict mapping run name to score (1-5), empty if not found
    """
    scores = {}
    for name in run_names:
        # Extract the letter from "Run A" -> "A", "Run B" -> "B"
        letter = name.split()[-1] if ' ' in name else name

        # Match patterns like "Run A: 4/5", "[Model A]: 4/5", "Run A]: 4/5", "Run A: 4 /5"
        patterns = [
            # Direct run name patterns
            rf"{re.escape(name)}[:\]]\s*(\d(?:\.\d)?)\s*/\s*5",
            rf"{re.escape(name)}[:\]]\s*(\d(?:\.\d)?)\s*out of\s*5",
            rf"\*\*{re.escape(name)}\*\*[:\]]\s*(\d(?:\.\d)?)\s*/\s*5",
            # Model X patterns (for prompts that use [Model A] format)
            rf"\[Model\s+{re.escape(letter)}\][:\]]\s*(\d(?:\.\d)?)\s*/\s*5",
            rf"\[Model\s+{re.escape(letter)}\][:\]]\s*(\d(?:\.\d)?)\s*out of\s*5",
        ]
        for pattern in patterns:
            match = re.search(pattern, analysis, re.IGNORECASE)
            if match:
                try:
                    scores[name] = float(match.group(1))
                    break
                except ValueError:
                    pass
    return scores


def generate_comparison_html(
    report: ComparisonReport,
    output_path: Path
) -> None:
    """Generate HTML comparison report."""
    timestamp = report.timestamp.strftime("%Y-%m-%d %H:%M:%S")

    # Calculate totals per run
    run_totals: dict[str, dict[str, Any]] = {}
    for run in report.runs:
        run_totals[run.name] = {
            "success": 0,
            "failed": 0,
            "cost": 0.0,
            "input_tokens": 0,
            "output_tokens": 0,
            "time_seconds": 0.0,
            "summary_model": run.summary_model,
            "tags_model": run.tags_model,
            "quality_scores": [],  # List of scores for averaging
        }

    for comp in report.comparisons:
        for run_name, result in comp.results.items():
            if result.success:
                run_totals[run_name]["success"] += 1
                if result.ai_metrics:
                    run_totals[run_name]["cost"] += result.ai_metrics.total_cost_usd
                    run_totals[run_name]["input_tokens"] += result.ai_metrics.total_input_tokens
                    run_totals[run_name]["output_tokens"] += result.ai_metrics.total_output_tokens
                    run_totals[run_name]["time_seconds"] += result.ai_metrics.total_time_seconds

                # Extract quality score from analysis
                if comp.quality_analysis:
                    scores = extract_quality_scores(comp.quality_analysis, [run_name])
                    if run_name in scores:
                        run_totals[run_name]["quality_scores"].append(scores[run_name])
            else:
                run_totals[run_name]["failed"] += 1

    # Calculate average quality scores and OPUS metric
    for run_name, data in run_totals.items():
        scores = data["quality_scores"]
        data["avg_quality"] = sum(scores) / len(scores) if scores else 0
        # OPUS = (quality/5) / avg_cost - higher is better
        avg_cost = data["cost"] / data["success"] if data["success"] > 0 else 0
        if avg_cost > 0:
            data["opus"] = (data["avg_quality"] / 5.0) / avg_cost
        else:
            data["opus"] = 1000.0 if data["avg_quality"] > 0 else 0  # Free model cap
        # Average time per capture
        data["avg_time"] = data["time_seconds"] / data["success"] if data["success"] > 0 else 0

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Claudsidian Model Comparison Report</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
            color: #333;
        }}
        h1 {{ color: #6b46c1; border-bottom: 3px solid #6b46c1; padding-bottom: 10px; }}
        h2 {{ color: #553c9a; margin-top: 30px; }}
        h3 {{ color: #6b46c1; }}
        .run-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .run-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border-left: 4px solid #6b46c1;
        }}
        .run-card h3 {{ margin-top: 0; }}
        .run-card .model {{ font-family: monospace; font-size: 12px; color: #666; margin: 5px 0; }}
        .run-card .stats {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 15px; }}
        .stat {{ text-align: center; padding: 10px; background: #f9f9f9; border-radius: 4px; }}
        .stat .value {{ font-size: 24px; font-weight: bold; }}
        .stat .label {{ font-size: 11px; color: #888; text-transform: uppercase; }}
        .stat.cost .value {{ color: #d69e2e; }}
        .stat.success .value {{ color: #38a169; }}
        .comparison-table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin: 20px 0;
        }}
        .comparison-table th, .comparison-table td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        .comparison-table th {{ background: #6b46c1; color: white; }}
        .comparison-table tr:hover {{ background: #f9f9f9; }}
        .quality-box {{
            background: #fef3c7;
            border: 1px solid #f6ad55;
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
        }}
        .quality-box h4 {{ margin: 0 0 10px 0; color: #92400e; }}
        .cost {{ font-family: monospace; color: #d69e2e; }}
        .tokens {{ font-family: monospace; color: #666; font-size: 12px; }}
        .winner {{ background: #d1fae5 !important; }}
        .model-tag {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-family: monospace;
            background: #e9d8fd;
            color: #553c9a;
        }}
        .savings {{
            background: #d1fae5;
            color: #065f46;
            padding: 4px 8px;
            border-radius: 4px;
            font-weight: bold;
        }}
        .cost-increase {{
            background: #fed7d7;
            color: #c53030;
            padding: 4px 8px;
            border-radius: 4px;
        }}
        footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #888; font-size: 12px; }}
        /* Expandable quality analysis */
        .quality-expandable {{
            max-height: 100px;
            overflow: hidden;
            transition: max-height 0.3s ease;
            position: relative;
        }}
        .quality-expandable.expanded {{
            max-height: none;
        }}
        .quality-expandable:not(.expanded)::after {{
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 40px;
            background: linear-gradient(transparent, #fef3c7);
        }}
        .expand-btn {{
            display: block;
            width: 100%;
            padding: 8px;
            background: #f6ad55;
            border: none;
            border-radius: 0 0 4px 4px;
            cursor: pointer;
            font-size: 12px;
            color: #92400e;
        }}
        .expand-btn:hover {{ background: #ed8936; }}
        /* OPUS metric styling */
        .opus-score {{
            font-size: 28px;
            font-weight: bold;
            color: #6b46c1;
        }}
        .opus-label {{
            font-size: 10px;
            color: #888;
        }}
        .time-stat {{ color: #3182ce; }}
        .chart-container {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin: 20px 0;
        }}
        .chart-container h3 {{
            margin-top: 0;
            margin-bottom: 20px;
        }}
        .scatter-chart {{
            position: relative;
            width: 100%;
            height: 400px;
            border: 1px solid #e2e8f0;
            border-radius: 4px;
            background: linear-gradient(to right, #fef3c7 0%, #d1fae5 100%);
        }}
        .chart-point {{
            position: absolute;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            transform: translate(-50%, -50%);
            cursor: pointer;
            border: 3px solid white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            transition: transform 0.2s;
        }}
        .chart-point:hover {{
            transform: translate(-50%, -50%) scale(1.3);
            z-index: 10;
        }}
        .chart-point.run-a {{ background: #6b46c1; }}
        .chart-point.run-b {{ background: #38a169; }}
        .chart-axis {{
            position: absolute;
            color: #666;
            font-size: 11px;
        }}
        .chart-label {{
            position: absolute;
            font-size: 12px;
            font-weight: bold;
            color: #333;
        }}
        .chart-legend {{
            display: flex;
            gap: 20px;
            margin-top: 15px;
            justify-content: center;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 13px;
        }}
        .legend-dot {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
        }}
        .legend-dot.run-a {{ background: #6b46c1; }}
        .legend-dot.run-b {{ background: #38a169; }}
        .tooltip {{
            position: absolute;
            background: rgba(0,0,0,0.8);
            color: white;
            padding: 8px 12px;
            border-radius: 4px;
            font-size: 12px;
            pointer-events: none;
            white-space: nowrap;
            z-index: 100;
            display: none;
        }}
    </style>
    <script>
        function toggleExpand(id) {{
            const el = document.getElementById(id);
            el.classList.toggle('expanded');
        }}
    </script>
</head>
<body>
    <h1>Model Comparison Report</h1>
    <p>Generated: {timestamp}</p>
    <p>Quality analysis model: <span class="model-tag">{report.comparison_model}</span></p>

    <h2>Run Summary</h2>
    <div class="run-cards">
"""

    # Calculate cost comparison - only compare runs with successful captures
    run_costs = [
        (name, data["cost"], data["success"])
        for name, data in run_totals.items()
    ]
    # Filter to runs with at least one success for meaningful comparison
    successful_runs = [(name, cost, success) for name, cost, success in run_costs if success > 0]

    cheapest = None
    most_expensive = None
    if len(successful_runs) >= 2:
        successful_runs.sort(key=lambda x: x[1])
        cheapest = successful_runs[0]
        most_expensive = successful_runs[-1]

    for run in report.runs:
        data = run_totals[run.name]

        # Cost comparison badge - only show if both runs have successful captures
        cost_badge = ""
        if cheapest and most_expensive and data["success"] > 0:
            if run.name == cheapest[0] and most_expensive[1] > 0:
                savings_pct = ((most_expensive[1] - cheapest[1]) / most_expensive[1]) * 100
                cost_badge = f'<span class="savings">{savings_pct:.0f}% cheaper</span>'
            elif run.name == most_expensive[0] and cheapest[1] > 0:
                increase_pct = ((most_expensive[1] - cheapest[1]) / cheapest[1]) * 100
                cost_badge = f'<span class="cost-increase">{increase_pct:.0f}% more</span>'
        elif data["success"] == 0:
            cost_badge = '<span style="background:#fed7d7;color:#c53030;padding:4px 8px;border-radius:4px;">All failed</span>'

        # Calculate derived metrics
        total_attempts = data['success'] + data['failed']
        success_rate = (data['success'] / total_attempts * 100) if total_attempts > 0 else 0
        cost_per_capture = (data['cost'] / data['success']) if data['success'] > 0 else 0

        # Format OPUS for display
        opus_display = f"{data['opus']:.1f}" if data['opus'] < 100 else "∞" if data['opus'] >= 1000 else f"{data['opus']:.0f}"

        html += f"""
        <div class="run-card">
            <h3>{run.name} {cost_badge}</h3>
            <div class="model">Summary: {run.summary_model}</div>
            <div class="model">Tags: {run.tags_model}</div>
            <div class="stats" style="grid-template-columns: repeat(3, 1fr);">
                <div class="stat">
                    <div class="opus-score">{opus_display}</div>
                    <div class="opus-label">OPUS Score</div>
                    <div style="font-size:10px;color:#888;">(quality/cost)</div>
                </div>
                <div class="stat">
                    <div class="value" style="color:#805ad5;">{data['avg_quality']:.1f}/5</div>
                    <div class="label">Avg Quality</div>
                </div>
                <div class="stat time-stat">
                    <div class="value">{data['avg_time']:.1f}s</div>
                    <div class="label">Avg Time</div>
                </div>
                <div class="stat success">
                    <div class="value">{data['success']}/{total_attempts}</div>
                    <div class="label">Success ({success_rate:.0f}%)</div>
                </div>
                <div class="stat cost">
                    <div class="value">${data['cost']:.4f}</div>
                    <div class="label">Total Cost</div>
                </div>
                <div class="stat">
                    <div class="value">${cost_per_capture:.4f}</div>
                    <div class="label">Cost/Capture</div>
                </div>
            </div>
            <div style="margin-top:10px;font-size:11px;color:#666;">
                Tokens: {data['input_tokens']:,} in / {data['output_tokens']:,} out |
                Total time: {data['time_seconds']:.1f}s
            </div>
        </div>
"""

    html += """
    </div>
"""

    # Build scatter chart data - cost vs quality by content type
    # Collect per-comparison data points
    chart_data: list[dict] = []
    for comp in report.comparisons:
        if comp.quality_analysis:
            run_names = [r.name for r in report.runs]
            scores = extract_quality_scores(comp.quality_analysis, run_names)

            for run in report.runs:
                result = comp.results.get(run.name)
                if result and result.success and result.ai_metrics and run.name in scores:
                    chart_data.append({
                        "run": run.name,
                        "content_type": comp.content_type,
                        "fixture": comp.fixture_name,
                        "cost": result.ai_metrics.total_cost_usd,
                        "quality": scores[run.name]
                    })

    # Only show chart if we have data points
    if chart_data:
        # Calculate chart bounds
        max_cost = max(d["cost"] for d in chart_data) * 1.1 if chart_data else 0.01
        min_cost = 0

        html += """
    <h2>Cost vs Quality</h2>
    <div class="chart-container">
        <h3>Lower cost + Higher quality = Better (top-left is ideal)</h3>
        <div class="scatter-chart" id="scatter-chart">
            <!-- Y-axis labels (Quality 1-5) -->
            <span class="chart-axis" style="left: -25px; top: 10%;">5</span>
            <span class="chart-axis" style="left: -25px; top: 30%;">4</span>
            <span class="chart-axis" style="left: -25px; top: 50%;">3</span>
            <span class="chart-axis" style="left: -25px; top: 70%;">2</span>
            <span class="chart-axis" style="left: -25px; top: 90%;">1</span>
            <span class="chart-label" style="left: -45px; top: 50%; transform: rotate(-90deg) translateX(50%);">Quality Score</span>

            <!-- X-axis label -->
            <span class="chart-label" style="bottom: -30px; left: 50%; transform: translateX(-50%);">Cost ($)</span>
"""

        # Add data points
        for i, point in enumerate(chart_data):
            # X position: cost (0 to max_cost) -> 5% to 95%
            x_pct = 5 + (point["cost"] / max_cost) * 90 if max_cost > 0 else 50
            # Y position: quality (1 to 5) -> 90% to 10% (inverted so 5 is at top)
            y_pct = 90 - ((point["quality"] - 1) / 4) * 80

            run_class = "run-a" if point["run"] == "Run A" else "run-b"
            tooltip = f"{point['fixture']} ({point['content_type']}): ${point['cost']:.4f}, {point['quality']}/5"

            html += f"""            <div class="chart-point {run_class}"
                 style="left: {x_pct}%; top: {y_pct}%;"
                 title="{tooltip}"
                 data-fixture="{point['fixture']}"
                 data-cost="{point['cost']:.4f}"
                 data-quality="{point['quality']}"></div>
"""

        # X-axis cost labels
        html += f"""
            <span class="chart-axis" style="bottom: -20px; left: 5%;">$0</span>
            <span class="chart-axis" style="bottom: -20px; left: 50%;">${max_cost/2:.4f}</span>
            <span class="chart-axis" style="bottom: -20px; left: 95%;">${max_cost:.4f}</span>
        </div>
        <div class="chart-legend">
            <div class="legend-item"><span class="legend-dot run-a"></span> {report.runs[0].name} ({report.runs[0].summary_model})</div>
"""
        if len(report.runs) > 1:
            html += f"""            <div class="legend-item"><span class="legend-dot run-b"></span> {report.runs[1].name} ({report.runs[1].summary_model})</div>
"""

        # Add summary stats
        run_a_data = [d for d in chart_data if d["run"] == "Run A"]
        run_b_data = [d for d in chart_data if d["run"] == "Run B"]

        avg_quality_a = sum(d["quality"] for d in run_a_data) / len(run_a_data) if run_a_data else 0
        avg_cost_a = sum(d["cost"] for d in run_a_data) / len(run_a_data) if run_a_data else 0
        avg_quality_b = sum(d["quality"] for d in run_b_data) / len(run_b_data) if run_b_data else 0
        avg_cost_b = sum(d["cost"] for d in run_b_data) / len(run_b_data) if run_b_data else 0

        html += f"""        </div>
        <div style="margin-top: 20px; display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
            <div style="text-align: center; padding: 15px; background: #f3e8ff; border-radius: 8px;">
                <strong>{report.runs[0].name}</strong><br>
                Avg Quality: <strong>{avg_quality_a:.2f}/5</strong> | Avg Cost: <strong>${avg_cost_a:.4f}</strong>
            </div>
"""
        if len(report.runs) > 1:
            html += f"""            <div style="text-align: center; padding: 15px; background: #d1fae5; border-radius: 8px;">
                <strong>{report.runs[1].name}</strong><br>
                Avg Quality: <strong>{avg_quality_b:.2f}/5</strong> | Avg Cost: <strong>${avg_cost_b:.4f}</strong>
            </div>
"""

        html += """        </div>
    </div>
"""

    html += """
    <h2>Detailed Comparisons</h2>
"""

    # Group by content type
    by_type: dict[str, list[CaptureComparison]] = {}
    for comp in report.comparisons:
        if comp.content_type not in by_type:
            by_type[comp.content_type] = []
        by_type[comp.content_type].append(comp)

    for ctype, comps in by_type.items():
        html += f"""
    <h3>{ctype.upper()}</h3>
    <table class="comparison-table">
        <tr>
            <th>URL</th>
"""
        for run in report.runs:
            html += f"            <th>{run.name}<br><small>Cost / Tokens</small></th>\n"
        html += "            <th>Quality Analysis</th>\n        </tr>\n"

        for comp in comps:
            html += f"""
        <tr>
            <td><strong>{comp.fixture_name}</strong><br><small>{comp.url[:50]}...</small></td>
"""
            # Find winner (lowest cost among successful)
            successful_costs = [
                (name, r.ai_metrics.total_cost_usd if r.ai_metrics else 999)
                for name, r in comp.results.items()
                if r.success
            ]
            winner = min(successful_costs, key=lambda x: x[1])[0] if successful_costs else None

            for run in report.runs:
                result = comp.results.get(run.name)
                if result and result.success and result.ai_metrics:
                    m = result.ai_metrics
                    winner_class = "winner" if run.name == winner and len(successful_costs) > 1 else ""
                    html += f"""            <td class="{winner_class}">
                <span class="cost">${m.total_cost_usd:.4f}</span><br>
                <span class="tokens">{m.total_input_tokens:,} / {m.total_output_tokens:,}</span>
            </td>
"""
                elif result:
                    html += f"            <td style='color:#e53e3e'>Failed</td>\n"
                else:
                    html += "            <td>-</td>\n"

            # Quality analysis - escape HTML and make expandable
            analysis = comp.quality_analysis or "No analysis available"
            # Escape HTML special chars
            analysis_escaped = analysis.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            # Convert newlines to <br> for display
            analysis_html = analysis_escaped.replace("\n", "<br>")
            # Generate unique ID for this row
            row_id = f"analysis_{hash(comp.url) % 10000}"

            html += f"""            <td class="quality-box" style="max-width: 500px;">
                <div class="quality-expandable" id="{row_id}">
                    {analysis_html}
                </div>
                <button class="expand-btn" onclick="toggleExpand('{row_id}')">
                    Show More / Less
                </button>
            </td>
        </tr>
"""

        html += "    </table>\n"

    html += """
    <footer>
        <p>Report generated by Claudsidian model comparison tool</p>
        <p style="margin-top:10px;">
            <strong>OPUS Score</strong> = (Quality / 5) ÷ Cost per capture<br>
            Higher is better. Measures quality-adjusted cost efficiency.
        </p>
    </footer>
</body>
</html>
"""

    output_path.write_text(html, encoding='utf-8')


@click.group()
def compare():
    """Compare AI models for capture quality and cost.

    Run captures with different model configurations and compare
    the results, costs, and quality.
    """
    pass


@compare.command("models")
def list_models() -> None:
    """List available model presets."""
    click.echo(click.style("\nAvailable Model Presets:", fg="cyan", bold=True))
    click.echo()
    for preset, model_id in AVAILABLE_MODELS.items():
        click.echo(f"  {preset}")
        click.echo(f"    → {model_id}")
    click.echo()
    click.echo("You can also use raw model IDs directly (e.g., 'anthropic/claude-3-haiku')")


@compare.command("run")
@click.option("--type", "-t", "content_type", help="Only test this content type")
@click.option("--count", "-n", default=1, help="Fixtures per type (default: 1)")
@click.option("--summary-model-1", "-s1", default="openrouter-grok-fast",
              help="First summary model (default: openrouter-grok-fast)")
@click.option("--summary-model-2", "-s2", default="openrouter-haiku",
              help="Second summary model (default: openrouter-haiku)")
@click.option("--tags-model-1", "-t1", default="openrouter-haiku",
              help="First tags model (default: openrouter-haiku)")
@click.option("--tags-model-2", "-t2", default="openrouter-haiku",
              help="Second tags model (default: openrouter-haiku)")
@click.option("--comparison-model", "-c", default=DEFAULT_COMPARISON_MODEL,
              help=f"Model for quality analysis (default: {DEFAULT_COMPARISON_MODEL})")
@click.option("--skip-quality", is_flag=True, help="Skip AI quality comparison")
@click.option("--require-gold", is_flag=True, help="Only analyze fixtures that have gold standards")
@click.option("--prefix", "-p", default="_CMP_", help="Prefix for test notes")
@click.option("--include-printable", is_flag=True,
              help="Include printable content type (requires Playwright)")
def run_comparison(
    content_type: str | None,
    count: int,
    summary_model_1: str,
    summary_model_2: str,
    tags_model_1: str,
    tags_model_2: str,
    comparison_model: str,
    skip_quality: bool,
    require_gold: bool,
    prefix: str,
    include_printable: bool
) -> None:
    """Run model comparison captures.

    Captures the same URLs with two different model configurations
    and compares cost, tokens, and optionally quality.

    By default, skips 'printable' content type since it requires Playwright
    browser automation. Use --include-printable to include it (requires
    Playwright to be installed: pip install playwright && playwright install chromium).

    If gold standard notes exist in _test_notes/_gold_standards/, they will
    be used as the reference for quality scoring (1-5) and comparison.

    Examples:
        # Compare default (Claude) vs cheap (Haiku) for summary
        claudsidian compare run --count 1

        # Compare two different cheap models
        claudsidian compare run -s1 openrouter-haiku -s2 openrouter-gpt4o-mini

        # Only run fixtures with gold standards
        claudsidian compare run --require-gold

        # Full comparison with all fixtures
        claudsidian compare run --count 3

        # Include printable content (requires Playwright)
        claudsidian compare run --include-printable
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

    # Create timestamped run directory
    pacific = ZoneInfo("America/Los_Angeles")
    run_timestamp = datetime.now(pacific)
    timestamp_str = run_timestamp.strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = vault_path / "reports" / timestamp_str
    run_dir.mkdir(parents=True, exist_ok=True)

    # Load fixtures
    fixtures = get_fixtures(config)
    test_file = vault_path / TEST_FIXTURES_FILE
    if not test_file.exists():
        click.echo(click.style("⚠ ", fg="yellow") + f"No {TEST_FIXTURES_FILE} found")
        click.echo("Run 'claudsidian test-capture init' first")
        sys.exit(EXIT_ERROR)

    # Define the runs
    runs = [
        ModelRun(
            name="Run A",
            summary_model=summary_model_1,
            tags_model=tags_model_1
        ),
        ModelRun(
            name="Run B",
            summary_model=summary_model_2,
            tags_model=tags_model_2
        )
    ]

    # Determine content types to test
    if content_type:
        # User specified a specific type
        types_to_test = [content_type]
        # Warn if requesting printable without --include-printable
        if content_type in PLAYWRIGHT_CONTENT_TYPES and not include_printable:
            click.echo(click.style("⚠ Warning: ", fg="yellow") +
                      f"'{content_type}' requires Playwright browser automation.")
            if not PLAYWRIGHT_AVAILABLE:
                click.echo(click.style("  ", fg="yellow") +
                          "Playwright not installed. Install with: pip install playwright && playwright install chromium")
            click.echo(click.style("  ", fg="yellow") +
                      "Add --include-printable flag to confirm you want to test this type.")
            sys.exit(EXIT_ERROR)
    else:
        # Default: use standard content types only
        types_to_test = STANDARD_CONTENT_TYPES.copy()

        # Add Playwright types if explicitly requested
        if include_printable:
            if PLAYWRIGHT_AVAILABLE:
                types_to_test.extend(PLAYWRIGHT_CONTENT_TYPES)
                click.echo(click.style("✓ ", fg="green") + "Including printable content (Playwright available)")
            else:
                click.echo(click.style("⚠ Warning: ", fg="yellow") +
                          "Cannot include printable - Playwright not installed")
                click.echo("  Install with: pip install playwright && playwright install chromium")
        else:
            # Show info about skipped types
            skipped = fixtures.get("printable", [])
            if skipped:
                click.echo(click.style("ℹ ", fg="blue") +
                          f"Skipping {len(skipped)} printable fixture(s) (requires Playwright)")
                click.echo("  Add --include-printable to include them")

    comparisons: list[CaptureComparison] = []

    # Count fixtures
    total_fixtures = 0
    for ctype in types_to_test:
        type_fixtures = fixtures.get(ctype, [])[:count]
        total_fixtures += len(type_fixtures)

    total_captures = total_fixtures * len(runs)

    click.echo(click.style(f"\nModel Comparison Test", fg="cyan", bold=True))
    click.echo(f"Fixtures: {total_fixtures} × {len(runs)} runs = {total_captures} captures")
    click.echo()

    for i, run in enumerate(runs):
        click.echo(f"  {run.name}:")
        click.echo(f"    Summary: {run.summary_model}")
        click.echo(f"    Tags: {run.tags_model}")

    if not skip_quality:
        click.echo(f"\n  Quality analysis: {comparison_model}")

    click.echo()

    # Build flat list of all fixture tasks for progress tracking
    all_tasks: list[tuple[str, dict]] = []
    for ctype in types_to_test:
        type_fixtures = fixtures.get(ctype, [])[:count]
        for fixture in type_fixtures:
            all_tasks.append((ctype, fixture))

    # Run captures with progress bar
    with click.progressbar(
        all_tasks,
        label="Capturing",
        item_show_func=lambda x: f"{x[0]}: {x[1].get('name', x[1]['url'])[:30]}..." if x else "",
        show_pos=True,
        show_percent=True
    ) as progress:
        for ctype, fixture in progress:
            url = fixture['url']
            name = fixture.get('name') or url

            # Check for gold standard if required
            if require_gold:
                gold_check = find_gold_standard(vault_path, name)
                if not gold_check:
                    continue

            comparison = CaptureComparison(
                url=url,
                content_type=ctype,
                fixture_name=name
            )

            for run in runs:
                run_prefix = f"{prefix}{run.name.replace(' ', '_')}_"
                # Use relative path from vault to run directory
                output_folder = str(run_dir.relative_to(vault_path))

                try:
                    result = asyncio.run(run_capture_with_config(
                        config=config,
                        url=url,
                        summary_model=run.summary_model,
                        tags_model=run.tags_model,
                        prefix=run_prefix,
                        output_folder=output_folder
                    ))

                    comparison.results[run.name] = result

                    if result.success:
                        # Read note content for quality comparison
                        if result.note_path:
                            note_path = vault_path / result.note_path
                            if note_path.exists():
                                comparison.note_contents[run.name] = note_path.read_text(encoding='utf-8')

                except Exception as e:
                    comparison.results[run.name] = CaptureResult(
                        success=False,
                        error=str(e)
                    )

            # Run quality comparison if we have successful captures
            if not skip_quality and len(comparison.note_contents) >= 1:
                # Look for gold standard for this fixture
                gold_standard = find_gold_standard(vault_path, name)

                if gold_standard or len(comparison.note_contents) >= 2:
                    try:
                        analysis = asyncio.run(analyze_quality(
                            config, comparison.note_contents, comparison_model,
                            gold_standard=gold_standard
                        ))
                        comparison.quality_analysis = analysis
                    except Exception:
                        pass  # Silently skip quality analysis failures during progress

            comparisons.append(comparison)

    # Generate report
    report = ComparisonReport(
        runs=runs,
        comparisons=comparisons,
        timestamp=run_timestamp,
        comparison_model=comparison_model
    )

    # Save HTML report in the run directory
    report_path = run_dir / "report.html"
    generate_comparison_html(report, report_path)

    # Calculate summary statistics for the markdown summary
    run_stats: dict[str, dict[str, Any]] = {}
    for run in runs:
        total_cost = sum(
            c.results[run.name].ai_metrics.total_cost_usd
            for c in comparisons
            if run.name in c.results and c.results[run.name].success and c.results[run.name].ai_metrics
        )
        success_count = sum(
            1 for c in comparisons
            if run.name in c.results and c.results[run.name].success
        )
        failed_count = sum(
            1 for c in comparisons
            if run.name in c.results and not c.results[run.name].success
        )
        total_time = sum(
            c.results[run.name].ai_metrics.total_time_seconds
            for c in comparisons
            if run.name in c.results and c.results[run.name].success and c.results[run.name].ai_metrics
        )
        run_stats[run.name] = {
            "success": success_count,
            "failed": failed_count,
            "total_cost": total_cost,
            "total_time": total_time
        }

    # Generate _run_summary.md
    summary_lines = [
        "# Model Comparison Run Summary",
        "",
        f"**Date/Time:** {run_timestamp.strftime('%Y-%m-%d %H:%M:%S %Z')}",
        "",
        "## Model Configuration",
        ""
    ]

    for run in runs:
        summary_lines.extend([
            f"### {run.name}",
            f"- **Summary Model:** `{run.summary_model}`",
            f"- **Tags Model:** `{run.tags_model}`",
            ""
        ])

    summary_lines.extend([
        f"**Quality Analysis Model:** `{comparison_model}`",
        "",
        "## Content Types Tested",
        ""
    ])

    # Group fixtures by content type
    by_type: dict[str, int] = {}
    for comp in comparisons:
        by_type[comp.content_type] = by_type.get(comp.content_type, 0) + 1

    for ctype, count in sorted(by_type.items()):
        summary_lines.append(f"- **{ctype}:** {count} fixture(s)")

    summary_lines.extend([
        "",
        f"**Total Fixtures:** {len(comparisons)}",
        "",
        "## Results Summary",
        ""
    ])

    for run in runs:
        stats = run_stats[run.name]
        success_rate = (stats["success"] / (stats["success"] + stats["failed"]) * 100) if (stats["success"] + stats["failed"]) > 0 else 0
        avg_cost = stats["total_cost"] / stats["success"] if stats["success"] > 0 else 0
        avg_time = stats["total_time"] / stats["success"] if stats["success"] > 0 else 0

        summary_lines.extend([
            f"### {run.name}",
            f"- **Success Rate:** {success_rate:.1f}% ({stats['success']}/{stats['success'] + stats['failed']})",
            f"- **Total Cost:** ${stats['total_cost']:.4f}",
            f"- **Average Cost per Capture:** ${avg_cost:.4f}",
            f"- **Total Time:** {stats['total_time']:.1f}s",
            f"- **Average Time per Capture:** {avg_time:.1f}s",
            ""
        ])

    summary_lines.extend([
        "## Generated Notes",
        ""
    ])

    # Add wikilinks to all created notes
    for comp in comparisons:
        for run in runs:
            result = comp.results.get(run.name)
            if result and result.success and result.note_path:
                note_path = vault_path / result.note_path
                if note_path.exists():
                    # Create wikilink using note filename without extension
                    note_name = note_path.stem
                    summary_lines.append(f"- [[{note_name}]] ({run.name})")

    summary_lines.extend([
        "",
        "## Report",
        "",
        "[[report.html|View HTML Comparison Report]]",
        ""
    ])

    summary_md_path = run_dir / "_run_summary.md"
    summary_md_path.write_text("\n".join(summary_lines), encoding="utf-8")

    # Update performance database with quality scores from comparisons
    try:
        perf_db_path = vault_path / ".claudsidian" / "model_performance.json"
        perf_db = ModelPerformanceDB(perf_db_path)

        for comp in comparisons:
            if not comp.quality_analysis:
                continue

            run_names = [r.name for r in runs]
            scores = extract_quality_scores(comp.quality_analysis, run_names)

            for run in runs:
                result = comp.results.get(run.name)
                if not result or not result.success or not result.ai_metrics:
                    continue

                quality_score = scores.get(run.name)
                if quality_score is None:
                    continue

                # Create performance record with quality score
                perf_record = CapturePerformance(
                    capture_id=f"compare_{run_timestamp.strftime('%Y%m%d_%H%M%S')}_{comp.fixture_name}_{run.name}",
                    timestamp=run_timestamp.isoformat(),
                    fixture_name=comp.fixture_name,
                    content_type=comp.content_type,
                    url=comp.url,
                    summary_model=run.summary_model,
                    tags_model=run.tags_model,
                    input_tokens=result.ai_metrics.summary_input_tokens + result.ai_metrics.tags_input_tokens,
                    output_tokens=result.ai_metrics.summary_output_tokens + result.ai_metrics.tags_output_tokens,
                    cost_usd=result.ai_metrics.total_cost_usd,
                    time_seconds=result.ai_metrics.total_time_seconds,
                    success=True,
                    quality=QualityScores(
                        accuracy=quality_score,
                        completeness=quality_score,
                        structure=quality_score,
                        conciseness=quality_score
                    ),
                    quality_notes=f"From compare run: {comp.quality_analysis[:200]}..."
                )
                perf_db.add_capture(perf_record)

        logger.info(f"Updated performance DB with {len(comparisons)} comparison results")
    except Exception as e:
        logger.warning(f"Failed to update performance DB: {e}")

    # Print summary
    click.echo()
    click.echo(click.style("Summary:", bold=True))

    for run in runs:
        stats = run_stats[run.name]
        click.echo(f"  {run.name}: {stats['success']} captures, ${stats['total_cost']:.4f}")

    click.echo()
    click.echo(click.style("Report:", bold=True))
    click.echo(f"  {report_path}")
    click.echo(f"  {summary_md_path}")


# Rating grace period in days - unrated notes older than this will be deleted
RATING_GRACE_PERIOD_DAYS = 14


def parse_note_frontmatter(file_path: Path) -> dict | None:
    """Parse frontmatter from a markdown file.

    Returns:
        Dict with frontmatter fields, or None if parsing fails
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        if not content.startswith("---"):
            return None
        parts = content.split("---", 2)
        if len(parts) < 3:
            return None
        return yaml.safe_load(parts[1].strip())
    except Exception:
        return None


def should_delete_test_note(file_path: Path, ignore_ratings: bool = False) -> tuple[bool, str]:
    """Determine if a test note should be deleted based on rating status.

    Rules:
    - If ignore_ratings=True, delete everything (for --force-all)
    - If rating_processed=True, delete (rating already captured)
    - If user_rating is set but rating_processed=False, keep (pending rating)
    - If no rating and note is older than 14 days, delete (grace period expired)
    - If no rating and note is less than 14 days old, keep (within grace period)

    Returns:
        Tuple of (should_delete: bool, reason: str)
    """
    if ignore_ratings:
        return True, "force-all"

    frontmatter = parse_note_frontmatter(file_path)
    if frontmatter is None:
        return True, "no frontmatter"

    user_rating = frontmatter.get("user_rating")
    rating_processed = frontmatter.get("rating_processed", False)

    # Already processed rating - safe to delete
    if rating_processed:
        return True, "rating processed"

    # Has unprocessed rating - keep it!
    if user_rating is not None:
        return False, f"pending rating ({user_rating} stars)"

    # No rating - check age
    captured_str = frontmatter.get("captured")
    if captured_str:
        try:
            captured = datetime.fromisoformat(captured_str.replace("Z", "+00:00"))
            age_days = (datetime.now(captured.tzinfo) - captured).days
            if age_days > RATING_GRACE_PERIOD_DAYS:
                return True, f"no rating, {age_days} days old (>{RATING_GRACE_PERIOD_DAYS})"
            else:
                return False, f"within grace period ({age_days}/{RATING_GRACE_PERIOD_DAYS} days)"
        except Exception:
            pass

    # Can't determine age, keep it to be safe
    return False, "unknown age"


@compare.command("cleanup")
@click.option("--prefix", "-p", default=None, help="Only remove notes with this prefix")
@click.option("--force", "-f", is_flag=True, help="Don't ask for confirmation")
@click.option("--all", "remove_all", is_flag=True, help="Remove entire _test_notes folder and all reports")
@click.option("--force-all", is_flag=True, help="Ignore ratings and delete everything")
@click.option("--dry-run", "-n", is_flag=True, help="Show what would be deleted without deleting")
def cleanup_comparison(prefix: str | None, force: bool, remove_all: bool, force_all: bool, dry_run: bool) -> None:
    """Remove comparison test notes and run directories from the vault.

    By default, respects the rating system for notes:
    - Keeps notes with unprocessed ratings (user_rating set, rating_processed=false)
    - Keeps unrated notes for 14 days to allow time for rating
    - Deletes notes where rating_processed=true (already captured to DB)
    - Deletes unrated notes older than 14 days

    Use --force-all to ignore ratings and delete everything.
    Use --dry-run to see what would be deleted.
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
    test_folder = vault_path / TEST_NOTES_FOLDER
    reports_folder = vault_path / "reports"

    # Find timestamped run directories in reports/
    run_directories: list[tuple[Path, datetime | None]] = []
    if reports_folder.exists():
        for item in reports_folder.iterdir():
            if item.is_dir():
                # Try to parse directory name as timestamp
                try:
                    dir_timestamp = datetime.strptime(item.name, "%Y-%m-%d_%H-%M-%S")
                    run_directories.append((item, dir_timestamp))
                except ValueError:
                    # Not a timestamped directory, skip it
                    pass

    # Find individual test notes (legacy support)
    all_test_notes: list[Path] = []

    if remove_all or prefix is None:
        # Check _test_notes folder for legacy notes
        if test_folder.exists():
            for md_file in test_folder.rglob("*.md"):
                all_test_notes.append(md_file)
    else:
        # Remove only notes with specific prefix (search entire vault for legacy cleanup)
        for md_file in vault_path.rglob("*.md"):
            if md_file.name.startswith(prefix):
                all_test_notes.append(md_file)

    if not all_test_notes and not run_directories:
        if prefix:
            click.echo(click.style("✓ ", fg="green") + f"No comparison notes found with prefix '{prefix}'")
        else:
            click.echo(click.style("✓ ", fg="green") + f"No test notes or run directories found")
        sys.exit(EXIT_SUCCESS)

    # Handle run directories
    dirs_to_delete: list[tuple[Path, str]] = []
    dirs_to_keep: list[tuple[Path, str]] = []

    if remove_all or force_all:
        # Delete all run directories
        for run_dir, dir_time in run_directories:
            time_str = dir_time.strftime("%Y-%m-%d %H:%M:%S") if dir_time else "unknown"
            dirs_to_delete.append((run_dir, f"created {time_str}"))
    else:
        # Check notes within each directory for rating status
        for run_dir, dir_time in run_directories:
            time_str = dir_time.strftime("%Y-%m-%d %H:%M:%S") if dir_time else "unknown"
            notes_in_dir = list(run_dir.glob("*.md"))

            # Check if any notes in this directory should be kept
            should_keep_dir = False
            keep_reasons = []

            for note in notes_in_dir:
                # Skip summary files
                if note.name.startswith("_run_summary"):
                    continue

                should_delete, reason = should_delete_test_note(note, ignore_ratings=False)
                if not should_delete:
                    should_keep_dir = True
                    keep_reasons.append(f"{note.name}: {reason}")

            if should_keep_dir:
                reason_summary = f"contains {len(keep_reasons)} note(s) to keep"
                dirs_to_keep.append((run_dir, reason_summary))
            else:
                dirs_to_delete.append((run_dir, f"created {time_str}, all notes deletable"))

    # Handle individual test notes (legacy)
    notes_to_delete: list[tuple[Path, str]] = []
    notes_to_keep: list[tuple[Path, str]] = []

    for note in all_test_notes:
        should_delete, reason = should_delete_test_note(note, ignore_ratings=force_all)
        if should_delete:
            notes_to_delete.append((note, reason))
        else:
            notes_to_keep.append((note, reason))

    # Show summary
    total_items = len(all_test_notes) + len(run_directories)
    click.echo(click.style(f"Found {total_items} items:", fg="cyan"))
    click.echo()

    if dirs_to_keep:
        click.echo(click.style(f"  Keeping {len(dirs_to_keep)} run directory(ies):", fg="yellow"))
        for run_dir, reason in dirs_to_keep[:5]:
            relative = run_dir.relative_to(vault_path)
            click.echo(f"    {relative} - {reason}")
        if len(dirs_to_keep) > 5:
            click.echo(f"    ... and {len(dirs_to_keep) - 5} more")
        click.echo()

    if notes_to_keep:
        click.echo(click.style(f"  Keeping {len(notes_to_keep)} individual note(s):", fg="yellow"))
        for note, reason in notes_to_keep[:5]:
            relative = note.relative_to(vault_path)
            click.echo(f"    {relative.name} - {reason}")
        if len(notes_to_keep) > 5:
            click.echo(f"    ... and {len(notes_to_keep) - 5} more")
        click.echo()

    to_delete_count = len(dirs_to_delete) + len(notes_to_delete)
    if to_delete_count > 0:
        click.echo(click.style(f"  Will delete:", fg="red"))

        if dirs_to_delete:
            click.echo(click.style(f"    {len(dirs_to_delete)} run directory(ies):", fg="red"))
            for run_dir, reason in dirs_to_delete[:5]:
                relative = run_dir.relative_to(vault_path)
                # Count notes in directory
                note_count = len([f for f in run_dir.glob("*.md") if not f.name.startswith("_run_summary")])
                html_count = len(list(run_dir.glob("*.html")))
                click.echo(f"      {relative} ({note_count} notes, {html_count} report) - {reason}")
            if len(dirs_to_delete) > 5:
                click.echo(f"      ... and {len(dirs_to_delete) - 5} more")
            click.echo()

        if notes_to_delete:
            click.echo(click.style(f"    {len(notes_to_delete)} individual note(s):", fg="red"))
            for note, reason in notes_to_delete[:10]:
                relative = note.relative_to(vault_path)
                click.echo(f"      {relative.name} - {reason}")
            if len(notes_to_delete) > 10:
                click.echo(f"      ... and {len(notes_to_delete) - 10} more")
    else:
        click.echo(click.style("  Nothing to delete", fg="green"))
        sys.exit(EXIT_SUCCESS)

    if dry_run:
        click.echo(click.style("\n  [DRY RUN - no files deleted]", fg="cyan"))
        sys.exit(EXIT_SUCCESS)

    if not force:
        click.confirm("\nDelete these items?", abort=True)

    deleted_dirs = 0
    deleted_notes = 0

    # Delete run directories
    import shutil
    for run_dir, reason in dirs_to_delete:
        try:
            shutil.rmtree(run_dir)
            deleted_dirs += 1
        except Exception as e:
            click.echo(click.style("✗ ", fg="red") + f"Failed to delete {run_dir.name}: {e}")

    # Delete individual notes
    for note, reason in notes_to_delete:
        try:
            note.unlink()
            deleted_notes += 1
        except Exception as e:
            click.echo(click.style("✗ ", fg="red") + f"Failed to delete {note.name}: {e}")

    click.echo(click.style(f"\n✓ ", fg="green") + f"Deleted {deleted_dirs} run directories and {deleted_notes} individual notes")

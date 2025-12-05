# Model Comparison & Performance Tracking

Claudsidian includes a comprehensive system for comparing AI models and tracking performance over time.

## Overview

The model comparison system helps you:
- **A/B test** different AI models on the same content
- **Track costs** per capture and per model
- **Measure quality** through automated scoring and user ratings
- **Optimize** your model selection for cost vs quality

## Quick Start

```bash
# See available models
claudsidian compare models

# Run a comparison
claudsidian compare run

# View performance stats
claudsidian ratings performance
```

## Model Comparison

### Running Comparisons

The `compare run` command captures test fixtures with two different model configurations:

```bash
# Default: Grok 4.1 Fast vs Haiku
claudsidian compare run

# Custom models
claudsidian compare run -s1 openrouter-haiku -s2 openrouter-grok-fast

# Test specific content type
claudsidian compare run --type video --count 3

# Include 3D model tests (requires Playwright)
claudsidian compare run --include-printable
```

### Test Fixtures

Test fixtures are defined in `test-captures.md` in your vault:

```markdown
## article
- [example_article](https://example.com/article)

## video
- [youtube_example](https://youtube.com/watch?v=xxx)

## printable
- [thingiverse_benchy](https://www.thingiverse.com/thing:763622)
```

### Comparison Output

Each run generates:
- **HTML report** with side-by-side comparisons
- **Markdown summary** with cost/time statistics
- **Test notes** prefixed with `_CMP_Run_A_` and `_CMP_Run_B_`

Reports are saved to: `{vault}/reports/{timestamp}/`

### Quality Analysis

The system uses AI to score each capture on:
- **Accuracy** - factual correctness
- **Completeness** - coverage of key points
- **Structure** - organization and formatting
- **Conciseness** - appropriate length

Scores are 1-5 and saved to the performance database.

### Gold Standards

Create gold standard notes for objective comparison:

1. Create folder: `{vault}/_test_notes/_gold_standards/`
2. Name files: `_GOLD_{fixture_name}.md`
3. Run comparisons with `--require-gold`

Gold standards provide a reference for quality scoring.

## Performance Tracking

### Automatic Tracking

Every capture automatically logs:
- **Model** used for summary and tags
- **Cost** in USD
- **Time** in seconds
- **Tokens** input and output
- **Content type**

Data stored in: `{vault}/.claudsidian/model_performance.json`

### Viewing Performance

```bash
# Summary of all models
claudsidian ratings performance

# Specific model details
claudsidian ratings performance -m "x-ai/grok-4.1-fast"

# Recent captures
claudsidian ratings recent -n 20
```

### OPUS Metric

OPUS (Optimized Performance per Unit Spend) measures efficiency:

```
OPUS = (quality_score / 5) / avg_cost_per_capture
```

- Higher is better
- Balances quality against cost
- Free models show ∞ if quality > 0

### Example Output

```
Model Performance Summary
  Total Captures: 42
  Total Spend: $0.1247

  Model                               Captures   Avg Cost     Avg Time   OPUS
  --------------------------------------------------------------------------------
  grok-4.1-fast                       25         $0.0028      4.2s       142.9
  claude-3-haiku                      17         $0.0012      2.1s       333.3
```

## User Ratings

### Rating Notes

1. Open any captured note in Obsidian
2. Find the `user_rating` field in frontmatter
3. Set a value from 1-5:

```yaml
user_rating: 4
rating_processed: false
```

### Collecting Ratings

```bash
# Process all unprocessed ratings
claudsidian ratings process

# Preview without saving
claudsidian ratings process --dry-run
```

### Rating Reports

```bash
# View all ratings
claudsidian ratings list

# Model statistics by rating
claudsidian ratings stats

# Generate full report
claudsidian ratings report -o quality_report.md
```

## Available Models

### Default Models (OpenRouter)

| Task | Model | Cost |
|------|-------|------|
| Summary | `x-ai/grok-4.1-fast` | ~$0.003/capture |
| Tags | `anthropic/claude-3-haiku` | ~$0.001/capture |
| Vision | `google/gemini-2.0-flash-exp:free` | Free |
| Quality | `google/gemini-2.0-flash-exp:free` | Free |

### Model Presets

```bash
claudsidian compare models
```

Available presets:
- `claude-sonnet-4` - High quality, higher cost
- `claude-haiku-3` - Fast and cheap
- `openrouter-haiku` - Haiku via OpenRouter
- `openrouter-sonnet` - Sonnet via OpenRouter
- `openrouter-grok-fast` - Grok 4.1 Fast
- `openrouter-gpt4o-mini` - GPT-4o Mini
- `openrouter-gemini-flash` - Gemini Flash

### Using Custom Models

Pass any OpenRouter model ID directly:

```bash
claudsidian compare run -s1 "anthropic/claude-3-opus" -s2 "meta-llama/llama-3-70b"
```

## Best Practices

### Finding the Right Model

1. Start with `compare run` using default models
2. Review the HTML report for quality differences
3. Check `ratings performance` for cost analysis
4. Rate a few notes manually for feedback
5. Adjust models based on your cost/quality preferences

### Cost Optimization

- Use free models for quality analysis
- Use Haiku for tags (fast, cheap, good enough)
- Reserve expensive models for summary only
- Track `ratings recent` to catch cost spikes

### Quality Assurance

- Create gold standards for important content types
- Run `--require-gold` comparisons periodically
- Process user ratings regularly
- Monitor OPUS scores over time

## Cleanup

Remove test notes after comparison:

```bash
# Remove processed test notes (keeps unrated for review)
claudsidian compare cleanup

# Remove all test notes including unrated
claudsidian compare cleanup --force-all
```

Test notes older than 14 days without ratings are automatically eligible for cleanup.

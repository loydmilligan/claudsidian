# Claudsidian Development Guidelines

AI-powered knowledge capture for Obsidian. Last updated: 2025-12-05

## Project Structure

```text
src/
├── cli/
│   ├── commands/
│   │   ├── capture.py      # URL capture command
│   │   ├── compare.py      # Model comparison A/B testing
│   │   ├── ratings.py      # Ratings and performance analytics
│   │   └── test_capture.py # Test fixtures and capture testing
│   └── main.py             # CLI entry point
├── core/
│   ├── ai/
│   │   ├── claude.py       # Claude direct API client
│   │   ├── openrouter.py   # OpenRouter API client
│   │   ├── router.py       # AI request routing with fallback
│   │   ├── vision.py       # Vision AI for screenshot analysis
│   │   └── prompts.py      # AI prompt templates
│   ├── extractors/
│   │   ├── article.py      # Article content extraction
│   │   ├── youtube.py      # YouTube video extraction
│   │   ├── github.py       # GitHub repo extraction
│   │   ├── news.py         # News article extraction
│   │   ├── walkthrough.py  # Tutorial/guide extraction
│   │   ├── printable.py    # 3D model HTTP extraction
│   │   └── printable_playwright.py  # 3D model browser extraction
│   ├── vault/
│   │   ├── writer.py       # Markdown note writer
│   │   └── backlinks.py    # Backlink discovery
│   ├── capture.py          # Main capture orchestration
│   ├── content_type.py     # Content type detection
│   ├── queue.py            # Capture queue management
│   └── config.py           # Configuration loading
├── models/
│   ├── config.py           # Configuration models
│   ├── capture.py          # Capture request models
│   ├── note.py             # Note and frontmatter models
│   ├── queue.py            # Queue item models
│   ├── model_performance.py # Performance tracking database
│   └── ratings.py          # User ratings database
├── server/
│   ├── app.py              # FastAPI application
│   └── routes/             # API route handlers
└── utils/
    └── url.py              # URL normalization utilities

tests/                      # Test suite
browser-extension/          # Chrome/Firefox extension
android/                    # Android share target app
specs/                      # Feature specifications
```

## Technologies

- **Python 3.11+** - Core runtime
- **httpx** - Async HTTP client
- **FastAPI** - Local HTTP server
- **Click** - CLI framework
- **OpenAI SDK** - OpenRouter API (default)
- **Anthropic SDK** - Claude direct API (optional)
- **Playwright** - Browser automation for 3D models
- **readability-lxml** - Article extraction
- **yt-dlp** - YouTube metadata
- **beautifulsoup4** - HTML parsing
- **Pydantic** - Data validation

## Commands

### Development
```bash
# Run CLI
python -m src.cli.main <command>

# Run tests
pytest

# Lint
ruff check .

# Type check
mypy src/
```

### CLI Commands
```bash
# Capture
claudsidian capture <url>
claudsidian capture <url> --type video

# Server
claudsidian serve
claudsidian serve --host 0.0.0.0 --port 8765

# Model comparison
claudsidian compare models
claudsidian compare run
claudsidian compare run -s1 openrouter-haiku -s2 openrouter-grok-fast
claudsidian compare cleanup

# Performance analytics
claudsidian ratings performance
claudsidian ratings recent
claudsidian ratings process

# Queue management
claudsidian queue list
claudsidian queue retry --all

# Configuration
claudsidian config show
claudsidian config init
claudsidian status
```

## Default Models (OpenRouter)

| Task | Model | ID |
|------|-------|-----|
| Summary | Grok 4.1 Fast | `x-ai/grok-4.1-fast` |
| Tags | Claude 3 Haiku | `anthropic/claude-3-haiku` |
| Vision | Gemini Flash | `google/gemini-2.0-flash-exp:free` |

## Key Files

- **src/core/capture.py** - Main capture orchestration, performance tracking
- **src/core/ai/router.py** - AI request routing with retry/fallback
- **src/cli/commands/compare.py** - Model comparison system
- **src/models/config.py** - Configuration and model presets
- **src/models/model_performance.py** - Performance database

## Code Style

- Python 3.11+ with type hints
- Async/await for IO operations
- Dataclasses for simple data structures
- Pydantic models for validation
- Click for CLI commands

## Architecture Notes

### Performance Tracking
Every capture automatically logs to `{vault}/.claudsidian/model_performance.json`:
- Cost, time, tokens
- Model used
- Content type
- Quality scores (from compare runs)

### AI Routing
1. OpenRouter is the default backend
2. Automatic retry with exponential backoff
3. Fallback to Claude direct API if OpenRouter fails

### Content Extraction
1. Detect content type from URL/content
2. Use appropriate extractor
3. For 3D models: Playwright captures screenshots, Vision AI analyzes

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->

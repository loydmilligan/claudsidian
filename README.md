# Claudsidian

AI-powered knowledge capture for Obsidian. Capture URLs from anywhere and automatically create well-formatted, summarized notes in your vault.

## Features

### Core Capture
- **One-click capture** from browser extension
- **CLI capture** for terminal users
- **Inbox file watching** - drop URLs in a file, they get processed automatically
- **Android share target** - capture from mobile via local network
- **Smart content detection** - articles, YouTube videos, GitHub repos, news, tutorials, 3D models
- **AI-powered summaries** - using OpenRouter (default) or Claude
- **Automatic tagging** - relevant tags generated from content
- **Backlink discovery** - finds related notes in your vault

### Model Comparison & Analytics
- **A/B model testing** - compare different AI models side-by-side
- **Performance tracking** - automatic cost, speed, and quality metrics
- **OPUS efficiency metric** - quality-adjusted cost efficiency ranking
- **User ratings** - rate notes to build quality feedback loop
- **Quality reports** - analyze model performance over time

### 3D Model Extraction
- **Playwright browser automation** - captures Thingiverse, Printables sites
- **Vision AI analysis** - extracts model info from screenshots
- **Non-headless mode** - bypasses Cloudflare bot protection

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/claudsidian.git
cd claudsidian

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install
pip install -e .
```

## Quick Start

### 1. Configure

```bash
# Interactive setup
claudsidian config init

# Or set manually
claudsidian config vault_path /path/to/your/vault
claudsidian config claude_api_key sk-ant-your-key
claudsidian config openrouter_api_key sk-or-your-key
```

### 2. Verify

```bash
claudsidian status
```

### 3. Capture

```bash
# Capture a URL
claudsidian capture https://example.com/article

# Force content type
claudsidian capture https://youtube.com/watch?v=xxx --type video
```

## Commands

### `claudsidian capture <url>`

Capture a URL and create a note.

```bash
claudsidian capture <url>              # Auto-detect content type
claudsidian capture <url> --type video # Force type (article|video|repo|news|walkthrough|printable)
claudsidian capture <url> --quiet      # Suppress output except errors
```

### `claudsidian serve`

Start the HTTP server for browser extension and mobile capture.

```bash
claudsidian serve                      # localhost:8765
claudsidian serve --port 9000          # Custom port
claudsidian serve --host 0.0.0.0       # Allow LAN connections
claudsidian serve --host 0.0.0.0 -a    # LAN + mDNS discovery for Android
```

### `claudsidian watch`

Watch inbox file for URLs to capture.

```bash
claudsidian watch                      # Watch default inbox.md
claudsidian watch --file urls.md       # Watch custom file
```

### `claudsidian queue`

Manage the capture queue.

```bash
claudsidian queue list                 # List all items
claudsidian queue list --status failed # Filter by status
claudsidian queue retry <id>           # Retry specific item
claudsidian queue retry --all          # Retry all failed
claudsidian queue remove <id>          # Remove item
claudsidian queue clear                # Clear completed
claudsidian queue clear --status all   # Clear everything
```

### `claudsidian config`

Manage configuration.

```bash
claudsidian config show                # Show current config
claudsidian config init                # Interactive setup
claudsidian config <key> <value>       # Set a value
claudsidian config vault_path /path    # Set vault path
claudsidian config folders.video Media # Set folder for video notes
```

### `claudsidian status`

Show system status.

```bash
claudsidian status                     # Show config, server, queue status
```

### `claudsidian compare`

Compare AI models for quality and cost.

```bash
claudsidian compare models                          # List available model presets
claudsidian compare run                             # Run comparison with defaults
claudsidian compare run -s1 openrouter-haiku -s2 openrouter-grok-fast
claudsidian compare run --type article --count 2   # Test specific content type
claudsidian compare run --include-printable        # Include 3D model tests (requires Playwright)
claudsidian compare cleanup                         # Remove test notes
claudsidian compare cleanup --force-all            # Remove all test notes including unrated
```

### `claudsidian ratings`

Manage ratings and view performance analytics.

```bash
claudsidian ratings performance                    # Show model performance summary
claudsidian ratings performance -m "x-ai/grok-4.1-fast"  # Stats for specific model
claudsidian ratings recent                         # Show recent captures with costs
claudsidian ratings process                        # Collect user ratings from notes
claudsidian ratings report                         # Generate quality report
claudsidian ratings stats                          # Show rating statistics
claudsidian ratings list                           # List all ratings
```

### `claudsidian test-capture`

Test capture functionality.

```bash
claudsidian test-capture                           # Run test captures
claudsidian test-capture --type video --count 2   # Test specific content type
```

### Global Options

```bash
claudsidian -v <command>               # Verbose output (INFO level)
claudsidian -d <command>               # Debug output (DEBUG level)
claudsidian --version                  # Show version
claudsidian --help                     # Show help
```

## Content Types

| Type | Sources | Note Location |
|------|---------|---------------|
| Article | Any webpage | `Learning/` |
| Video | YouTube | `Videos/` |
| Repository | GitHub | `Projects/` |
| News | CNN, BBC, Reuters, etc. | `News/` |
| Walkthrough | Tutorials, how-tos | `Guides/` |
| 3D Model | Thingiverse, Printables, Cults3D | `3D-Models/` |

## API Endpoints

When running `claudsidian serve`:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API info |
| `/health` | GET | Health check |
| `/capture` | POST | Capture a URL |
| `/status` | GET | System status |
| `/queue` | GET | List queue items |
| `/queue/{id}` | GET | Get queue item |
| `/queue/{id}` | DELETE | Remove queue item |
| `/queue/retry` | POST | Retry all failed |
| `/queue/retry/{id}` | POST | Retry specific item |

### Capture Request

```bash
curl -X POST http://localhost:8765/capture \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/article"}'
```

## Browser Extension

1. Start the server: `claudsidian serve`
2. Load extension from `browser-extension/` folder:
   - Chrome: `chrome://extensions` → Load unpacked
   - Firefox: `about:debugging` → Load Temporary Add-on

## Android App

See [android/README.md](android/README.md) for mobile capture setup.

## Configuration

Config file: `~/.config/claudsidian/config.json`

| Key | Description | Default |
|-----|-------------|---------|
| `vault_path` | Path to Obsidian vault | (required) |
| `claude_api_key` | Anthropic API key | - |
| `openrouter_api_key` | OpenRouter API key | - |
| `server_port` | Server port | 8765 |
| `vision_model` | Model for image analysis | `google/gemini-2.0-flash-exp:free` |
| `folders.article` | Article notes folder | `Learning` |
| `folders.video` | Video notes folder | `Videos` |
| `folders.repo` | Repository notes folder | `Projects` |
| `folders.news` | News notes folder | `News` |
| `folders.walkthrough` | Tutorial notes folder | `Guides` |
| `folders.printable` | 3D model notes folder | `3D-Models` |

## Default AI Models

Claudsidian uses OpenRouter by default (no direct Claude API calls):

| Task | Default Model | Model ID |
|------|---------------|----------|
| Summary | Grok 4.1 Fast | `x-ai/grok-4.1-fast` |
| Tags | Claude 3 Haiku | `anthropic/claude-3-haiku` |
| Vision | Gemini Flash | `google/gemini-2.0-flash-exp:free` |
| Quality Analysis | Gemini Flash | `google/gemini-2.0-flash-exp:free` |

Available model presets: `claudsidian compare models`

## Performance Tracking

Every capture automatically tracks:
- **Cost** - API call cost in USD
- **Time** - Response time in seconds
- **Tokens** - Input/output token counts
- **Quality** - Scores from compare runs (1-5)
- **OPUS** - Efficiency metric: `(quality/5) / cost`

View stats: `claudsidian ratings performance`

Data stored in: `{vault}/.claudsidian/model_performance.json`

## Troubleshooting

**"API key not configured"**
```bash
claudsidian config claude_api_key YOUR_KEY
```

**"Vault path not found"**
```bash
claudsidian config vault_path /correct/path
```

**"Port already in use"**
```bash
claudsidian serve --port 8766
```

**Enable debug logging**
```bash
claudsidian -d capture https://example.com
```

## Requirements

- Python 3.11+
- An Obsidian vault
- At least one API key (Claude or OpenRouter)

### Optional Dependencies

- **Playwright** - For 3D model capture (Thingiverse, Printables)
  ```bash
  pip install playwright
  playwright install chromium
  ```

## License

MIT

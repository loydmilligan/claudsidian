# Quickstart: Claudsidian

Get Claudsidian running in 5 minutes.

## Prerequisites

- Python 3.11+
- An Obsidian vault (any folder with markdown files works)
- At least one API key: Claude (Anthropic) or OpenRouter

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/claudsidian.git
cd claudsidian

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .
```

## Initial Setup

Run the interactive configuration wizard:

```bash
claudsidian config init
```

This will prompt you for:
1. **Vault path**: Full path to your Obsidian vault folder
2. **Claude API key**: Get one at https://console.anthropic.com/
3. **OpenRouter API key**: Get one at https://openrouter.ai/keys

Alternatively, set configuration manually:

```bash
claudsidian config vault_path /path/to/your/vault
claudsidian config claude_api_key sk-ant-your-key-here
claudsidian config openrouter_api_key sk-or-your-key-here
```

## Verify Setup

```bash
claudsidian status
```

You should see:
```
Claudsidian v1.0.0

Configuration:
  Vault: /path/to/your/vault ✓
  Claude API: configured ✓
  OpenRouter API: configured ✓
```

## Your First Capture

### Via CLI

```bash
claudsidian capture https://example.com/interesting-article
```

Check your vault - a new note should appear in the `Learning/` folder.

### Via Browser Extension

1. Start the local server:
   ```bash
   claudsidian serve
   ```

2. Install the browser extension:
   - Chrome: Load unpacked from `browser-extension/`
   - Firefox: Load temporary add-on from `browser-extension/manifest.json`

3. Navigate to any article and click the Claudsidian extension icon.

### Via Inbox File

1. Start the file watcher:
   ```bash
   claudsidian watch
   ```

2. Add URLs to `inbox.md` in your vault root:
   ```markdown
   # Inbox

   - https://example.com/article-to-read
   - https://youtube.com/watch?v=example
   ```

3. URLs will be processed automatically and removed from the inbox.

## Common Commands

```bash
# Capture a URL
claudsidian capture <url>

# Force a specific content type
claudsidian capture <url> --type video

# Start server for browser extension
claudsidian serve

# Watch inbox file
claudsidian watch

# Check queue status
claudsidian queue list

# Retry failed captures
claudsidian queue retry --all

# Enable verbose logging (helpful for troubleshooting)
claudsidian -v capture <url>

# Enable debug logging (very detailed)
claudsidian -d capture <url>
```

## Folder Structure

After capturing different content types, your vault will look like:

```
MyVault/
├── Learning/           # Articles
│   └── intro-to-python.md
├── Videos/             # YouTube
│   └── python-tutorial.md
├── Projects/           # GitHub repos
│   └── awesome-project.md
├── News/               # News articles
│   └── 2025-12-01-tech-news.md
├── Guides/             # Walkthroughs
│   └── how-to-setup-docker.md
├── 3D-Models/          # Printables
│   └── cool-model.md
└── inbox.md            # Watched inbox
```

## Next Steps

- Customize folder names: `claudsidian config folders.article MyArticles`
- Set up the server to start on boot (see docs/autostart.md)
- Configure the Android app for mobile capture (see docs/android.md)

## Troubleshooting

**"API key not configured"**
```bash
claudsidian config claude_api_key YOUR_KEY
# or
claudsidian config openrouter_api_key YOUR_KEY
```

**"Vault path not found"**
```bash
claudsidian config vault_path /correct/path/to/vault
```

**"Port already in use"**
```bash
claudsidian serve --port 8766
```

**Server not responding to browser extension**
- Make sure `claudsidian serve` is running
- Check the server is on the correct port (default: 8765)
- Ensure browser extension is pointed to `http://localhost:8765`

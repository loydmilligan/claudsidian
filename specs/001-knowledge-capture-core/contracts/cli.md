# CLI Contract: Claudsidian

## Command Structure

```
claudsidian <command> [options] [arguments]
```

## Commands

### capture

Capture a URL and create a note in the vault.

```
claudsidian capture <url> [options]
```

**Arguments**:
- `<url>` (required): URL to capture

**Options**:
- `--type, -t <type>`: Force content type (article|video|repo|news|walkthrough|printable)
- `--async, -a`: Return immediately, process in background
- `--quiet, -q`: Suppress output except errors

**Output (success)**:
```
✓ Captured: Introduction to Python
  Type: article
  Path: Learning/introduction-to-python.md
  Tags: python, tutorial, programming
```

**Output (duplicate)**:
```
⚠ Note already exists: Learning/introduction-to-python.md
```

**Output (error)**:
```
✗ Error: Could not fetch URL (404 Not Found)
```

**Exit Codes**:
- 0: Success
- 1: General error
- 2: Invalid arguments
- 3: Duplicate URL
- 4: API error (queued for retry)

---

### serve

Start the local HTTP server.

```
claudsidian serve [options]
```

**Options**:
- `--port, -p <port>`: Port to listen on (default: 8765)
- `--host <host>`: Host to bind to (default: 127.0.0.1)
- `--daemon, -d`: Run in background

**Output**:
```
Claudsidian server running at http://127.0.0.1:8765
Press Ctrl+C to stop
```

**Exit Codes**:
- 0: Clean shutdown
- 1: Error (port in use, config error)

---

### watch

Watch inbox file for URLs to capture.

```
claudsidian watch [options]
```

**Options**:
- `--file, -f <path>`: Inbox file to watch (default: inbox.md in vault root)
- `--daemon, -d`: Run in background

**Output**:
```
Watching: /path/to/vault/inbox.md
[10:30:15] Processing: https://example.com/article
[10:30:18] ✓ Captured: Article Title → Learning/article-title.md
```

---

### config

View or set configuration.

```
claudsidian config [key] [value]
```

**Subcommands**:
- `claudsidian config`: Show all configuration
- `claudsidian config <key>`: Show specific key
- `claudsidian config <key> <value>`: Set key to value
- `claudsidian config --init`: Interactive setup wizard

**Keys**:
- `vault_path`: Path to Obsidian vault
- `claude_api_key`: Anthropic API key
- `openrouter_api_key`: OpenRouter API key
- `server_port`: HTTP server port
- `folders.article`: Folder for articles (default: Learning)
- `folders.video`: Folder for videos (default: Videos)
- `folders.repo`: Folder for repos (default: Projects)
- `folders.news`: Folder for news (default: News)
- `folders.walkthrough`: Folder for guides (default: Guides)
- `folders.printable`: Folder for 3D models (default: 3D-Models)

**Output (show all)**:
```
vault_path: /home/user/Obsidian/MyVault
claude_api_key: sk-ant-***************
openrouter_api_key: sk-or-***************
server_port: 8765
folders:
  article: Learning
  video: Videos
  repo: Projects
  news: News
  walkthrough: Guides
  printable: 3D-Models
```

---

### queue

Manage the capture queue.

```
claudsidian queue [subcommand]
```

**Subcommands**:
- `claudsidian queue`: List all queued items
- `claudsidian queue retry`: Retry all failed items
- `claudsidian queue clear`: Clear completed/failed items
- `claudsidian queue remove <id>`: Remove specific item

**Output (list)**:
```
Queue (3 items):
  [pending]    abc123  https://example.com/article1
  [failed]     def456  https://example.com/article2 (Error: API timeout)
  [processing] ghi789  https://example.com/article3
```

---

### status

Check system status.

```
claudsidian status
```

**Output**:
```
Claudsidian v1.0.0

Configuration:
  Vault: /home/user/Obsidian/MyVault ✓
  Claude API: configured ✓
  OpenRouter API: configured ✓

Server: running on http://127.0.0.1:8765
Watcher: running (watching inbox.md)
Queue: 2 pending, 0 failed
```

---

### compare

Compare AI models for quality and cost.

```
claudsidian compare <subcommand> [options]
```

**Subcommands**:

#### `compare models`
List available model presets.

```
claudsidian compare models
```

**Output**:
```
Available Model Presets:
  claude-sonnet-4      → claude-sonnet-4-20250514
  openrouter-haiku     → anthropic/claude-3-haiku
  openrouter-grok-fast → x-ai/grok-4.1-fast
  ...
```

#### `compare run`
Run model comparison captures.

```
claudsidian compare run [options]
```

**Options**:
- `--type, -t <type>`: Only test this content type
- `--count, -n <num>`: Fixtures per type (default: 1)
- `--summary-model-1, -s1 <model>`: First summary model (default: openrouter-grok-fast)
- `--summary-model-2, -s2 <model>`: Second summary model (default: openrouter-haiku)
- `--tags-model-1, -t1 <model>`: First tags model (default: openrouter-haiku)
- `--tags-model-2, -t2 <model>`: Second tags model (default: openrouter-haiku)
- `--comparison-model, -c <model>`: Model for quality analysis
- `--skip-quality`: Skip AI quality comparison
- `--require-gold`: Only analyze fixtures with gold standards
- `--include-printable`: Include printable content (requires Playwright)
- `--prefix, -p <prefix>`: Prefix for test notes (default: _CMP_)

**Output**:
```
Model Comparison Test
Fixtures: 5 × 2 runs = 10 captures

  Run A: openrouter-grok-fast / openrouter-haiku
  Run B: openrouter-haiku / openrouter-haiku

Capturing...
✓ Article: example-article (Run A: 2.3s, Run B: 1.8s)

Summary:
  Run A: 5 captures, $0.0042
  Run B: 5 captures, $0.0018

Report:
  reports/2025-12-05_14-30-00/report.html
```

#### `compare cleanup`
Remove comparison test notes.

```
claudsidian compare cleanup [options]
```

**Options**:
- `--force-all`: Remove all test notes including unrated ones

---

### ratings

Manage ratings and performance analytics.

```
claudsidian ratings <subcommand> [options]
```

**Subcommands**:

#### `ratings performance`
Show model performance metrics.

```
claudsidian ratings performance [options]
```

**Options**:
- `--model, -m <model>`: Filter by model ID

**Output**:
```
Model Performance Summary
  Total Captures: 25
  Total Spend: $0.0842

  Model                               Captures   Avg Cost     Avg Time   OPUS
  --------------------------------------------------------------------------------
  grok-4.1-fast                       15         $0.0028      4.2s       178.6
  claude-3-haiku                      10         $0.0012      2.1s       416.7

OPUS = (quality/5) / cost - higher is better
```

#### `ratings recent`
Show recent capture performance.

```
claudsidian ratings recent [options]
```

**Options**:
- `--limit, -n <num>`: Number of captures to show (default: 10)

**Output**:
```
Recent Captures (10):
  Time         Title                          Model                Cost       Time
  -------------------------------------------------------------------------------------
  2025-12-05   Example Article                grok-4.1-fast        $0.0028    4.2s  ✓
```

#### `ratings process`
Collect user ratings from vault notes.

```
claudsidian ratings process [options]
```

**Options**:
- `--dry-run`: Show what would be processed without saving

#### `ratings report`
Generate quality report.

```
claudsidian ratings report [options]
```

**Options**:
- `--output, -o <path>`: Output file for report

#### `ratings stats`
Show rating statistics.

#### `ratings list`
List all ratings.

```
claudsidian ratings list [options]
```

**Options**:
- `--limit, -n <num>`: Number of ratings to show (default: 20)
- `--model, -m <model>`: Filter by model ID

---

### test-capture

Test capture functionality with sample URLs.

```
claudsidian test-capture [options]
```

**Options**:
- `--type, -t <type>`: Test specific content type
- `--count, -n <num>`: Number of fixtures to test (default: 1)
- `--model, -m <model>`: Model to use for capture

---

## Global Options

Available for all commands:

- `--help, -h`: Show help
- `--version`: Show version
- `-v, --verbose`: Enable verbose output (INFO level)
- `-d, --debug`: Enable debug output (DEBUG level)

---

## Environment Variables

- `CLAUDSIDIAN_CONFIG`: Path to config file
- `CLAUDSIDIAN_VAULT`: Override vault path
- `CLAUDE_API_KEY`: Anthropic API key (fallback)
- `OPENROUTER_API_KEY`: OpenRouter API key (fallback)

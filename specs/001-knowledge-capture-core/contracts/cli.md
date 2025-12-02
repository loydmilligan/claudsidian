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

## Global Options

Available for all commands:

- `--help, -h`: Show help
- `--version, -v`: Show version
- `--config, -c <path>`: Use alternate config file
- `--verbose`: Enable debug output

---

## Environment Variables

- `CLAUDSIDIAN_CONFIG`: Path to config file
- `CLAUDSIDIAN_VAULT`: Override vault path
- `CLAUDE_API_KEY`: Anthropic API key (fallback)
- `OPENROUTER_API_KEY`: OpenRouter API key (fallback)

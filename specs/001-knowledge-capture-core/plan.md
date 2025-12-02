# Implementation Plan: Claudsidian Knowledge Capture Core

**Branch**: `001-knowledge-capture-core` | **Date**: 2025-12-01 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-knowledge-capture-core/spec.md`

## Summary

Build an AI-powered knowledge capture tool that writes directly to an Obsidian vault. The system accepts URLs from multiple sources (browser extension, CLI, inbox file, Android app), processes them through AI (Claude for complex tasks, OpenRouter for simple ones), and outputs organized markdown notes with auto-generated tags, summaries, and backlinks. Core architecture: Python CLI + simple HTTP server for local processing.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: httpx (HTTP client), FastAPI (local server), anthropic (Claude SDK), openai (OpenRouter), readability-lxml (article extraction), yt-dlp (YouTube), beautifulsoup4 (scraping)
**Storage**: Local filesystem (Obsidian vault folder) + JSON config file
**Testing**: pytest (optional per constitution - add when stability matters)
**Target Platform**: Linux (primary), macOS, Windows (WSL supported)
**Project Type**: Single project with CLI + local HTTP server
**Performance Goals**: Capture-to-note in <60 seconds, server response <500ms
**Constraints**: Local-only (no cloud beyond AI APIs), single-user
**Scale/Scope**: Single user, ~1000s of notes over time

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Requirement | Status |
|-----------|-------------|--------|
| I. Frictionless Capture | ≤3 user actions for any capture | ✅ PASS - Browser: 1 click, CLI: 1 command, Inbox: drop file |
| II. Automation First | AI handles organization | ✅ PASS - Auto-tags, auto-folders, auto-backlinks |
| III. Simplicity Over Elegance | Simplest viable architecture | ✅ PASS - Direct file writes, simple HTTP server, no plugins |
| IV. Proactive AI Collaboration | Discuss significant decisions | ✅ PASS - Technology choices discussed with user |
| V. Local-First | No cloud beyond AI APIs | ✅ PASS - All data in local vault, local network only |
| VI. Pragmatic Development | No testing overhead | ✅ PASS - Tests optional, ship when ready |
| VII. Content-Type Aware | Specialized handling per type | ✅ PASS - 6 content types with specific pipelines |

**Gate Status**: PASSED - Proceed to Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/001-knowledge-capture-core/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (API specs)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/
├── cli/
│   ├── __init__.py
│   ├── main.py           # CLI entry point (claudsidian command)
│   └── commands/
│       ├── capture.py    # claudsidian capture <url>
│       ├── serve.py      # claudsidian serve (start HTTP server)
│       └── config.py     # claudsidian config
├── server/
│   ├── __init__.py
│   ├── app.py            # HTTP server (FastAPI)
│   └── routes/
│       └── capture.py    # POST /capture endpoint
├── core/
│   ├── __init__.py
│   ├── capture.py        # Main capture orchestration
│   ├── content_type.py   # Content type detection
│   ├── extractors/       # Content extraction per type
│   │   ├── article.py
│   │   ├── youtube.py
│   │   ├── github.py
│   │   ├── news.py
│   │   ├── walkthrough.py
│   │   └── printable.py
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── router.py     # Route to Claude vs OpenRouter
│   │   ├── claude.py     # Claude API wrapper
│   │   └── openrouter.py # OpenRouter API wrapper
│   └── vault/
│       ├── __init__.py
│       ├── writer.py     # Write markdown to vault
│       ├── backlinks.py  # Find and create backlinks
│       └── templates/    # Note templates per content type
├── models/
│   ├── __init__.py
│   ├── capture.py        # Capture request/response
│   ├── note.py           # Note structure
│   └── config.py         # Configuration schema
└── utils/
    ├── __init__.py
    └── url.py            # URL parsing utilities

config/
└── claudsidian.json      # User configuration (vault path, API keys)

browser-extension/        # Chrome/Firefox extension (P1)
├── manifest.json
├── popup.html
├── popup.js
└── background.js

android/                  # Android share target app (P8 - later)
└── [Flutter project - chosen for faster development and simpler implementation]
```

**Structure Decision**: Single Python project with CLI entry point. Browser extension is separate JavaScript project. Android app deferred to P8 priority.

## Complexity Tracking

No violations to track - architecture follows Simplicity principle.

# Research: Claudsidian Knowledge Capture Core

**Date**: 2025-12-01
**Branch**: `001-knowledge-capture-core`

## Research Questions

1. Best Python libraries for article content extraction
2. YouTube transcript extraction approach
3. GitHub API vs scraping for repo metadata
4. OpenRouter API integration patterns
5. Browser extension architecture for Chrome/Firefox
6. File watching approach for inbox monitoring
7. Markdown generation and Obsidian compatibility

---

## 1. Article Content Extraction

**Decision**: Use `readability-lxml` for main content extraction, `httpx` for fetching

**Rationale**:
- `readability-lxml` is the Python port of Mozilla's Readability.js (used by Firefox Reader View)
- Extracts main article content, removes ads/navigation/sidebars
- Battle-tested on millions of articles
- Falls back gracefully when content structure is unusual

**Alternatives Considered**:
- `newspaper3k`: More features but heavier, less maintained
- `trafilatura`: Good but readability has better edge case handling
- `beautifulsoup4` alone: Requires custom extraction logic per site

**Implementation Notes**:
```python
from readability import Document
import httpx

response = httpx.get(url)
doc = Document(response.text)
title = doc.title()
content = doc.summary()  # HTML of main content
```

---

## 2. YouTube Transcript Extraction

**Decision**: Use `yt-dlp` for metadata + `youtube-transcript-api` for transcripts

**Rationale**:
- `yt-dlp` is actively maintained fork of youtube-dl, handles all YouTube edge cases
- `youtube-transcript-api` extracts auto-generated and manual captions
- No YouTube API key required (scraping approach)
- Handles private videos gracefully (returns error, doesn't crash)

**Alternatives Considered**:
- YouTube Data API v3: Requires API key, quota limits, doesn't include transcripts
- `pytube`: Less maintained than yt-dlp
- `whisper` for audio transcription: Overkill when captions exist

**Implementation Notes**:
```python
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp

# Get metadata
with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
    info = ydl.extract_info(url, download=False)

# Get transcript
video_id = extract_video_id(url)
transcript = YouTubeTranscriptApi.get_transcript(video_id)
```

---

## 3. GitHub Repository Metadata

**Decision**: Use GitHub API (unauthenticated) for basic metadata, fall back to scraping

**Rationale**:
- Unauthenticated GitHub API allows 60 requests/hour (sufficient for personal use)
- Returns structured JSON with stars, language, description, topics
- README content available via separate endpoint
- Scraping fallback for rate limit scenarios

**Alternatives Considered**:
- Authenticated API: Unnecessary complexity for single-user tool
- Pure scraping: More fragile, GitHub changes HTML frequently
- `PyGithub` library: Adds dependency when simple httpx calls suffice

**Implementation Notes**:
```python
# GET https://api.github.com/repos/{owner}/{repo}
# GET https://api.github.com/repos/{owner}/{repo}/readme (base64 encoded)
```

---

## 4. OpenRouter API Integration

**Decision**: Use OpenRouter's OpenAI-compatible API with `openai` Python SDK

**Rationale**:
- OpenRouter provides OpenAI-compatible endpoint
- Can use existing `openai` Python package (no new dependency)
- Easy model switching (claude-3-haiku for cheap, claude-3-opus for complex)
- Cost tracking built into OpenRouter dashboard

**Alternatives Considered**:
- Direct httpx calls: More code, same result
- Custom wrapper: Unnecessary when openai SDK works

**Implementation Notes**:
```python
from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=openrouter_api_key,
)

response = client.chat.completions.create(
    model="anthropic/claude-3-haiku",  # or claude-3-opus for complex
    messages=[{"role": "user", "content": prompt}]
)
```

**AI Routing Strategy**:
- OpenRouter (claude-3-haiku): Content type detection, basic extraction, template filling
- Claude API direct (claude-3-sonnet): Summarization, tag generation, backlink discovery

---

## 5. Browser Extension Architecture

**Decision**: Manifest V3 Chrome extension with Firefox compatibility

**Rationale**:
- Manifest V3 is required for new Chrome extensions
- Firefox supports Manifest V3 with minor tweaks
- Single-click capture: extension sends URL to local server
- No content scripts needed (just URL capture)

**Alternatives Considered**:
- Bookmarklet: Blocked by many sites' CSP
- Native messaging: More complex, unnecessary for simple URL passing

**Implementation Notes**:
```javascript
// popup.js
chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
    fetch('http://localhost:8765/capture', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({url: tabs[0].url})
    });
});
```

**Port Choice**: 8765 (unlikely to conflict, easy to remember)

---

## 6. Inbox File Watching

**Decision**: Use `watchdog` library for cross-platform file system events

**Rationale**:
- `watchdog` handles inotify (Linux), FSEvents (macOS), ReadDirectoryChangesW (Windows)
- Can watch single file (inbox.md) or directory
- Debounce rapid changes to avoid duplicate processing

**Alternatives Considered**:
- Polling: Inefficient, delays detection
- `inotify` directly: Linux-only
- `pyinotify`: Less maintained than watchdog

**Implementation Notes**:
```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class InboxHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('inbox.md'):
            process_inbox()
```

---

## 7. Markdown Generation & Obsidian Compatibility

**Decision**: Generate plain markdown with YAML frontmatter, use Obsidian wiki-link syntax

**Rationale**:
- Obsidian reads any markdown, no special format required
- YAML frontmatter for metadata (tags, source URL, date)
- Wiki-links `[[Note Name]]` for backlinks (Obsidian native format)
- Keep templates simple, let Obsidian handle rendering

**Alternatives Considered**:
- Obsidian plugin: Adds complexity, not needed for file writing
- Standard markdown links: Less discoverable in Obsidian graph view

**Template Structure**:
```markdown
---
source: https://example.com/article
captured: 2025-12-01T10:30:00
type: article
tags:
  - python
  - machine-learning
---

# Article Title

## Summary

[AI-generated summary]

## Key Points

- Point 1
- Point 2

## Related Notes

- [[Related Note 1]]
- [[Related Note 2]]

---
*Source: [Original Article](https://example.com/article)*
```

---

## Resolved Unknowns

| Unknown | Resolution |
|---------|------------|
| Article extraction library | readability-lxml |
| YouTube transcript method | youtube-transcript-api + yt-dlp |
| GitHub data source | Unauthenticated API with scraping fallback |
| OpenRouter integration | openai SDK with custom base_url |
| Browser extension approach | Manifest V3, simple URL POST |
| File watching | watchdog library |
| Markdown format | Plain MD + YAML frontmatter + wiki-links |

All NEEDS CLARIFICATION items resolved. Ready for Phase 1.

# Data Model: Claudsidian Knowledge Capture Core

**Date**: 2025-12-01
**Branch**: `001-knowledge-capture-core`

## Overview

Claudsidian uses a file-based data model - all data is stored as files in the user's Obsidian vault or local config directory. No database required.

---

## Entities

### 1. CaptureRequest

Represents an incoming capture request from any source.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| url | string (URL) | Yes | The URL to capture |
| source | enum | Yes | Where request came from: `browser`, `cli`, `inbox`, `android` |
| timestamp | datetime | Yes | When request was received |
| force_type | enum | No | Override auto-detection: `article`, `video`, `repo`, `news`, `walkthrough`, `printable` |

**Validation Rules**:
- `url` must be a valid HTTP/HTTPS URL
- `source` must be one of the defined enum values
- `force_type` if provided must match a supported content type

---

### 2. ContentType

Classification of captured content determining processing pipeline.

| Value | Detection Patterns | Processing Pipeline |
|-------|-------------------|---------------------|
| `article` | Default for most URLs, blog domains | readability extraction → summarize → tag |
| `video` | youtube.com, youtu.be, vimeo.com | yt-dlp metadata → transcript → summarize |
| `repo` | github.com/{owner}/{repo} | GitHub API → README extract → tag |
| `news` | news domains (CNN, BBC, etc.), /news/ paths | readability → key facts → date extract |
| `walkthrough` | Contains "how to", "tutorial", "guide" | readability → step extraction → prerequisites |
| `printable` | thingiverse.com, printables.com, cults3d.com | scrape metadata → print settings |

**Detection Priority**:
1. User-specified `force_type` (highest)
2. Domain-based matching (YouTube, GitHub, etc.)
3. Content analysis (keywords, structure)
4. Default to `article`

---

### 3. Note

The markdown output stored in the vault.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| title | string | Yes | Note title (also filename) |
| content | string | Yes | Markdown body |
| frontmatter | Frontmatter | Yes | YAML metadata block |
| file_path | string | Yes | Relative path in vault |

**Frontmatter Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| source | string (URL) | Yes | Original URL |
| captured | datetime | Yes | ISO 8601 capture timestamp |
| type | ContentType | Yes | Content type classification |
| tags | list[string] | Yes | Auto-generated tags |
| summary | string | No | One-line summary for preview |

**File Path Rules**:
- Articles: `Learning/{sanitized-title}.md`
- Videos: `Videos/{sanitized-title}.md`
- Repos: `Projects/{sanitized-title}.md`
- News: `News/{YYYY-MM-DD}-{sanitized-title}.md`
- Walkthroughs: `Guides/{sanitized-title}.md`
- Printables: `3D-Models/{sanitized-title}.md`

**Title Sanitization**:
- Remove special characters except `-` and `_`
- Replace spaces with `-`
- Truncate to 100 characters
- Append `-1`, `-2` etc. for duplicates

---

### 4. Tag

Labels for organizing and searching notes.

| Field | Type | Description |
|-------|------|-------------|
| name | string | Tag name (lowercase, hyphenated) |
| category | enum | `topic`, `technology`, `source`, `custom` |

**Tag Generation Rules**:
- Extract from content via AI analysis
- Normalize: lowercase, replace spaces with hyphens
- Limit: Maximum 10 tags per note
- Categories:
  - `topic`: Subject matter (e.g., `machine-learning`, `politics`)
  - `technology`: Tech stack (e.g., `python`, `react`, `docker`)
  - `source`: Origin domain (e.g., `medium`, `github`, `youtube`)

---

### 5. Backlink

Connection between notes.

| Field | Type | Description |
|-------|------|-------------|
| from_note | string | Source note path |
| to_note | string | Target note path |
| reason | enum | `topic`, `tag`, `explicit` |

**Backlink Discovery**:
1. Search vault for notes with overlapping tags (≥2 shared tags)
2. Search vault for notes with similar titles (fuzzy match)
3. AI analysis of content similarity (optional, expensive)

**Backlink Format**:
```markdown
## Related Notes

- [[Other Note Title]] - shared tags: #python, #tutorial
```

---

### 6. Configuration

User settings stored in `~/.config/claudsidian/config.json` (or `config/claudsidian.json` in project).

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| vault_path | string | Yes | - | Absolute path to Obsidian vault |
| claude_api_key | string | No* | - | Anthropic API key |
| openrouter_api_key | string | No* | - | OpenRouter API key |
| server_port | integer | No | 8765 | Local HTTP server port |
| inbox_file | string | No | `inbox.md` | Inbox file name in vault root |
| folders | FolderConfig | No | (defaults) | Content type → folder mapping |

*At least one API key required.

**FolderConfig**:
```json
{
  "article": "Learning",
  "video": "Videos",
  "repo": "Projects",
  "news": "News",
  "walkthrough": "Guides",
  "printable": "3D-Models"
}
```

---

### 7. CaptureQueue

Pending captures when offline or API unavailable.

| Field | Type | Description |
|-------|------|-------------|
| id | string (UUID) | Unique identifier |
| request | CaptureRequest | Original request |
| status | enum | `pending`, `processing`, `failed`, `completed` |
| attempts | integer | Number of processing attempts |
| error | string | Last error message if failed |
| created_at | datetime | When queued |
| updated_at | datetime | Last status change |

**Storage**: `~/.config/claudsidian/queue.json`

**Retry Logic**:
- Max 3 attempts
- Exponential backoff: 1min, 5min, 15min
- After 3 failures: mark as `failed`, notify user

---

## State Transitions

### Capture Request Lifecycle

```
[Received] → [Type Detected] → [Content Extracted] → [AI Processed] → [Note Written] → [Complete]
     ↓              ↓                  ↓                   ↓
  [Queued]     [Error: Unknown]   [Error: Fetch]    [Error: API]
                    ↓                  ↓                   ↓
              [Manual Review]     [Retry Queue]      [Retry Queue]
```

### Queue Item States

```
pending → processing → completed
              ↓
           failed (after 3 attempts)
```

---

## Relationships

```
CaptureRequest
    ↓ (1:1)
ContentType ←── detected from URL/content
    ↓ (1:1)
Note
    ↓ (1:N)
Tag ←── generated by AI
    ↓ (N:N)
Backlink ←── discovered from shared tags/topics
```

---

## File Storage Layout

```
~/.config/claudsidian/
├── config.json          # User configuration
└── queue.json           # Pending captures

{vault_path}/
├── Learning/            # Articles
├── Videos/              # YouTube notes
├── Projects/            # GitHub repos
├── News/                # News articles
├── Guides/              # Walkthroughs
├── 3D-Models/           # Printables
└── inbox.md             # Watched inbox file
```

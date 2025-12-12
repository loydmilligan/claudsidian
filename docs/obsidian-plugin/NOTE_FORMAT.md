# Claudsidian Note Format Specification

Complete specification for the markdown note format and YAML frontmatter schema used by Claudsidian captures.

---

## Complete Note Example

```markdown
---
source: https://example.com/article
captured: '2025-12-01T12:00:00Z'
type: article
tags:
  - technology
  - ai
  - knowledge-management
summary: A brief one-line summary of the content
ai:
  summary:
    backend: openrouter
    model: x-ai/grok-4.1-fast
    temperature: 0.7
    max_tokens: 2000
  tags:
    backend: openrouter
    model: anthropic/claude-3-haiku
    temperature: 0.5
    max_tokens: 200
user_rating: null
rating_processed: false
---

# Article Title

Main content goes here in markdown format...

## Section 1

Content for section 1...

## Section 2

Content for section 2...
```

---

## Frontmatter Schema

### Core Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `source` | URL | Yes | - | Original URL where content was captured |
| `captured` | ISO 8601 | Yes | - | Timestamp when content was captured |
| `type` | enum | Yes | - | Content type classification |
| `tags` | string[] | No | `[]` | Auto-generated organizational tags |
| `summary` | string | No | `null` | One-line summary for preview |

### AI Metadata Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ai` | object | No | Container for AI generation metadata |
| `ai.summary` | object | No | Metadata for summary generation |
| `ai.summary.backend` | string | No | `claude` or `openrouter` |
| `ai.summary.model` | string | No | Model identifier used |
| `ai.summary.temperature` | float | No | Sampling temperature (0.0-1.0) |
| `ai.summary.max_tokens` | int | No | Maximum tokens requested |
| `ai.tags` | object | No | Metadata for tag generation |
| `ai.tags.backend` | string | No | `claude` or `openrouter` |
| `ai.tags.model` | string | No | Model identifier used |
| `ai.tags.temperature` | float | No | Sampling temperature (0.0-1.0) |
| `ai.tags.max_tokens` | int | No | Maximum tokens requested |

### User Interaction Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `user_rating` | int (1-5) | No | `null` | User quality rating (1-5 stars) |
| `rating_processed` | bool | No | `false` | Whether rating has been processed into analytics |

---

## Content Types

The `type` field accepts one of these values:

| Type | Description | Example URLs | Default Folder |
|------|-------------|--------------|----------------|
| `article` | Blog posts, essays, documentation | Medium, dev.to, Wikipedia | `Learning/` |
| `video` | YouTube, Vimeo, video content | youtube.com, vimeo.com | `Videos/` |
| `repo` | GitHub repositories | github.com/user/repo | `Projects/` |
| `news` | News articles, press releases | CNN, BBC, Reuters | `News/` |
| `walkthrough` | Tutorials, how-to guides | Dev tutorials, docs | `Guides/` |
| `printable` | 3D models, printable content | Thingiverse, Printables | `3D-Models/` |

---

## Content Type Detection

Content type is automatically detected based on:

1. **URL patterns:**
   - `youtube.com`, `youtu.be` -> `video`
   - `github.com/user/repo` -> `repo`
   - `thingiverse.com`, `printables.com`, `cults3d.com` -> `printable`

2. **Content analysis:**
   - News indicators -> `news`
   - Tutorial/step indicators -> `walkthrough`
   - Default fallback -> `article`

3. **Force override:**
   - Can be overridden via `force_type` in capture request

---

## File Naming

### Sanitization Rules

Filenames are derived from the note title with these transformations:

1. **Removed characters:** `/`, `\`, `:`, `*`, `?`, `"`, `<`, `>`, `|`
2. **Collapsed:** Multiple spaces/underscores become single space
3. **Reserved names replaced:** Windows reserved names (CON, PRN, AUX, NUL, COM1-9, LPT1-9)
4. **Length limit:** Truncated to 200 characters at word boundary
5. **Empty fallback:** Defaults to "Untitled"

### Duplicate Handling

When a file already exists:
- Default: Appends counter like `(2)`, `(3)`
- Example: `Article Title.md` -> `Article Title (2).md`

---

## Folder Structure

Notes are organized by content type into configurable folders:

```
vault/
├── Learning/           # article type
│   ├── blog-post.md
│   └── documentation.md
├── Videos/             # video type
│   └── youtube-video.md
├── Projects/           # repo type
│   └── github-repo.md
├── News/               # news type
│   └── news-article.md
├── Guides/             # walkthrough type
│   └── tutorial.md
└── 3D-Models/          # printable type
    └── model.md
```

---

## Markdown Body Structure

### Standard Article/News

```markdown
# Title

Summary or introduction paragraph...

## Key Points

- Point 1
- Point 2
- Point 3

## Main Content

Full article content...

## Conclusion

Concluding remarks...
```

### Video Content

```markdown
# Video Title

**Duration:** 10:30
**Channel:** Channel Name
**Published:** 2025-01-15

## Summary

Video summary...

## Key Topics

- Topic 1
- Topic 2

## Transcript Highlights

Notable quotes or sections...
```

### Repository Content

```markdown
# Repository Name

**Author:** username
**Stars:** 1,234
**Language:** Python

## Description

Repository description...

## Key Features

- Feature 1
- Feature 2

## Getting Started

Quick start instructions...
```

### 3D Model (Printable) Content

```markdown
# Model Name

**Designer:** username
**Downloads:** 5,678
**Category:** Functional

## Description

Model description...

## Print Settings

- Layer Height: 0.2mm
- Infill: 20%
- Supports: Yes

## Images

![Preview](image-url.jpg)
```

---

## TypeScript Types

```typescript
interface Frontmatter {
  source: string;           // URL
  captured: string;         // ISO 8601 datetime
  type: ContentType;
  tags?: string[];
  summary?: string;
  ai?: AIMetadata;
  user_rating?: number;     // 1-5
  rating_processed?: boolean;
}

type ContentType =
  | 'article'
  | 'video'
  | 'repo'
  | 'news'
  | 'walkthrough'
  | 'printable';

interface AIMetadata {
  summary?: AICallInfo;
  tags?: AICallInfo;
}

interface AICallInfo {
  backend?: 'claude' | 'openrouter';
  model?: string;
  temperature?: number;
  max_tokens?: number;
}

interface Note {
  title: string;
  content: string;
  frontmatter: Frontmatter;
  file_path: string;
}
```

---

## Parsing Notes

### Reading Frontmatter

To parse a Claudsidian note:

1. Split on `---` delimiters
2. Parse YAML between first two `---` markers
3. Remaining content is markdown body

```typescript
function parseNote(markdown: string): { frontmatter: Frontmatter; content: string } {
  const parts = markdown.split('---');
  if (parts.length < 3) {
    throw new Error('Invalid frontmatter format');
  }

  const frontmatter = parseYAML(parts[1].trim());
  const content = parts.slice(2).join('---').trim();

  return { frontmatter, content };
}
```

### Identifying Claudsidian Notes

A note is a Claudsidian capture if:
1. Has YAML frontmatter
2. Contains `source` field with valid URL
3. Contains `captured` field with ISO 8601 timestamp
4. Contains `type` field with valid content type

```typescript
function isClaudsidianNote(frontmatter: any): boolean {
  return (
    typeof frontmatter.source === 'string' &&
    frontmatter.source.startsWith('http') &&
    typeof frontmatter.captured === 'string' &&
    ['article', 'video', 'repo', 'news', 'walkthrough', 'printable']
      .includes(frontmatter.type)
  );
}
```

---

## Querying Recent Captures

To find recent captures for review workflows:

1. **Glob pattern:** `**/*.md` in vault
2. **Filter by:** `captured` date in frontmatter
3. **Sort by:** `captured` descending (newest first)

```typescript
async function getRecentCaptures(
  vault: Vault,
  days: number = 7
): Promise<Note[]> {
  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - days);

  const files = vault.getMarkdownFiles();
  const captures: Note[] = [];

  for (const file of files) {
    const content = await vault.read(file);
    const { frontmatter } = parseNote(content);

    if (!isClaudsidianNote(frontmatter)) continue;

    const captured = new Date(frontmatter.captured);
    if (captured >= cutoff) {
      captures.push({ frontmatter, content, file_path: file.path });
    }
  }

  return captures.sort((a, b) =>
    new Date(b.frontmatter.captured).getTime() -
    new Date(a.frontmatter.captured).getTime()
  );
}
```

---

## Special Considerations

### Backlinks

Claudsidian may add internal links to other notes in the vault:
- Format: `[[Note Title]]` or `[[Note Title|Display Text]]`
- Found in content body, not frontmatter
- Based on tag and topic similarity

### Rating System

The `user_rating` field supports the review workflow:
- Values: 1-5 (5 being highest quality)
- `rating_processed`: Set to `true` after analytics processing
- Used for model performance comparison

### Inbox Notes

Notes from inbox processing have:
- `source: "inbox"` in capture request
- May need additional metadata like `inbox_processed: true`

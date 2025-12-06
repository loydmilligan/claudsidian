# Research: Obsidian Learning Plugin

**Feature**: 002-obsidian-learning-plugin
**Date**: 2025-12-05

## Research Summary

This document consolidates research findings for building an Obsidian plugin that integrates with Claudsidian captures, SourceInfo API, and OpenRouter AI.

---

## 1. Obsidian Plugin Development Stack

### Decision: TypeScript + esbuild + Standard Plugin Architecture

**Rationale**: TypeScript is the standard for Obsidian plugins, with esbuild providing fast builds. The official obsidian-sample-plugin template provides a proven starting point.

**Alternatives Considered**:
- Plain JavaScript: Rejected due to lack of type safety with complex Obsidian API
- Rollup/Webpack: Rejected; esbuild is faster and is the official recommendation
- React for UI: Rejected; Obsidian's built-in Modal/Setting components are sufficient and simpler

### Key Technical Decisions

| Area | Decision | Rationale |
|------|----------|-----------|
| Language | TypeScript 5.x | Standard for Obsidian plugins, excellent type support |
| Build Tool | esbuild | Official recommendation, fast bundling |
| Testing | Jest + jest-environment-obsidian | Community standard, good examples available |
| YAML Parsing | gray-matter | Well-maintained, handles frontmatter parsing |
| HTTP Client | Obsidian's requestUrl() | Built-in, bypasses CORS restrictions |

---

## 2. Obsidian API Patterns

### File Operations

```typescript
// Read file content
const content = await this.app.vault.read(file);

// Write file content
await this.app.vault.modify(file, newContent);

// Create new file
await this.app.vault.create(path, content);

// Get all markdown files
const files = this.app.vault.getMarkdownFiles();
```

### Frontmatter Operations

```typescript
// Read frontmatter (cached, fast)
const cache = this.app.metadataCache.getFileCache(file);
const frontmatter = cache?.frontmatter;

// Modify frontmatter (preserves formatting)
await this.app.fileManager.processFrontMatter(file, (fm) => {
  fm.reviewed = true;
  fm.reviewed_at = new Date().toISOString();
});
```

**Best Practice**: Use `processFrontMatter()` for modifications - it preserves YAML formatting and is the official API.

### HTTP Requests (Critical for External APIs)

```typescript
import { requestUrl } from 'obsidian';

// OpenRouter API call
const response = await requestUrl({
  url: 'https://openrouter.ai/api/v1/chat/completions',
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${apiKey}`,
    'Content-Type': 'application/json',
    'HTTP-Referer': 'https://github.com/user/plugin',
    'X-Title': 'Obsidian Learning Plugin'
  },
  body: JSON.stringify({
    model: 'x-ai/grok-4.1-fast',
    messages: [{ role: 'user', content: prompt }]
  })
});
```

**Critical**: Always use `requestUrl()` instead of `fetch()` - it bypasses CORS restrictions that would block external API calls.

### Event Handling

```typescript
// File watcher for inbox folder
this.registerEvent(
  this.app.vault.on('create', (file) => {
    if (file.path.startsWith(this.settings.inboxFolder)) {
      this.onInboxFileCreated(file);
    }
  })
);

// Metadata cache changes
this.registerEvent(
  this.app.metadataCache.on('changed', (file) => {
    // React to frontmatter changes
  })
);
```

**Best Practice**: Always use `registerEvent()` for automatic cleanup on plugin unload.

### UI Components

```typescript
// Modal pattern
class ReviewModal extends Modal {
  onOpen() {
    const { contentEl } = this;

    // Add UI elements
    new Setting(contentEl)
      .setName('Rate this note')
      .addSlider(slider => slider
        .setLimits(1, 5, 1)
        .setValue(3)
        .setDynamicTooltip()
        .onChange(value => this.rating = value));
  }
}

// Settings tab pattern
class PluginSettingTab extends PluginSettingTab {
  display() {
    const { containerEl } = this;
    containerEl.empty();

    new Setting(containerEl)
      .setName('OpenRouter API Key')
      .addText(text => text
        .setPlaceholder('sk-or-...')
        .setValue(this.plugin.settings.openrouterApiKey)
        .onChange(async value => {
          this.plugin.settings.openrouterApiKey = value;
          await this.plugin.saveSettings();
        }));
  }
}
```

---

## 3. Integration Points

### Claudsidian Note Format

Notes created by Claudsidian have this frontmatter structure:

```yaml
---
source: https://example.com/article
captured: '2025-12-01T12:00:00Z'
type: article  # article, video, repo, news, walkthrough, printable
tags:
  - technology
  - ai
summary: Optional one-line summary
ai:
  summary:
    backend: openrouter
    model: x-ai/grok-4.1-fast
  tags:
    backend: openrouter
    model: anthropic/claude-3-haiku
user_rating: null  # Plugin will write 1-5
rating_processed: false
---
```

**Detection Pattern**: A note is a Claudsidian capture if it has `source` (URL), `captured` (ISO timestamp), and `type` fields.

### Claudsidian Data Files

Located in `{vault}/.claudsidian/`:

| File | Purpose | Format |
|------|---------|--------|
| `model_performance.json` | Performance metrics per model | JSON array of CapturePerformance |
| `ratings.json` | User ratings database | JSON array of NoteRating |

### SourceInfo API

**Base URL**: `http://localhost:8000` (configurable)

| Endpoint | Purpose |
|----------|---------|
| `GET /api/sources/{domain}` | Get source credibility and bias |
| `GET /api/sources/{domain}/counternarratives` | Get opposing perspective sources |
| `POST /api/analyze` | Analyze a URL for source info |

**Response Example**:
```json
{
  "domain": "nytimes.com",
  "name": "New York Times",
  "political_lean": -1,
  "political_lean_label": "Lean Left",
  "newsguard_score": 100,
  "newsguard_rating": "High Credibility"
}
```

### OpenRouter API

**Base URL**: `https://openrouter.ai/api/v1`

**Recommended Models** (from user preference):
- `x-ai/grok-4.1-fast` - Fast, good quality
- `minimax/minimax-m2` - Alternative fast model
- `deepseek/deepseek-chat-v3.1` - Cost-effective
- `z-ai/glm-4.5-air:free` - Free tier option

**Headers Required**:
```
Authorization: Bearer <api_key>
HTTP-Referer: <plugin_url>
X-Title: <plugin_name>
Content-Type: application/json
```

---

## 4. AI Prompts Strategy

### Learning Question Generation

```
You are a learning assistant. Given the following content, generate 3-5 comprehension questions that will help the reader process and retain the key information.

Focus on:
- Main concepts and their relationships
- Practical applications
- Critical thinking about the content

Content:
{note_content}

Format as:
1. [Question]
2. [Question]
...
```

### Inbox Triage Suggestion

```
Analyze this captured content and suggest an appropriate action:

Title: {title}
Type: {type}
Summary: {summary}
Tags: {tags}

Suggest ONE of:
- KEEP: Move to appropriate folder (specify folder)
- ARCHIVE: Low relevance, move to archive
- DEEP_READ: Flag for focused reading session
- MERGE: Similar to existing note (suggest which)

Response format:
Action: [ACTION]
Reason: [Brief explanation]
Folder: [If KEEP, which folder]
```

### Related Topics

```
Given this content, suggest 2-3 related topics for further reading:

Content summary: {summary}
Tags: {tags}

Format as:
- [Topic]: [Why it's relevant]
```

---

## 5. Performance Considerations

### Vault Scanning

- Use `metadataCache` for frontmatter queries (cached, fast)
- Don't read full file content unless necessary
- Cache SourceInfo lookups in memory (sources rarely change)

### AI API Optimization

- Batch similar requests when possible
- Truncate very long notes before sending to AI
- Cache question generation results in frontmatter

### UI Responsiveness

- Show loading states during AI calls
- Process notes sequentially in workflows to avoid overwhelming APIs
- Use Notice for quick feedback, Modal for detailed interactions

---

## 6. Plugin Settings Schema

```typescript
interface PluginSettings {
  // Server connections
  openrouterApiKey: string;
  sourceInfoUrl: string;  // default: http://localhost:8000

  // AI configuration
  aiModel: string;  // default: x-ai/grok-4.1-fast

  // Folders
  inboxFolder: string;  // default: Inbox
  archiveFolder: string;  // default: Archive

  // Review settings
  reviewPeriodDays: number;  // default: 7
  notesPerSession: number;  // default: 10

  // Content type filters
  enabledTypes: string[];  // default: all types

  // Feature toggles
  enableBiasAnalysis: boolean;  // default: true
  enableAutoInboxDetection: boolean;  // default: false
}
```

---

## 7. Resolved Clarifications

All technical unknowns from the spec have been resolved:

| Unknown | Resolution |
|---------|------------|
| Plugin language/framework | TypeScript + standard Obsidian plugin architecture |
| Testing approach | Jest + jest-environment-obsidian for smoke tests |
| HTTP request method | Obsidian's requestUrl() to bypass CORS |
| Frontmatter modification | processFrontMatter() API |
| UI framework | Built-in Modal + Setting components |
| AI model selection | User preference: Grok 4.1 Fast as default |

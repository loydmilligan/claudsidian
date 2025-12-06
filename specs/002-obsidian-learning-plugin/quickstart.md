# Quickstart: Obsidian Learning Plugin Development

**Feature**: 002-obsidian-learning-plugin
**Date**: 2025-12-05

## Prerequisites

- Node.js 16+ installed
- Obsidian desktop app (for testing)
- OpenRouter API key (for AI features)
- SourceInfo server running locally (for bias analysis)
- Claudsidian already configured in your vault

## Setup

### 1. Clone the Official Sample Plugin

```bash
# Create plugin directory
mkdir obsidian-learning-plugin
cd obsidian-learning-plugin

# Initialize from sample plugin template
npx degit obsidianmd/obsidian-sample-plugin .

# Install dependencies
npm install
```

### 2. Install Additional Dependencies

```bash
# YAML frontmatter parsing
npm install gray-matter

# TypeScript types
npm install -D @types/gray-matter
```

### 3. Update manifest.json

```json
{
  "id": "obsidian-learning-plugin",
  "name": "Learning Plugin",
  "version": "0.1.0",
  "minAppVersion": "1.0.0",
  "description": "AI-powered learning workflows for Claudsidian captures",
  "author": "Your Name",
  "authorUrl": "https://github.com/yourusername",
  "isDesktopOnly": true
}
```

### 4. Configure for Development

Link the plugin to your test vault:

```bash
# Build in watch mode
npm run dev

# Symlink to vault (macOS/Linux)
ln -s $(pwd) "/path/to/vault/.obsidian/plugins/obsidian-learning-plugin"

# Or copy on Windows
# Copy entire folder to %VAULT%/.obsidian/plugins/obsidian-learning-plugin
```

### 5. Enable the Plugin

1. Open Obsidian Settings
2. Go to Community Plugins
3. Enable "Learning Plugin"
4. Configure API keys in plugin settings

## Project Structure

```
obsidian-learning-plugin/
├── src/
│   ├── main.ts              # Plugin entry point
│   ├── settings.ts          # Settings tab
│   ├── types.ts             # TypeScript interfaces
│   ├── services/
│   │   ├── ai.ts            # OpenRouter client
│   │   ├── sourceinfo.ts    # SourceInfo client
│   │   ├── vault.ts         # Vault operations
│   │   └── ratings.ts       # Claudsidian ratings sync
│   ├── workflows/
│   │   ├── review.ts        # Review Recent workflow
│   │   └── inbox.ts         # Inbox Processing workflow
│   ├── analysis/
│   │   ├── questions.ts     # Learning question generation
│   │   ├── bias.ts          # Source bias analysis
│   │   └── triage.ts        # Inbox triage suggestions
│   └── ui/
│       ├── review-modal.ts
│       ├── inbox-modal.ts
│       └── dashboard-view.ts
├── tests/
│   └── smoke.test.ts
├── manifest.json
├── package.json
├── tsconfig.json
├── esbuild.config.mjs
└── styles.css
```

## Key Patterns

### Plugin Entry Point (main.ts)

```typescript
import { Plugin } from 'obsidian';
import { PluginSettings, DEFAULT_SETTINGS } from './settings';

export default class LearningPlugin extends Plugin {
  settings: PluginSettings;

  async onload() {
    await this.loadSettings();

    // Register settings tab
    this.addSettingTab(new LearningSettingTab(this.app, this));

    // Register commands
    this.addCommand({
      id: 'review-recent',
      name: 'Review Recent Captures',
      callback: () => this.openReviewWorkflow()
    });

    this.addCommand({
      id: 'process-inbox',
      name: 'Process Inbox',
      callback: () => this.openInboxWorkflow()
    });

    // Register file watcher for inbox
    this.registerEvent(
      this.app.vault.on('create', (file) => {
        if (file.path.startsWith(this.settings.inboxFolder)) {
          // New inbox item detected
        }
      })
    );
  }

  async loadSettings() {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }

  async saveSettings() {
    await this.saveData(this.settings);
  }
}
```

### HTTP Requests (Bypass CORS)

```typescript
import { requestUrl } from 'obsidian';

async function callOpenRouter(apiKey: string, prompt: string): Promise<string> {
  const response = await requestUrl({
    url: 'https://openrouter.ai/api/v1/chat/completions',
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
      'HTTP-Referer': 'https://github.com/user/obsidian-learning-plugin',
      'X-Title': 'Obsidian Learning Plugin'
    },
    body: JSON.stringify({
      model: 'x-ai/grok-4.1-fast',
      messages: [{ role: 'user', content: prompt }],
      temperature: 0.7,
      max_tokens: 1000
    })
  });

  const data = JSON.parse(response.text);
  return data.choices[0].message.content;
}
```

### Frontmatter Modification

```typescript
import { TFile } from 'obsidian';

async function updateNoteRating(file: TFile, rating: number): Promise<void> {
  await this.app.fileManager.processFrontMatter(file, (fm) => {
    fm.user_rating = rating;
    fm.reviewed = true;
    fm.reviewed_at = new Date().toISOString();
  });
}
```

### Detecting Claudsidian Notes

```typescript
import { TFile } from 'obsidian';

function isClaudsidianNote(file: TFile): boolean {
  const cache = this.app.metadataCache.getFileCache(file);
  const fm = cache?.frontmatter;

  if (!fm) return false;

  return (
    typeof fm.source === 'string' &&
    fm.source.startsWith('http') &&
    typeof fm.captured === 'string' &&
    ['article', 'video', 'repo', 'news', 'walkthrough', 'printable'].includes(fm.type)
  );
}
```

### Modal Pattern

```typescript
import { Modal, Setting } from 'obsidian';

class ReviewModal extends Modal {
  private rating: number = 0;

  onOpen() {
    const { contentEl } = this;

    contentEl.createEl('h2', { text: 'Review Capture' });

    new Setting(contentEl)
      .setName('Rate this note')
      .addSlider(slider => slider
        .setLimits(1, 5, 1)
        .setValue(3)
        .setDynamicTooltip()
        .onChange(value => this.rating = value));

    new Setting(contentEl)
      .addButton(btn => btn
        .setButtonText('Save & Next')
        .setCta()
        .onClick(() => {
          this.onSave(this.rating);
          this.close();
        }));
  }

  onClose() {
    const { contentEl } = this;
    contentEl.empty();
  }
}
```

## Build & Test

### Development Build

```bash
# Watch mode (rebuilds on changes)
npm run dev
```

### Production Build

```bash
npm run build
```

### Manual Testing

1. Open test vault in Obsidian
2. Reload plugins (Ctrl+R on plugin settings page)
3. Test commands via Command Palette (Ctrl+P)

### Smoke Test

```typescript
// tests/smoke.test.ts
import { describe, it, expect } from '@jest/globals';

describe('Learning Plugin', () => {
  it('detects Claudsidian notes correctly', () => {
    const validFrontmatter = {
      source: 'https://example.com/article',
      captured: '2025-12-01T12:00:00Z',
      type: 'article'
    };

    expect(isClaudsidianNote(validFrontmatter)).toBe(true);
  });

  it('rejects non-Claudsidian notes', () => {
    const invalidFrontmatter = {
      title: 'Regular note'
    };

    expect(isClaudsidianNote(invalidFrontmatter)).toBe(false);
  });
});
```

## Environment Setup

### Required Services

| Service | URL | Purpose |
|---------|-----|---------|
| SourceInfo API | http://localhost:8000 | Source bias data |
| Claudsidian | N/A (file-based) | Note captures |
| OpenRouter | https://openrouter.ai | AI completions |

### API Keys

Store in plugin settings (encrypted in Obsidian's data.json):

```typescript
interface PluginSettings {
  openrouterApiKey: string;  // Required for AI features
  sourceInfoUrl: string;      // Default: http://localhost:8000
}
```

## Next Steps

1. Implement P1: Review Recent Captures workflow
2. Implement P2: Inbox Processing + Source Bias
3. Implement P3: Single Note Analysis + Ratings
4. Implement P4: Model Performance Dashboard

See [spec.md](./spec.md) for full requirements and [data-model.md](./data-model.md) for entity definitions.

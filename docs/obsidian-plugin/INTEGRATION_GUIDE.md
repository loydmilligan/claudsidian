# Claudsidian Integration Guide

How to integrate an Obsidian plugin with the Claudsidian capture system for review workflows and AI-aided knowledge processing.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      Obsidian Vault                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   Inbox/    │  │  Learning/  │  │  Videos/    │  ...         │
│  │  (staging)  │  │  (articles) │  │  (videos)   │              │
│  └──────┬──────┘  └─────────────┘  └─────────────┘              │
│         │                                                        │
│         ▼                                                        │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              Obsidian Plugin (claudsidian-review)           ││
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐             ││
│  │  │   Review   │  │   Inbox    │  │    AI      │             ││
│  │  │  Workflow  │  │ Processing │  │  Routing   │             ││
│  │  └────────────┘  └────────────┘  └────────────┘             ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
         │                    │
         ▼                    ▼
┌─────────────────┐  ┌─────────────────┐
│ Claudsidian     │  │  AI Services    │
│ Server (local)  │  │ (OpenRouter/    │
│ :8765           │  │  Claude)        │
└─────────────────┘  └─────────────────┘
```

---

## Connection Methods

### 1. Direct Vault Access (Primary)

The plugin runs inside Obsidian and has direct access to vault files via the Obsidian API.

```typescript
import { App, TFile, Vault } from 'obsidian';

class ClaudsidianPlugin extends Plugin {
  async getRecentCaptures(): Promise<TFile[]> {
    const files = this.app.vault.getMarkdownFiles();
    return files.filter(file => this.isClaudsidianNote(file));
  }

  async readNoteFrontmatter(file: TFile): Promise<Frontmatter | null> {
    const content = await this.app.vault.read(file);
    return this.parseFrontmatter(content);
  }
}
```

### 2. Claudsidian Server API (Optional)

For triggering new captures or checking queue status:

```typescript
class ClaudsidianAPI {
  private baseUrl = 'http://127.0.0.1:8765';

  async checkStatus(): Promise<ServerStatus> {
    const response = await fetch(`${this.baseUrl}/status`);
    return response.json();
  }

  async capture(url: string): Promise<CaptureResponse> {
    const response = await fetch(`${this.baseUrl}/capture`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, source: 'inbox' })
    });
    return response.json();
  }

  async getQueue(): Promise<QueueResponse> {
    const response = await fetch(`${this.baseUrl}/queue`);
    return response.json();
  }
}
```

### 3. Service Discovery (mDNS)

For finding the server on the local network:

```typescript
// Browser/Electron doesn't support mDNS directly
// Alternative: Try common ports or use settings
const COMMON_PORTS = [8765, 8766, 8767];

async function discoverServer(): Promise<string | null> {
  for (const port of COMMON_PORTS) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}/health`);
      if (response.ok) return `http://127.0.0.1:${port}`;
    } catch {}
  }
  return null;
}
```

---

## Workflow 1: Review Recent Captures

Goal: Present captured notes for user review to reinforce learning.

### Data Flow

```
1. User triggers review (command/ribbon/timer)
       │
       ▼
2. Query vault for recent captures (last 7 days)
       │
       ▼
3. Filter unreviewed notes (no user_rating)
       │
       ▼
4. Present in review modal/pane
       │
       ▼
5. User reviews: rate, add notes, move to folder
       │
       ▼
6. Update frontmatter with rating
```

### Implementation Steps

```typescript
// Step 1: Query recent captures
async function getReviewQueue(vault: Vault, days: number = 7): Promise<TFile[]> {
  const cutoff = Date.now() - (days * 24 * 60 * 60 * 1000);
  const files = vault.getMarkdownFiles();

  const candidates: TFile[] = [];
  for (const file of files) {
    const meta = await this.parseFrontmatter(file);
    if (!meta || !isClaudsidianNote(meta)) continue;
    if (meta.user_rating !== null) continue; // Already reviewed

    const captured = new Date(meta.captured).getTime();
    if (captured >= cutoff) {
      candidates.push(file);
    }
  }

  // Sort by captured date, oldest first (review backlog)
  return candidates.sort((a, b) => {
    const aDate = new Date(a.frontmatter.captured);
    const bDate = new Date(b.frontmatter.captured);
    return aDate.getTime() - bDate.getTime();
  });
}

// Step 2: Present review modal
class ReviewModal extends Modal {
  private queue: TFile[];
  private currentIndex: number = 0;

  async showNext() {
    const file = this.queue[this.currentIndex];
    const content = await this.app.vault.read(file);
    const { frontmatter, body } = parseFrontmatter(content);

    this.contentEl.empty();
    this.contentEl.createEl('h2', { text: frontmatter.title });
    this.contentEl.createEl('p', { text: frontmatter.summary });
    // ... render content preview

    // Rating buttons
    const ratingEl = this.contentEl.createDiv('rating');
    for (let i = 1; i <= 5; i++) {
      const btn = ratingEl.createEl('button', { text: '⭐'.repeat(i) });
      btn.onclick = () => this.rate(file, i);
    }
  }

  async rate(file: TFile, rating: number) {
    await this.updateFrontmatter(file, { user_rating: rating });
    this.currentIndex++;
    if (this.currentIndex < this.queue.length) {
      this.showNext();
    } else {
      this.close();
      new Notice('Review complete!');
    }
  }
}
```

### Review UI Suggestions

1. **Card View:** Show note as a card with summary, tags, source domain
2. **Quick Actions:**
   - Rate 1-5 stars
   - Skip (review later)
   - Open full note
   - Delete/archive
3. **Progress Indicator:** "3 of 12 notes reviewed"
4. **Spaced Repetition:** Re-surface high-rated notes periodically

---

## Workflow 2: Inbox Processing

Goal: AI-aided triage of new captures to decide next actions.

### Inbox Folder Setup

```
vault/
├── Inbox/                  # New captures land here
│   ├── pending-article.md
│   └── pending-video.md
├── Learning/               # Approved articles
├── Archive/                # Dismissed content
└── ...
```

### Processing Flow

```
1. New capture arrives in Inbox/
       │
       ▼
2. Plugin detects new file (file watcher)
       │
       ▼
3. AI analyzes content:
   - Relevance score
   - Topic classification
   - Suggested action
       │
       ▼
4. Present to user with AI recommendation:
   - "Move to Learning (relevance: 0.8)"
   - "Archive (duplicate topic)"
   - "Flag for deep reading"
       │
       ▼
5. User confirms/overrides
       │
       ▼
6. Execute action (move file, update metadata)
```

### Implementation Steps

```typescript
// File watcher for inbox
class InboxWatcher {
  private inboxPath = 'Inbox';

  onload() {
    this.registerEvent(
      this.app.vault.on('create', (file) => {
        if (file.path.startsWith(this.inboxPath)) {
          this.processNewCapture(file as TFile);
        }
      })
    );
  }

  async processNewCapture(file: TFile) {
    const content = await this.app.vault.read(file);
    const { frontmatter, body } = parseFrontmatter(content);

    // Get AI analysis
    const analysis = await this.analyzeWithAI(frontmatter, body);

    // Show notification with action
    new InboxActionModal(this.app, file, analysis).open();
  }

  async analyzeWithAI(frontmatter: Frontmatter, body: string): Promise<Analysis> {
    // Option 1: Use Claudsidian server
    const response = await fetch('http://127.0.0.1:8765/analyze', {
      method: 'POST',
      body: JSON.stringify({ content: body, metadata: frontmatter })
    });

    // Option 2: Direct OpenRouter/Claude call
    const aiResponse = await this.callOpenRouter({
      model: 'anthropic/claude-3-haiku',
      prompt: `Analyze this captured content and suggest an action:

Title: ${frontmatter.title}
Type: ${frontmatter.type}
Tags: ${frontmatter.tags?.join(', ')}
Summary: ${frontmatter.summary}

Suggest one of:
- KEEP: Move to appropriate folder
- ARCHIVE: Low relevance, archive
- DEEP_READ: Flag for deep reading session
- MERGE: Similar to existing note

Respond as JSON: { "action": "...", "reason": "...", "folder": "..." }`
    });

    return JSON.parse(aiResponse);
  }
}

// Action modal
class InboxActionModal extends Modal {
  constructor(app: App, file: TFile, analysis: Analysis) {
    super(app);
    this.file = file;
    this.analysis = analysis;
  }

  onOpen() {
    const { contentEl } = this;

    contentEl.createEl('h2', { text: 'New Capture' });
    contentEl.createEl('p', { text: this.file.basename });

    // AI recommendation
    const rec = contentEl.createDiv('recommendation');
    rec.createEl('strong', { text: 'AI Suggestion: ' });
    rec.createEl('span', { text: this.analysis.action });
    rec.createEl('p', { text: this.analysis.reason });

    // Action buttons
    const actions = contentEl.createDiv('actions');

    const keepBtn = actions.createEl('button', { text: 'Keep' });
    keepBtn.onclick = () => this.executeAction('keep');

    const archiveBtn = actions.createEl('button', { text: 'Archive' });
    archiveBtn.onclick = () => this.executeAction('archive');

    const laterBtn = actions.createEl('button', { text: 'Decide Later' });
    laterBtn.onclick = () => this.close();
  }

  async executeAction(action: string) {
    const newPath = action === 'keep'
      ? `Learning/${this.file.name}`
      : `Archive/${this.file.name}`;

    await this.app.fileManager.renameFile(this.file, newPath);
    this.close();
  }
}
```

### AI Prompts for Inbox Processing

```typescript
const TRIAGE_PROMPT = `You are helping a user decide what to do with a captured article.

Content:
Title: {title}
Source: {source}
Type: {type}
Summary: {summary}
Tags: {tags}

User's interests (based on vault): {user_topics}

Evaluate and respond with JSON:
{
  "relevance_score": 0.0-1.0,
  "suggested_action": "KEEP|ARCHIVE|DEEP_READ|MERGE",
  "reason": "Brief explanation",
  "suggested_folder": "folder name if KEEP",
  "similar_notes": ["existing note titles if MERGE"]
}`;

const LEARNING_EXTRACTION_PROMPT = `Extract key learnings from this content:

{content}

Format as:
{
  "key_insights": ["insight 1", "insight 2"],
  "action_items": ["todo 1", "todo 2"],
  "questions": ["question to explore"],
  "connections": ["related topic or concept"]
}`;
```

---

## Workflow 3: Learning Sessions

Goal: Scheduled deep engagement with captured content.

### Session Types

1. **Quick Review (5 min):** Flash through summaries, rate
2. **Deep Read (30 min):** Read full articles, take notes
3. **Topic Dive (60 min):** Explore all captures on a topic
4. **Random Discovery:** Surface old/forgotten captures

### Implementation

```typescript
class LearningSession {
  private sessionType: 'quick' | 'deep' | 'topic' | 'random';
  private duration: number;
  private notes: TFile[];

  async startQuickReview() {
    // Get 10 unreviewed notes from last 7 days
    this.notes = await this.getReviewQueue(7);
    this.notes = this.notes.slice(0, 10);
    this.showReviewUI();
  }

  async startDeepRead() {
    // Get 3 high-relevance unread notes
    this.notes = await this.getUnreadNotes();
    this.notes = this.notes
      .sort((a, b) => b.relevance - a.relevance)
      .slice(0, 3);
    this.showDeepReadUI();
  }

  async startTopicDive(topic: string) {
    // Get all notes matching topic
    this.notes = await this.getNotesByTag(topic);
    this.showTopicUI();
  }

  async startRandomDiscovery() {
    // Get 5 random notes older than 30 days
    const oldNotes = await this.getOldNotes(30);
    this.notes = this.shuffle(oldNotes).slice(0, 5);
    this.showDiscoveryUI();
  }
}

// Session scheduling
class SessionScheduler {
  scheduleDaily(time: string, sessionType: string) {
    // Use Obsidian's periodic notes or cron-like scheduling
  }

  async checkDueSession() {
    const lastSession = await this.getLastSessionDate();
    const daysSince = this.daysSince(lastSession);

    if (daysSince >= 1) {
      new Notice('You have captures to review!');
    }
  }
}
```

---

## Settings & Configuration

### Plugin Settings

```typescript
interface ClaudsidianReviewSettings {
  // Server connection
  serverUrl: string;
  serverPort: number;

  // Inbox
  inboxFolder: string;
  autoProcessInbox: boolean;

  // Review
  reviewIntervalDays: number;
  notesPerSession: number;

  // AI
  aiBackend: 'claudsidian' | 'openrouter' | 'claude';
  openrouterApiKey?: string;
  claudeApiKey?: string;
  triageModel: string;

  // Folders
  archiveFolder: string;
  defaultFolder: string;
}

const DEFAULT_SETTINGS: ClaudsidianReviewSettings = {
  serverUrl: 'http://127.0.0.1',
  serverPort: 8765,
  inboxFolder: 'Inbox',
  autoProcessInbox: false,
  reviewIntervalDays: 7,
  notesPerSession: 10,
  aiBackend: 'claudsidian',
  triageModel: 'anthropic/claude-3-haiku',
  archiveFolder: 'Archive',
  defaultFolder: 'Learning'
};
```

### Settings Tab

```typescript
class ClaudsidianSettingTab extends PluginSettingTab {
  display(): void {
    const { containerEl } = this;
    containerEl.empty();

    containerEl.createEl('h2', { text: 'Claudsidian Review Settings' });

    // Server connection
    new Setting(containerEl)
      .setName('Server URL')
      .setDesc('Claudsidian capture server address')
      .addText(text => text
        .setValue(this.plugin.settings.serverUrl)
        .onChange(async (value) => {
          this.plugin.settings.serverUrl = value;
          await this.plugin.saveSettings();
        }));

    // Inbox folder
    new Setting(containerEl)
      .setName('Inbox Folder')
      .setDesc('Folder for new captures to be triaged')
      .addText(text => text
        .setValue(this.plugin.settings.inboxFolder)
        .onChange(async (value) => {
          this.plugin.settings.inboxFolder = value;
          await this.plugin.saveSettings();
        }));

    // ... more settings
  }
}
```

---

## Commands to Register

```typescript
this.addCommand({
  id: 'review-captures',
  name: 'Review Recent Captures',
  callback: () => new ReviewModal(this.app, this).open()
});

this.addCommand({
  id: 'process-inbox',
  name: 'Process Inbox',
  callback: () => this.processInbox()
});

this.addCommand({
  id: 'start-learning-session',
  name: 'Start Learning Session',
  callback: () => new SessionPickerModal(this.app, this).open()
});

this.addCommand({
  id: 'capture-url',
  name: 'Capture URL',
  callback: () => new CaptureModal(this.app, this).open()
});

this.addCommand({
  id: 'server-status',
  name: 'Check Claudsidian Server',
  callback: () => this.checkServerStatus()
});
```

---

## Ribbon Icons

```typescript
this.addRibbonIcon('inbox', 'Claudsidian Inbox', () => {
  this.processInbox();
});

this.addRibbonIcon('book-open', 'Review Captures', () => {
  new ReviewModal(this.app, this).open();
});
```

---

## Status Bar

```typescript
const statusBarItem = this.addStatusBarItem();

async function updateStatusBar() {
  const unreviewed = await getUnreviewedCount();
  const inbox = await getInboxCount();

  statusBarItem.setText(`📥 ${inbox} | 📚 ${unreviewed}`);
}

// Update periodically
this.registerInterval(
  window.setInterval(() => updateStatusBar(), 60000)
);
```

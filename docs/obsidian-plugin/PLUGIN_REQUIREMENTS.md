# Claudsidian Review Plugin - Requirements

Product requirements and feature specifications for the Obsidian plugin that enables AI-aided knowledge capture workflows.

---

## Vision

Transform passive content capture into active learning by providing workflows that help users:
1. **Review** captured content to reinforce memory
2. **Triage** new captures with AI assistance
3. **Engage** deeply with content through structured sessions
4. **Learn** by connecting ideas across captures

---

## Core Features

### Feature 1: Review Recent Captures

**Goal:** Present recently captured notes for quick review and rating.

**User Stories:**
- As a user, I want to review captures from the past week so I remember what I saved
- As a user, I want to rate content quality so the system learns my preferences
- As a user, I want to skip irrelevant captures without losing track of them

**Requirements:**

| ID | Requirement | Priority |
|----|-------------|----------|
| R1.1 | Query vault for notes captured in last N days | Must |
| R1.2 | Filter to unreviewed notes (no `user_rating`) | Must |
| R1.3 | Display note in review modal with summary | Must |
| R1.4 | Allow 1-5 star rating | Must |
| R1.5 | Save rating to frontmatter | Must |
| R1.6 | Show progress (X of Y reviewed) | Should |
| R1.7 | Skip button to review later | Should |
| R1.8 | Open full note button | Should |
| R1.9 | Keyboard shortcuts for rating | Nice |
| R1.10 | Configurable review period (days) | Nice |

**UI Mockup:**
```
┌─────────────────────────────────────────────┐
│  Review Captures (3 of 12)                  │
├─────────────────────────────────────────────┤
│                                             │
│  📄 Article Title                           │
│  ─────────────────────────────              │
│  source.com • article • 2 days ago          │
│                                             │
│  Summary text appears here showing the      │
│  main points of the captured content...     │
│                                             │
│  Tags: #ai #technology #learning            │
│                                             │
├─────────────────────────────────────────────┤
│  Rate this capture:                         │
│  [⭐] [⭐⭐] [⭐⭐⭐] [⭐⭐⭐⭐] [⭐⭐⭐⭐⭐]          │
│                                             │
│  [Skip]  [Open Note]                        │
└─────────────────────────────────────────────┘
```

---

### Feature 2: Inbox Processing

**Goal:** AI-assisted triage of new captures with suggested actions.

**User Stories:**
- As a user, I want new captures to land in an inbox folder for triage
- As a user, I want AI to suggest what to do with each capture
- As a user, I want to quickly approve or override AI suggestions

**Requirements:**

| ID | Requirement | Priority |
|----|-------------|----------|
| I2.1 | Configure inbox folder path | Must |
| I2.2 | Detect new files in inbox folder | Must |
| I2.3 | Call AI to analyze capture content | Must |
| I2.4 | Display AI recommendation with reasoning | Must |
| I2.5 | Allow user to accept/reject recommendation | Must |
| I2.6 | Move file to appropriate folder on accept | Must |
| I2.7 | Batch processing mode for multiple items | Should |
| I2.8 | Auto-process option (apply AI suggestions automatically) | Should |
| I2.9 | Track AI suggestion accuracy over time | Nice |
| I2.10 | Learn from user overrides | Nice |

**AI Actions:**
- **KEEP:** Move to appropriate content folder
- **ARCHIVE:** Move to archive folder
- **DEEP_READ:** Flag for deep reading session
- **MERGE:** Suggest combining with similar note

**UI Mockup:**
```
┌─────────────────────────────────────────────┐
│  Inbox Processing (5 items)                 │
├─────────────────────────────────────────────┤
│  📥 New Article Title                       │
│  ─────────────────────────────              │
│  Captured: 2 hours ago                      │
│  Type: article | Tags: #python #tutorial    │
│                                             │
│  ┌─────────────────────────────────────────┐│
│  │ 🤖 AI Suggestion: KEEP                  ││
│  │ Reason: Matches your interest in Python ││
│  │ Folder: Learning/                       ││
│  └─────────────────────────────────────────┘│
│                                             │
│  [✓ Accept]  [Archive]  [Later]  [Open]     │
└─────────────────────────────────────────────┘
```

---

### Feature 3: Learning Sessions

**Goal:** Structured sessions for deep engagement with captured content.

**User Stories:**
- As a user, I want guided sessions to actually read my captures
- As a user, I want to discover forgotten captures
- As a user, I want to explore topics deeply

**Session Types:**

| Type | Duration | Content | Purpose |
|------|----------|---------|---------|
| Quick Review | 5-10 min | 10 summaries | Daily catch-up |
| Deep Read | 30 min | 3 full articles | Weekly learning |
| Topic Dive | 60 min | All notes on topic | Subject mastery |
| Random Discovery | 15 min | 5 old notes | Resurface ideas |

**Requirements:**

| ID | Requirement | Priority |
|----|-------------|----------|
| L3.1 | Session type selector | Must |
| L3.2 | Timer/progress indicator | Must |
| L3.3 | Note navigation within session | Must |
| L3.4 | Take notes during session (append to file) | Should |
| L3.5 | Mark note as "read" | Should |
| L3.6 | Session history/stats | Nice |
| L3.7 | Spaced repetition scheduling | Nice |
| L3.8 | Cross-note linking suggestions | Nice |

---

### Feature 4: Server Integration

**Goal:** Connect to Claudsidian capture server for status and triggers.

**Requirements:**

| ID | Requirement | Priority |
|----|-------------|----------|
| S4.1 | Check server health status | Must |
| S4.2 | Display server status in status bar | Must |
| S4.3 | Trigger capture from plugin (URL input) | Should |
| S4.4 | View capture queue | Should |
| S4.5 | Retry failed captures | Nice |
| S4.6 | Auto-discover server via mDNS | Nice |

---

## Technical Requirements

### Platform Support

| Platform | Support Level |
|----------|---------------|
| Obsidian Desktop (Windows) | Must |
| Obsidian Desktop (macOS) | Must |
| Obsidian Desktop (Linux) | Must |
| Obsidian Mobile (iOS) | Should |
| Obsidian Mobile (Android) | Should |

### Obsidian API Usage

```typescript
// Required APIs
this.app.vault              // File operations
this.app.workspace          // UI manipulation
this.app.metadataCache      // Frontmatter access
this.app.fileManager        // File management

// Recommended patterns
- Use metadataCache for fast frontmatter queries
- Use vault.on('create') for file watching
- Use Modal for review/inbox UIs
- Use MarkdownView for note display
```

### AI Integration Options

| Option | Pros | Cons |
|--------|------|------|
| Via Claudsidian server | No extra API keys, consistent | Requires server running |
| Direct OpenRouter | Works standalone | User needs API key |
| Direct Claude | Best quality | Most expensive |

Recommendation: Support all three with fallback chain.

---

## Settings

### Required Settings

```typescript
interface PluginSettings {
  // Server
  claudsidianServerUrl: string;      // default: 'http://127.0.0.1:8765'

  // Folders
  inboxFolder: string;               // default: 'Inbox'
  archiveFolder: string;             // default: 'Archive'

  // Review
  reviewPeriodDays: number;          // default: 7
  notesPerQuickReview: number;       // default: 10

  // AI
  aiBackend: 'server' | 'openrouter' | 'claude' | 'none';
  openrouterApiKey?: string;
  claudeApiKey?: string;
  triageModel: string;               // default: 'anthropic/claude-3-haiku'
}
```

### Settings Tab Sections

1. **Server Connection**
   - URL/port configuration
   - Test connection button
   - Status indicator

2. **Folders**
   - Inbox folder picker
   - Archive folder picker

3. **Review Settings**
   - Review period (days)
   - Notes per session

4. **AI Configuration**
   - Backend selection
   - API key inputs
   - Model selection

---

## Commands

| Command | Description | Hotkey Suggestion |
|---------|-------------|-------------------|
| `Review Recent Captures` | Open review modal | `Ctrl+Shift+R` |
| `Process Inbox` | Triage inbox items | `Ctrl+Shift+I` |
| `Start Learning Session` | Session type picker | `Ctrl+Shift+L` |
| `Capture URL` | Input URL to capture | `Ctrl+Shift+U` |
| `Check Server Status` | Display server info | - |

---

## UI Components

### Modals

1. **ReviewModal** - Card-based review interface
2. **InboxModal** - AI triage interface
3. **SessionModal** - Learning session viewer
4. **CaptureModal** - URL input for capture
5. **SessionPickerModal** - Session type selection

### Status Bar

```
📥 3 | 📚 7 | 🟢
 │    │    └── Server status (green=ok, yellow=degraded, red=offline)
 │    └── Unreviewed captures
 └── Inbox items
```

### Ribbon Icons

| Icon | Action |
|------|--------|
| 📥 | Process Inbox |
| 📚 | Review Captures |

---

## Data Flow

### Capture -> Review Flow

```
1. Content captured via browser/CLI/android
       ↓
2. Note created in vault (folder by type)
       ↓
3. Plugin detects via metadataCache
       ↓
4. Appears in review queue after N days
       ↓
5. User reviews and rates
       ↓
6. Rating saved to frontmatter
```

### Inbox Processing Flow

```
1. Capture configured to use inbox folder
       ↓
2. Note lands in Inbox/
       ↓
3. Plugin detects via vault.on('create')
       ↓
4. AI analyzes and suggests action
       ↓
5. User approves/modifies
       ↓
6. Note moved to final location
```

---

## Frontmatter Extensions

The plugin may add these fields to captured notes:

```yaml
# Existing Claudsidian fields
source: https://...
captured: '2025-12-01T12:00:00Z'
type: article
tags: [...]
summary: ...
user_rating: null          # Plugin updates this

# New fields added by plugin
reviewed_at: '2025-12-02T10:00:00Z'    # When user reviewed
session_notes: |                        # Notes taken during session
  - Key insight here
  - Action item
learning_status: unread|read|mastered   # Reading progress
last_surfaced: '2025-12-05T...'         # For spaced repetition
```

---

## Error Handling

| Scenario | User Feedback |
|----------|---------------|
| Server offline | Notice: "Claudsidian server not reachable" + fallback to local AI |
| AI API error | Notice: "AI unavailable" + manual triage mode |
| No captures to review | Notice: "All caught up!" |
| Empty inbox | Notice: "Inbox empty" |
| Invalid frontmatter | Skip note + log warning |

---

## Performance Considerations

1. **Vault scanning:** Use metadataCache, not file reads
2. **AI calls:** Batch when possible, cache results
3. **File watching:** Debounce inbox detection
4. **Modal rendering:** Lazy load note content

---

## Future Enhancements

- [ ] Spaced repetition algorithm (SM-2 or similar)
- [ ] Topic clustering/visualization
- [ ] Export learning reports
- [ ] Integration with Obsidian Sync
- [ ] Collaborative review sessions
- [ ] Natural language search across captures
- [ ] Auto-linking between related captures

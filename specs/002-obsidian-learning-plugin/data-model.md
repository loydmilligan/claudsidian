# Data Model: Obsidian Learning Plugin

**Feature**: 002-obsidian-learning-plugin
**Date**: 2025-12-05

## Overview

This document defines the data structures for the Obsidian Learning Plugin. The plugin operates primarily on Claudsidian-created notes (markdown files with YAML frontmatter) and integrates with external JSON databases.

---

## Core Entities

### 1. ClaudsidianNote

A markdown note created by the Claudsidian capture system.

**Detection**: A file is a Claudsidian note if its frontmatter contains `source` (URL), `captured` (ISO timestamp), and `type` fields.

```typescript
interface ClaudsidianNote {
  // File reference
  file: TFile;                        // Obsidian file reference
  path: string;                       // Vault-relative path

  // Claudsidian core fields (from frontmatter)
  source: string;                     // Original URL
  captured: string;                   // ISO 8601 timestamp
  type: ContentType;                  // Content classification
  tags: string[];                     // Auto-generated tags
  summary?: string;                   // AI-generated summary

  // AI metadata (from frontmatter.ai)
  ai?: {
    summary?: AICallInfo;
    tags?: AICallInfo;
  };

  // Plugin-managed fields
  user_rating?: number;               // 1-5 stars (null = unrated)
  rating_processed?: boolean;         // Synced to ratings DB
  reviewed?: boolean;                 // Reviewed in learning workflow
  reviewed_at?: string;               // ISO 8601 timestamp
  learning_analysis?: LearningAnalysis; // Cached analysis results
}

type ContentType =
  | 'article'
  | 'video'
  | 'repo'
  | 'news'
  | 'walkthrough'
  | 'printable';

interface AICallInfo {
  backend?: 'claude' | 'openrouter';
  model?: string;
  temperature?: number;
  max_tokens?: number;
}
```

**Validation Rules**:
- `source` must be a valid HTTP/HTTPS URL
- `captured` must be a valid ISO 8601 datetime
- `type` must be one of the defined ContentType values
- `user_rating` must be 1-5 if present

**State Transitions**:
```
[Captured] → [Unreviewed] → [Reviewed] → [Rated]
                    ↓
              [Analyzed]
```

---

### 2. LearningAnalysis

AI-generated learning content for a note.

```typescript
interface LearningAnalysis {
  generated_at: string;               // ISO 8601 timestamp
  model_used: string;                 // Model that generated this

  // Learning questions
  questions: LearningQuestion[];

  // Further reading
  related_topics: RelatedTopic[];

  // Source analysis (for news content)
  source_analysis?: SourceAnalysis;
}

interface LearningQuestion {
  question: string;                   // The comprehension question
  category: 'concept' | 'application' | 'critical_thinking';
}

interface RelatedTopic {
  topic: string;                      // Topic name
  relevance: string;                  // Why it's related
}

interface SourceAnalysis {
  domain: string;                     // Source domain
  bias_lean: number;                  // -2 to +2
  bias_label: string;                 // Human-readable label
  credibility_score: number;          // 0-100
  credibility_tier: 'high' | 'medium' | 'low' | 'unknown';
  counternarratives: CounternarrativeSource[];
}

interface CounternarrativeSource {
  domain: string;
  name: string;
  political_lean: number;
  credibility_score: number;
}
```

---

### 3. InboxItem

A note in the inbox folder awaiting triage.

```typescript
interface InboxItem {
  note: ClaudsidianNote;              // The underlying note

  // Triage state
  status: InboxStatus;
  processed_at?: string;              // When triaged

  // AI suggestion
  suggestion?: TriageSuggestion;
}

type InboxStatus = 'pending' | 'processing' | 'triaged';

interface TriageSuggestion {
  action: TriageAction;
  reason: string;                     // AI explanation
  target_folder?: string;             // For KEEP action
  merge_target?: string;              // For MERGE action (note path)
  confidence: number;                 // 0-1 confidence score
}

type TriageAction = 'KEEP' | 'ARCHIVE' | 'DEEP_READ' | 'MERGE';
```

---

### 4. ReviewSession

Tracks a learning review session.

```typescript
interface ReviewSession {
  id: string;                         // UUID
  started_at: string;                 // ISO 8601
  ended_at?: string;                  // ISO 8601

  // Configuration
  period_days: number;                // How far back to look
  content_types: ContentType[];       // Filtered types
  include_reviewed: boolean;          // Show already-reviewed notes

  // Progress
  notes_queue: string[];              // Paths of notes to review
  current_index: number;              // Current position
  reviewed_notes: string[];           // Paths of completed notes
  skipped_notes: string[];            // Paths of skipped notes

  // Metrics
  ratings_given: number;              // Count of ratings in session
  total_time_seconds: number;         // Session duration
}
```

---

### 5. PluginSettings

User configuration stored in Obsidian's data.json.

```typescript
interface PluginSettings {
  // API Configuration
  openrouterApiKey: string;           // Required for AI features
  sourceInfoUrl: string;              // Default: http://localhost:8000

  // AI Model Selection
  aiModel: string;                    // Default: x-ai/grok-4.1-fast
  aiTemperature: number;              // Default: 0.7
  aiMaxTokens: number;                // Default: 1000

  // Folder Configuration
  inboxFolder: string;                // Default: Inbox
  archiveFolder: string;              // Default: Archive

  // Review Settings
  reviewPeriodDays: number;           // Default: 7
  notesPerSession: number;            // Default: 10

  // Content Type Filters
  enabledTypes: ContentType[];        // Default: all types

  // Batch Processing
  batchAutoAcceptThreshold: number;   // Default: 0.8 (80%) - confidence threshold for auto-accept in batch mode

  // Feature Toggles
  enableBiasAnalysis: boolean;        // Default: true
  enableAutoInboxDetection: boolean;  // Default: false
  minCounternarrativeCredibility: number; // Default: 60

  // Cache Settings
  sourceInfoCacheTTL: number;         // Default: 3600 (1 hour)
}

const DEFAULT_SETTINGS: PluginSettings = {
  openrouterApiKey: '',
  sourceInfoUrl: 'http://localhost:8000',
  aiModel: 'x-ai/grok-4.1-fast',
  aiTemperature: 0.7,
  aiMaxTokens: 1000,
  inboxFolder: 'Inbox',
  archiveFolder: 'Archive',
  reviewPeriodDays: 7,
  notesPerSession: 10,
  enabledTypes: ['article', 'video', 'repo', 'news', 'walkthrough', 'printable'],
  batchAutoAcceptThreshold: 0.8,
  enableBiasAnalysis: true,
  enableAutoInboxDetection: false,
  minCounternarrativeCredibility: 60,
  sourceInfoCacheTTL: 3600
};
```

---

## External Data Structures

### Claudsidian Ratings Database

Located at `{vault}/.claudsidian/ratings.json`

```typescript
interface NoteRating {
  note_path: string;                  // Vault-relative path
  note_title: string;
  source_url: string;

  // User rating
  user_rating: number;                // 1-5
  rated_at: string;                   // ISO 8601

  // Content info
  content_type: ContentType;
  tags: string[];

  // AI model metadata - summary
  summary_backend: 'claude' | 'openrouter';
  summary_model: string;
  summary_temperature?: number;
  summary_max_tokens?: number;

  // AI model metadata - tags
  tags_backend: 'claude' | 'openrouter';
  tags_model: string;
  tags_temperature?: number;
  tags_max_tokens?: number;

  // Token/cost metrics
  summary_input_tokens: number;
  summary_output_tokens: number;
  tags_input_tokens: number;
  tags_output_tokens: number;
  total_cost_usd: number;

  // Timestamps
  captured_at?: string;               // ISO 8601
}
```

### Claudsidian Performance Database

Located at `{vault}/.claudsidian/model_performance.json`

```typescript
interface CapturePerformance {
  capture_id: string;
  timestamp: string;
  fixture_name: string;
  content_type: ContentType;
  url: string;
  summary_model: string;
  tags_model: string;

  // Metrics
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  time_seconds: number;

  // Quality (if scored)
  quality?: {
    accuracy: number;                 // 0-5
    completeness: number;             // 0-5
    structure: number;                // 0-5
    conciseness: number;              // 0-5
    average: number;                  // Computed
  };

  success: boolean;
  error?: string;
}
```

### SourceInfo API Response

```typescript
interface SourceInfoResponse {
  domain: string;
  name: string;
  political_lean: number;             // -2 to +2
  political_lean_label: string;       // 'Left', 'Lean Left', 'Center', 'Lean Right', 'Right'
  newsguard_score?: number;           // 0-100
  newsguard_rating?: string;          // 'High Credibility', etc.
  source_type?: string;               // 'news_media', 'fact_check', etc.
  description?: string;
}

interface CounternarrativeResponse {
  domain: string;
  name: string;
  political_lean: number;
  weighted_score: number;
}
```

---

## Relationships

```
PluginSettings (1) ─────────────────────────────────── Plugin
       │
       └─> configures

ClaudsidianNote (n) ────────────────────────────────── Vault Files
       │
       ├─> has (0..1) LearningAnalysis
       │
       ├─> has (0..1) user_rating ───────────────────> NoteRating (external)
       │
       └─> can be InboxItem (when in inbox folder)

ReviewSession (n) ──────────────────────────────────── Plugin State
       │
       └─> contains (n) ClaudsidianNote references

SourceInfoResponse (cached) ────────────────────────── External API
       │
       └─> enriches ClaudsidianNote.source_analysis
```

---

## Storage Locations

| Data | Location | Format |
|------|----------|--------|
| Notes | `{vault}/{type_folder}/*.md` | Markdown + YAML frontmatter |
| Plugin Settings | `{vault}/.obsidian/plugins/obsidian-learning-plugin/data.json` | JSON |
| Ratings (external) | `{vault}/.claudsidian/ratings.json` | JSON array |
| Performance (external) | `{vault}/.claudsidian/model_performance.json` | JSON array |
| Source Cache | Plugin memory (not persisted) | In-memory Map |
| Review Session | Plugin memory (not persisted) | In-memory object |

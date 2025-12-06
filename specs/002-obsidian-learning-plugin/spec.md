# Feature Specification: Obsidian Learning Plugin

**Feature Branch**: `002-obsidian-learning-plugin`
**Created**: 2025-12-05
**Status**: Draft
**Input**: User description: "Obsidian plugin for AI-aided learning workflows with recent capture review, inbox processing, source bias analysis, and model performance tracking"

## Overview

An Obsidian plugin that transforms passive content capture into active learning. The plugin works with Claudsidian-captured notes to help users engage deeply with their captured content through AI-generated learning questions, balanced perspective suggestions for news/political content using source bias data, and quality-based model performance tracking.

### Key Integrations

- **Claudsidian**: Note capture system with model performance tracking in `{vault}/.claudsidian/`
- **SourceInfo API**: Source bias and credibility ratings (222 sources, bias -2 to +2, NewsGuard 0-100)
- **OpenRouter**: AI backend for analysis (Grok 4.1 Fast, Minimax M2, DeepSeek Chat, GLM 4.5 Air)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Review Recent Captures (Priority: P1)

A user opens their vault after capturing several articles during the week. They want to actively engage with these captures to retain information rather than just collecting dust in their vault. The plugin surfaces recent captures based on smart filtering (content type, recency, unreviewed status), and for each note, generates learning questions that help process and retain the information.

**Why this priority**: This is the core value proposition - transforming passive captures into active learning. Without this, the plugin has no purpose.

**Independent Test**: Can be fully tested by capturing 5 articles, opening the review workflow, and verifying learning questions are generated for each. Delivers value by helping users actively engage with captured content.

**Acceptance Scenarios**:

1. **Given** a vault with 10 Claudsidian-captured notes from the past 7 days, **When** user opens the "Review Recent" workflow, **Then** notes are displayed sorted by captured date with filtering options by content type
2. **Given** a selected note in review mode, **When** AI analysis completes, **Then** 3-5 learning questions are displayed that test comprehension of key concepts
3. **Given** a user completes reviewing a note, **When** they mark it as reviewed, **Then** the note frontmatter is updated with `reviewed: true` and `reviewed_at: [timestamp]`
4. **Given** a note has already been reviewed, **When** user opens "Review Recent" workflow, **Then** that note is excluded from the queue (unless "Show Reviewed" is enabled)

---

### User Story 2 - Inbox Processing Workflow (Priority: P2)

A user has configured certain captures to go to an inbox folder (via browser extension checkbox or automatic rules based on content type/tags). They open the inbox workflow to process these items with AI assistance that suggests actions like "keep and file", "archive", "needs deeper reading", or "merge with existing note".

**Why this priority**: Inbox processing is the second core workflow, enabling users to triage captured content intelligently. Depends on basic note access from P1.

**Independent Test**: Can be fully tested by placing 5 notes in an inbox folder, running the inbox workflow, and verifying AI suggestions are provided for each with actionable buttons.

**Acceptance Scenarios**:

1. **Given** 5 notes in the configured inbox folder, **When** user opens "Process Inbox" workflow, **Then** notes are displayed in a queue with AI-suggested actions for each
2. **Given** AI suggests "Keep and File" for a note, **When** user accepts, **Then** note is moved to the appropriate content-type folder based on Claudsidian configuration
3. **Given** AI suggests "Merge with existing", **When** user accepts, **Then** a merge preview is shown with the suggested target note
4. **Given** user overrides AI suggestion and selects a different action, **When** action is executed, **Then** system learns from the override for future suggestions

---

### User Story 3 - Balanced Perspectives for News Content (Priority: P2)

A user is reviewing a news or political article from a source with a known bias. The plugin detects the source, displays its bias rating and credibility score, and suggests alternative sources with opposing perspectives to provide a balanced view on the story.

**Why this priority**: Critical differentiator for news/political content. Same priority as inbox because both extend the core review workflow.

**Independent Test**: Can be fully tested by reviewing a news article from a known biased source (e.g., MSNBC or Fox News), and verifying counternarrative sources are suggested with their credibility ratings.

**Acceptance Scenarios**:

1. **Given** a news article from "nytimes.com" (Lean Left, NewsGuard 100), **When** user opens note review, **Then** source bias indicator shows "-1 Lean Left" and "High Credibility (100)"
2. **Given** source is identified as biased (lean != 0), **When** "Get Balanced View" is clicked, **Then** SourceInfo API returns 3-5 counternarrative sources from opposing perspectives with credibility >= 60
3. **Given** counternarrative sources are displayed, **When** user clicks a source, **Then** a web search is triggered to find that source's coverage of the same story
4. **Given** a source URL is not in the SourceInfo database, **When** review opens, **Then** display "Source not rated" with option to submit for review

---

### User Story 4 - Single Note Analysis (Priority: P3)

A user right-clicks on any note (not just during workflow) and selects "Analyze for Learning" to add learning questions, further research suggestions, and (for news) balanced perspectives - the same features available in the review workflow, but on-demand for any note.

**Why this priority**: Extends core functionality to ad-hoc use. Lower priority because workflows cover the primary use case.

**Independent Test**: Can be fully tested by right-clicking any Claudsidian note, selecting "Analyze for Learning", and verifying questions are appended to the note.

**Acceptance Scenarios**:

1. **Given** any Claudsidian-captured note, **When** user invokes "Analyze for Learning" command, **Then** AI generates learning questions and appends them to the note body
2. **Given** the note is a news article with source in SourceInfo, **When** analysis completes, **Then** source credibility and suggested counternarratives are also added
3. **Given** analysis is already present in a note, **When** user runs "Analyze" again, **Then** user is prompted to replace or append to existing analysis

---

### User Story 5 - Model Quality Rating (Priority: P3)

After reviewing a note, a user rates the quality of the AI-generated summary and tags (1-5 stars). This rating is synced to the Claudsidian ratings database, contributing to model performance analytics and potentially influencing future model selection.

**Why this priority**: Enables the feedback loop for model performance. Lower priority because the system works without ratings, but ratings improve it over time.

**Independent Test**: Can be fully tested by reviewing a note, rating it 4 stars, and verifying the rating appears in `{vault}/.claudsidian/ratings.json`.

**Acceptance Scenarios**:

1. **Given** a note is open in review mode, **When** user clicks rating stars (1-5), **Then** rating is saved to note frontmatter as `user_rating: [1-5]`
2. **Given** rating is saved, **When** background sync runs (or manually triggered), **Then** rating is written to Claudsidian ratings database with model metadata
3. **Given** multiple notes are rated, **When** user views "Model Performance" dashboard, **Then** average ratings per model are displayed alongside cost metrics

---

### User Story 6 - Model Performance Dashboard (Priority: P4)

A user wants to understand which AI models are performing best for their content. The plugin generates a dashboard showing model rankings based on quality ratings, cost efficiency (OPUS score), and content type breakdowns.

**Why this priority**: Analytics feature that builds on collected data. Valuable but not essential for core learning workflows.

**Independent Test**: Can be fully tested by rating 10+ notes across different models, then opening the dashboard to verify rankings are calculated and displayed.

**Acceptance Scenarios**:

1. **Given** ratings exist in the Claudsidian database, **When** user opens "Model Performance" view, **Then** models are ranked by average quality rating
2. **Given** performance data includes costs, **When** dashboard renders, **Then** OPUS efficiency scores are shown (quality/cost ratio)
3. **Given** user clicks on a model row, **When** detail view opens, **Then** breakdown by content type is shown
4. **Given** user exports dashboard, **When** export completes, **Then** an HTML report is generated in the vault

---

### Edge Cases

- What happens when Claudsidian server is not running? Plugin should work in "offline mode" with direct vault file access, degraded without new captures
- What happens when SourceInfo API is unavailable? Display cached data if available, otherwise show "Source analysis unavailable"
- How does system handle notes without Claudsidian frontmatter? Skip non-Claudsidian notes in workflows, show warning in single-note analysis
- What happens when inbox folder is empty? Display friendly "Inbox empty" message with link to configure inbox rules
- How does system handle very long notes (>10K tokens)? Chunk content for AI analysis, process most relevant sections first
- What happens if AI API key is missing or invalid? Show clear setup instructions with link to settings
- How does system handle rate limits from OpenRouter? Exponential backoff with user notification, queue remaining items

## Requirements *(mandatory)*

### Functional Requirements

#### Core Plugin Infrastructure
- **FR-001**: Plugin MUST load in Obsidian desktop (Windows, macOS, Linux)
- **FR-002**: Plugin MUST provide settings panel for configuration (API keys, folders, AI model selection)
- **FR-003**: Plugin MUST store settings in Obsidian's data.json for the plugin
- **FR-004**: Plugin MUST detect Claudsidian notes by frontmatter schema (`source`, `captured`, `type` fields)

#### Review Recent Captures Workflow
- **FR-010**: Plugin MUST query vault for notes captured in configurable time period (default: 7 days)
- **FR-011**: Plugin MUST filter notes by content type (article, video, repo, news, walkthrough, printable)
- **FR-012**: Plugin MUST exclude notes marked as reviewed unless user enables "Show Reviewed"
- **FR-013**: Plugin MUST display notes in a queue interface sorted by captured date
- **FR-014**: Plugin MUST generate 3-5 learning questions per note using configured AI model
- **FR-015**: Plugin MUST suggest 2-3 related topics or further reading based on note content
- **FR-016**: Plugin MUST allow user to mark note as reviewed, updating frontmatter
- **FR-017**: Plugin MUST track review progress (X of Y notes reviewed)

#### Inbox Processing Workflow
- **FR-020**: Plugin MUST monitor a configurable inbox folder for new notes
- **FR-021**: Plugin MUST analyze each inbox note and suggest one of: Keep, Archive, Deep Read, Merge
- **FR-022**: Plugin MUST move notes to appropriate folders when user accepts "Keep" action
- **FR-023**: Plugin MUST move notes to archive folder when user accepts "Archive" action
- **FR-024**: Plugin MUST mark notes for later deep reading when user accepts "Deep Read"
- **FR-025**: Plugin MUST show merge preview with suggested target note for "Merge" actions
- **FR-026**: Plugin MUST support batch processing mode for processing multiple inbox items

#### Source Bias Integration
- **FR-030**: Plugin MUST extract source domain from note's `source` URL field
- **FR-031**: Plugin MUST query SourceInfo API for source credibility and bias data
- **FR-032**: Plugin MUST display source bias indicator (-2 to +2 scale with labels)
- **FR-033**: Plugin MUST display credibility tier (High/Medium/Low based on NewsGuard score)
- **FR-034**: Plugin MUST request counternarrative sources from SourceInfo when bias != 0
- **FR-035**: Plugin MUST filter counternarratives by minimum credibility (default: 60)
- **FR-036**: Plugin MUST cache source lookups to reduce API calls

#### Single Note Analysis
- **FR-040**: Plugin MUST register "Analyze for Learning" command accessible via command palette
- **FR-041**: Plugin MUST register right-click context menu item on note files
- **FR-042**: Plugin MUST append learning questions to note body under "## Learning Questions" heading
- **FR-043**: Plugin MUST append source analysis (if applicable) under "## Source Analysis" heading
- **FR-044**: Plugin MUST prompt before overwriting existing analysis sections

#### Quality Rating System
- **FR-050**: Plugin MUST display 1-5 star rating interface during note review
- **FR-051**: Plugin MUST save user rating to note frontmatter (`user_rating` field)
- **FR-052**: Plugin MUST sync ratings to Claudsidian ratings database
- **FR-053**: Plugin MUST include full rating data when syncing: user_rating, rated_at, model metadata (backend, model_id, temperature, max_tokens for summary and tags), token counts (input/output for summary and tags), and total_cost_usd

#### Model Performance Dashboard
- **FR-060**: Plugin MUST read performance data from `{vault}/.claudsidian/model_performance.json`
- **FR-061**: Plugin MUST read ratings data from `{vault}/.claudsidian/ratings.json`
- **FR-062**: Plugin MUST calculate and display average quality rating per model
- **FR-063**: Plugin MUST calculate and display OPUS efficiency score (quality/cost ratio)
- **FR-064**: Plugin MUST allow filtering by content type, date range, and model
- **FR-065**: Plugin MUST export dashboard as HTML report to `{vault}/reports/performance/model-performance.html` (single file, overwritten on each export)

#### AI Integration
- **FR-070**: Plugin MUST support OpenRouter as AI backend
- **FR-071**: Plugin MUST support configurable model selection from presets (Grok 4.1 Fast, Minimax M2, DeepSeek Chat, GLM 4.5 Air Free)
- **FR-072**: Plugin MUST handle API errors gracefully with user-friendly messages
- **FR-073**: Plugin MUST implement exponential backoff for rate limiting
- **FR-074**: Plugin MUST track token usage and estimated costs per analysis

### Key Entities

- **ClaudsidianNote**: A markdown note with Claudsidian frontmatter (source URL, captured timestamp, type, tags, AI metadata, optional user_rating)
- **InboxItem**: A note in the inbox folder pending triage, with suggested action and AI reasoning
- **SourceInfo**: Credibility and bias data for a news source (domain, bias lean, NewsGuard score, source type)
- **ReviewSession**: A session tracking which notes have been reviewed, progress, and timing
- **ModelPerformance**: Aggregated statistics for an AI model (average rating, cost, OPUS score, capture count)
- **LearningAnalysis**: AI-generated content for a note (questions, related topics, source analysis)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can review a captured note and receive learning questions within 60 seconds of selecting the note (longer for slow models)
- **SC-002**: Inbox processing provides AI suggestions for 95% of notes with valid Claudsidian frontmatter
- **SC-003**: Source bias data is displayed for 80% of news articles (based on SourceInfo database coverage of ~220 sources)
- **SC-004**: Users complete reviewing a 10-note queue in under 15 minutes (average 90 seconds per note)
- **SC-005**: Model quality ratings are successfully synced to Claudsidian database for 100% of rated notes
- **SC-006**: Dashboard displays within 3 seconds for vaults with up to 1000 rated notes

### Hypotheses to Validate (Manual Measurement)

- **HV-001**: Users report increased retention of captured content (validate via optional user feedback)
- **HV-002**: Users who try inbox processing continue using it after first week (validate via usage patterns)

## Assumptions

- Claudsidian capture system is already installed and operational in the user's vault
- SourceInfo API is running locally at `http://localhost:8000` (or configurable URL)
- User has an OpenRouter API key for AI analysis features
- Notes in inbox folder follow standard Claudsidian frontmatter format
- Vault uses default Obsidian file structure without heavy plugin modifications
- User has basic familiarity with Obsidian's command palette and settings

## Out of Scope

- Browser extension modifications (inbox checkbox is a separate Claudsidian browser-extension feature)
- Automatic model selection based on rankings (future enhancement for Claudsidian core)
- Adaptive learning from user triage overrides (v1.0 logs overrides for future use; active learning is a future enhancement)
- SourceInfo database expansion (managed by separate SourceInfo project)
- Mobile Obsidian support (desktop-first, mobile compatibility is a future goal)
- Spaced repetition scheduling (potential future enhancement)
- Multi-vault support

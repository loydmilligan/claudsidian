# Feature Specification: Claudsidian Knowledge Capture Core

**Feature Branch**: `001-knowledge-capture-core`
**Created**: 2025-12-01
**Status**: Draft
**Input**: AI-powered knowledge capture tool for Obsidian with multi-platform input and automated organization

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Capture Article from Browser (Priority: P1)

As a user browsing the web, I find an interesting article I want to save for later learning. I click a browser extension button, and within seconds the article is processed, summarized, tagged, and saved to my Obsidian vault as a properly formatted learning note - without me having to organize anything.

**Why this priority**: This is the core use case - frictionless capture from the most common discovery source (web browsing). If this works well, the tool delivers immediate value.

**Independent Test**: Can be fully tested by installing the browser extension, clicking capture on any article URL, and verifying a formatted note appears in the vault within 60 seconds.

**Acceptance Scenarios**:

1. **Given** I am viewing an article in my browser, **When** I click the Claudsidian capture button, **Then** a note is created in my vault with title, summary, key points, tags, and source link within 60 seconds.
2. **Given** I capture an article, **When** the note is created, **Then** it is automatically placed in the correct folder based on content type and linked to related existing notes.
3. **Given** I capture an article about a topic I've captured before, **When** the note is created, **Then** it includes backlinks to related notes on the same topic.

---

### User Story 2 - Capture via CLI Command (Priority: P2)

As a terminal-oriented user, I want to quickly capture content by pasting a URL into a command. I run a simple command with the URL, and the system processes it the same way the browser extension would.

**Why this priority**: Terminal users need a fast path that doesn't require switching to a browser. This also serves as the foundation for automation and scripting.

**Independent Test**: Can be fully tested by running the CLI with a URL and verifying the vault note is created correctly.

**Acceptance Scenarios**:

1. **Given** I have a URL copied, **When** I run `claudsidian capture <url>`, **Then** the content is processed and saved to my vault.
2. **Given** I run the capture command, **When** processing completes, **Then** I see a confirmation message with the note path and generated tags.

---

### User Story 3 - Capture YouTube Video Notes (Priority: P3)

As a user who learns from YouTube videos, I want to capture a video URL and have the system extract the transcript, generate a summary with timestamps, and create a video note I can reference later.

**Why this priority**: Video content is a major learning source. Transcript extraction and timestamped summaries add significant value over manual note-taking.

**Independent Test**: Can be tested by capturing a YouTube URL and verifying the note includes transcript excerpts, summary, and timestamp markers.

**Acceptance Scenarios**:

1. **Given** I capture a YouTube URL, **When** processing completes, **Then** the note includes video title, channel, summary, key points with timestamps, and embedded link.
2. **Given** I capture a long video (>30 minutes), **When** processing completes, **Then** the note includes chapter markers or logical section breaks.

---

### User Story 4 - Track GitHub Repository (Priority: P4)

As a developer who discovers interesting tools and projects, I want to capture a GitHub repo URL and have it processed into a project tracking note with tech stack, purpose, and why it's interesting.

**Why this priority**: Developers constantly discover repos worth tracking. Auto-extracting README info and tech stack reduces manual effort.

**Independent Test**: Can be tested by capturing a GitHub repo URL and verifying the project note includes extracted metadata.

**Acceptance Scenarios**:

1. **Given** I capture a GitHub repo URL, **When** processing completes, **Then** the note includes repo name, description, primary language, star count, and key README content.
2. **Given** I capture a repo, **When** the note is created, **Then** it is tagged with relevant technology tags and linked to other tracked projects using similar tech.

---

### User Story 5 - Capture News Article (Priority: P5)

As someone who follows tech, political, and business news, I want to quickly capture news articles with summaries and key facts, organized into a news digest format.

**Why this priority**: News consumption benefits from quick summaries. Capturing the essence without full-text reading saves time.

**Independent Test**: Can be tested by capturing a news URL and verifying the digest entry is created with summary and key facts.

**Acceptance Scenarios**:

1. **Given** I capture a news article URL, **When** processing completes, **Then** the note includes headline, source, publication date, summary, and key facts.
2. **Given** I capture multiple news articles, **When** I view my news folder, **Then** each article is its own note, organized by date and tagged by topic.

---

### User Story 6 - Capture Walkthrough/Tutorial (Priority: P6)

As someone learning new skills, I want to capture how-to articles and have the system extract the steps, prerequisites, and common pitfalls into a structured guide format.

**Why this priority**: Walkthroughs need structured extraction to be useful later. Step-by-step format with prerequisites makes them actionable.

**Independent Test**: Can be tested by capturing a how-to article and verifying the note includes extracted steps and prerequisites.

**Acceptance Scenarios**:

1. **Given** I capture a how-to article URL, **When** processing completes, **Then** the note includes extracted steps, prerequisites, warnings/gotchas, and code blocks (if any).
2. **Given** I capture a walkthrough, **When** the note is created, **Then** it includes a difficulty level and estimated time if mentioned in the source.

---

### User Story 7 - Inbox File Drop Capture (Priority: P7)

As a user who prefers drag-and-drop workflows, I want to drop URLs or content into an inbox file, and have the system automatically process them in the background.

**Why this priority**: Some users prefer file-based workflows over extensions or CLI. This enables batch processing and asynchronous capture.

**Independent Test**: Can be tested by adding a URL to the inbox file and verifying it gets processed and removed from inbox.

**Acceptance Scenarios**:

1. **Given** I add a URL to my inbox.md file, **When** the file watcher detects the change, **Then** the URL is processed and the entry is removed from inbox.md.
2. **Given** I add multiple URLs to inbox.md, **When** processing completes, **Then** each URL is processed independently and failures don't block other captures.

---

### User Story 8 - Mobile Capture via Android Widget (Priority: P8)

As an Android user, I want to share content to Claudsidian from any app and have it sent to my desktop for processing when I'm on the same local network.

**Why this priority**: Mobile discovery is common but full processing can happen on desktop. This bridges the mobile-to-desktop workflow via local network.

**Independent Test**: Can be tested by sharing a URL to the Android app while on the same WiFi as the desktop, and verifying it gets processed.

**Acceptance Scenarios**:

1. **Given** I share a URL from any Android app to Claudsidian, **When** my phone is on the same network as my desktop, **Then** the URL is sent to the desktop service for processing.
2. **Given** I share a URL while not on my home network, **When** I return home and open the app, **Then** queued items are sent to the desktop for processing.
3. **Given** the desktop service is not running, **When** I share a URL, **Then** it is queued locally on the phone until the desktop becomes available.

---

### User Story 9 - Track 3D Printable Models (Priority: P9)

As a 3D printing enthusiast, I want to capture links to printable models (Thingiverse, Printables, etc.) with metadata about print settings and file types.

**Why this priority**: Niche but valuable for tracking interesting models. Lower priority as it's a specific content type.

**Independent Test**: Can be tested by capturing a Thingiverse/Printables URL and verifying the note includes model metadata.

**Acceptance Scenarios**:

1. **Given** I capture a 3D model URL, **When** processing completes, **Then** the note includes model name, creator, file types, and suggested print settings if available.
2. **Given** I capture a model, **When** the note is created, **Then** it is tagged with material type, print difficulty, and category tags.

---

### Edge Cases

- What happens when the URL is behind a paywall or login wall? System should capture available metadata and note that full content was inaccessible.
- How does the system handle URLs that resolve to non-content pages (404, redirects to homepage)? System should report the error and not create a broken note.
- What happens when AI API is unavailable? System should queue the capture for retry and notify the user.
- How does the system handle duplicate captures of the same URL? System should detect duplicates, skip silently, and display a message that the note already exists with a link to it.
- What happens when the vault folder is not accessible (permissions, disk full)? System should fail gracefully with clear error message.

## Requirements *(mandatory)*

### Functional Requirements

**Capture & Input**
- **FR-001**: System MUST accept URLs from browser extension with single-click capture.
- **FR-002**: System MUST accept URLs via CLI command with syntax `claudsidian capture <url>`.
- **FR-003**: System MUST monitor an inbox file for URLs and process them automatically.
- **FR-004**: System MUST provide an Android share target that sends URLs to desktop via local network API (with local queue for offline capture).
- **FR-005**: System MUST detect content type (article, video, repo, news, walkthrough, 3D model) from URL and content analysis.

**AI Processing**
- **FR-006**: System MUST use Claude API for complex tasks: summarization, tag generation, relationship mapping.
- **FR-007**: System MUST use OpenRouter API for simpler tasks: basic extraction, formatting.
- **FR-008**: System MUST generate relevant tags based on content analysis.
- **FR-009**: System MUST identify and create backlinks to related existing notes in the vault.
- **FR-010**: System MUST generate summaries appropriate to content type (key points for articles, timestamps for videos, steps for walkthroughs).

**Output & Organization**
- **FR-011**: System MUST write properly formatted markdown files directly to the Obsidian vault folder.
- **FR-012**: System MUST auto-assign folder location based on content type.
- **FR-013**: System MUST use content-type-specific templates for each note type.
- **FR-014**: System MUST preserve source URL and capture timestamp in every note.
- **FR-015**: System MUST complete capture-to-note process within 60 seconds for standard content.

**Configuration**
- **FR-016**: System MUST allow configuration of vault folder path.
- **FR-017**: System MUST allow configuration of API keys (Claude, OpenRouter).
- **FR-018**: System MUST allow customization of folder structure for each content type.
- **FR-019**: System MUST store configuration locally without requiring cloud accounts.

**Error Handling**
- **FR-020**: System MUST queue failed captures for retry when AI API is unavailable.
- **FR-021**: System MUST detect duplicate URL captures, skip processing, and display a message with link to existing note.
- **FR-022**: System MUST provide clear error messages for common failure modes.

### Key Entities

- **Capture**: A single URL submission with source (browser/CLI/inbox/mobile), timestamp, and processing status.
- **Note**: The markdown output stored in the vault with content, metadata, tags, and backlinks.
- **Content Type**: Classification of captured content (article, video, repo, news, walkthrough, printable) determining processing pipeline and template.
- **Tag**: Auto-generated or user-defined labels for organizing and finding notes.
- **Backlink**: Connection between notes based on topic, tag, or explicit reference.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can capture any supported content type in 3 or fewer actions (click/command/drop).
- **SC-002**: Captured content appears as a formatted note in the vault within 60 seconds.
- **SC-003**: 90% of auto-generated tags are relevant to the content (user doesn't need to remove/change them).
- **SC-004**: System correctly identifies content type for 95% of supported URLs without user intervention.
- **SC-005**: Users spend zero time on manual organization for 80% of captured content.
- **SC-006**: System successfully processes queued captures within 5 minutes of connectivity restoration.
- **SC-007**: Duplicate detection prevents redundant notes 99% of the time.
- **SC-008**: Generated summaries capture the essential information such that users can recall the content without re-reading the source 80% of the time.

## Assumptions

- User has an existing Obsidian vault folder on their local machine.
- User has valid API keys for Claude and/or OpenRouter.
- User's machine has internet connectivity for AI API calls.
- YouTube videos have available transcripts or auto-generated captions.
- GitHub repos have public READMEs accessible without authentication.
- 3D model sites (Thingiverse, Printables) have scrapable metadata.
- Android mobile capture communicates with desktop via local network API when on same WiFi; queues locally when offline.
- Browser extension targets Chrome/Firefox as primary browsers.

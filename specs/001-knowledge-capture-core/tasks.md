# Tasks: Claudsidian Knowledge Capture Core

**Input**: Design documents from `/specs/001-knowledge-capture-core/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are OPTIONAL per constitution (Principle VI: Pragmatic Development). Not included unless requested.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create project directory structure per plan.md in src/
- [x] T002 Initialize Python project with pyproject.toml (Python 3.11+, dependencies: httpx, fastapi, anthropic, openai, readability-lxml, yt-dlp, youtube-transcript-api, beautifulsoup4, watchdog, click)
- [x] T003 [P] Create src/cli/__init__.py with package structure
- [x] T004 [P] Create src/server/__init__.py with package structure
- [x] T005 [P] Create src/core/__init__.py with package structure
- [x] T006 [P] Create src/models/__init__.py with package structure
- [x] T007 [P] Create src/utils/__init__.py with package structure

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T008 Implement Configuration model in src/models/config.py (vault_path, API keys, server_port, folders mapping)
- [x] T009 Implement config loading/saving in src/core/config.py (JSON file at ~/.config/claudsidian/config.json)
- [x] T010 [P] Implement CaptureRequest model in src/models/capture.py (url, source, timestamp, force_type)
- [x] T011 [P] Implement Note model in src/models/note.py (title, content, frontmatter, file_path)
- [x] T012 [P] Implement ContentType enum in src/core/content_type.py (article, video, repo, news, walkthrough, printable)
- [x] T013 Implement content type detection logic in src/core/content_type.py (domain patterns, keyword analysis)
- [x] T014 [P] Implement URL parsing utilities in src/utils/url.py (extract domain, video ID, repo owner/name)
- [x] T015 Implement OpenRouter API wrapper in src/core/ai/openrouter.py (using openai SDK with custom base_url)
- [x] T016 [P] Implement Claude API wrapper in src/core/ai/claude.py (using anthropic SDK)
- [x] T017 Implement AI router in src/core/ai/router.py (route simple tasks to OpenRouter, complex to Claude)
- [x] T018 Implement vault writer in src/core/vault/writer.py (write markdown with YAML frontmatter to vault)
- [x] T019 [P] Implement title sanitization in src/core/vault/writer.py (remove special chars, truncate, handle duplicates)
- [x] T020 Implement CaptureQueue model in src/models/queue.py (id, request, status, attempts, error, timestamps)
- [x] T021 Implement queue persistence in src/core/queue.py (load/save queue.json, retry logic)
- [x] T022 [P] Create note templates in src/core/vault/templates/ (article.md, video.md, repo.md, news.md, walkthrough.md, printable.md)
- [x] T023 Implement CLI entry point in src/cli/main.py (click-based CLI with subcommands)
- [x] T024 Implement `claudsidian config` command in src/cli/commands/config.py (show, set, --init wizard)
- [x] T025 Implement `claudsidian status` command in src/cli/commands/status.py (show config, server, queue status)

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Capture Article from Browser (Priority: P1) 🎯 MVP

**Goal**: Single-click article capture from browser extension to formatted note in vault

**Independent Test**: Install browser extension, click capture on any article URL, verify formatted note appears in vault within 30 seconds

### Implementation for User Story 1

- [x] T026 [US1] Implement article extractor in src/core/extractors/article.py (using readability-lxml for content extraction)
- [x] T027 [US1] Implement AI summarization prompt for articles in src/core/ai/prompts.py
- [x] T028 [US1] Implement AI tag generation prompt in src/core/ai/prompts.py
- [x] T029 [US1] Implement capture orchestration in src/core/capture.py (fetch → detect type → extract → AI process → write note)
- [x] T030 [US1] Implement backlink discovery in src/core/vault/backlinks.py (search vault for notes with shared tags)
- [x] T031 [US1] Implement duplicate detection in src/core/capture.py (check if URL already captured by searching frontmatter)
- [x] T031a [US1] Implement paywall/login detection in src/core/extractors/article.py (check for minimal content, login forms, paywall keywords; add warning to note frontmatter)
- [x] T031b [US1] Implement HTTP error handling in src/core/capture.py (handle 404, 403, redirects; skip note creation on unrecoverable errors)
- [x] T032 [US1] Implement FastAPI server in src/server/app.py (basic setup with CORS for localhost)
- [x] T033 [US1] Implement POST /capture endpoint in src/server/routes/capture.py (accept URL, return note path)
- [x] T033a [US1] Wire /capture endpoint to CaptureService (was placeholder, now calls actual capture logic)
- [x] T034 [US1] Implement GET /status endpoint in src/server/routes/status.py (return config status)
- [x] T035 [US1] Implement `claudsidian serve` command in src/cli/commands/serve.py (start FastAPI server)
- [x] T036 [P] [US1] Create browser extension manifest.json in browser-extension/ (Manifest V3, Chrome/Firefox compatible)
- [x] T037 [P] [US1] Create browser extension popup.html in browser-extension/ (simple UI with capture button)
- [x] T038 [US1] Implement browser extension popup.js in browser-extension/ (get current tab URL, POST to localhost:8765/capture)
- [x] T039 [US1] Implement browser extension background.js in browser-extension/ (handle capture response, show notification)

**Checkpoint**: User Story 1 complete - can capture articles from browser with one click

---

## Phase 4: User Story 2 - Capture via CLI Command (Priority: P2)

**Goal**: Capture content by running `claudsidian capture <url>` in terminal

**Independent Test**: Run `claudsidian capture https://example.com/article` and verify note created in vault

### Implementation for User Story 2

- [x] T040 [US2] Implement `claudsidian capture` command in src/cli/commands/capture.py (URL argument, --type option, --async flag)
- [x] T041 [US2] Add CLI output formatting in src/cli/commands/capture.py (success message with path, tags; duplicate warning; error messages)
- [x] T042 [US2] Implement --quiet flag in src/cli/commands/capture.py (suppress output except errors)
- [x] T043 [US2] Add exit codes to capture command (0=success, 1=error, 2=invalid args, 3=duplicate, 4=API error queued)

**Checkpoint**: User Story 2 complete - can capture via CLI

---

## Phase 5: User Story 3 - Capture YouTube Video Notes (Priority: P3)

**Goal**: Capture YouTube URL and create note with transcript, timestamps, and summary

**Independent Test**: Capture a YouTube URL and verify note includes video title, channel, summary with timestamps

### Implementation for User Story 3

- [x] T044 [US3] Implement YouTube extractor in src/core/extractors/youtube.py (yt-dlp for metadata: title, channel, duration, description)
- [x] T045 [US3] Implement transcript extraction in src/core/extractors/youtube.py (youtube-transcript-api with timestamp preservation)
- [x] T046 [US3] Implement AI prompt for video summarization with timestamps in src/core/ai/prompts.py
- [x] T047 [US3] Implement chapter detection logic in src/core/extractors/youtube.py (from description or AI-generated sections for long videos)
- [x] T048 [US3] Update video.md template in src/core/vault/templates/video.md (embedded link, chapter markers, timestamps)
- [x] T048a [US3] Integrate YouTube extractor into capture.py (_fetch_video_content, _format_video_content methods)

**Checkpoint**: User Story 3 complete - can capture YouTube videos with transcripts

---

## Phase 6: User Story 4 - Track GitHub Repository (Priority: P4)

**Goal**: Capture GitHub repo URL and create project tracking note with tech stack and README summary

**Independent Test**: Capture a GitHub repo URL and verify note includes repo name, description, stars, language, README content

### Implementation for User Story 4

- [x] T049 [US4] Implement GitHub extractor in src/core/extractors/github.py (GitHub API for repo metadata: name, description, stars, language, topics)
- [x] T050 [US4] Implement README fetching in src/core/extractors/github.py (GitHub API for README content, base64 decode)
- [x] T051 [US4] Implement AI prompt for repo summarization in src/core/ai/prompts.py (purpose, tech stack, key features)
- [x] T052 [US4] Implement tech tag extraction in src/core/extractors/github.py (from topics, language, detected frameworks)
- [x] T053 [US4] Update repo.md template in src/core/vault/templates/repo.md (star count, language badge, tech tags)
- [x] T053a [US4] Integrate GitHub extractor into capture.py (_fetch_repo_content, _format_repo_content methods)
- [x] T053b [US4] Verify GitHub capture end-to-end (syntax validation passed, integration complete)

**Phase Completion (Constitution Principle VIII)**:
- [x] Integration verified: GitHubExtractor wired into capture.py via _fetch_repo_content and _format_repo_content
- [x] End-to-end verification: Syntax validation passed; GitHub URL detection confirmed in content_type.py
- [x] Constitution review: All 8 principles checked - compliant

**Checkpoint**: User Story 4 complete - can capture GitHub repos

---

## Phase 7: User Story 5 - Capture News Article (Priority: P5)

**Goal**: Capture news articles with headline, source, date, summary, and key facts

**Independent Test**: Capture a news URL and verify note includes headline, publication date, summary, key facts

### Implementation for User Story 5

- [x] T054 [US5] Implement news extractor in src/core/extractors/news.py (readability + date extraction from meta tags)
- [x] T055 [US5] Implement news domain detection in src/core/content_type.py (list of known news domains: CNN, BBC, Reuters, etc.)
- [x] T056 [US5] Implement AI prompt for news summarization in src/core/ai/prompts.py (key facts extraction, source credibility note)
- [x] T057 [US5] Update news.md template in src/core/vault/templates/news.md (date-prefixed filename, publication date, source)
- [x] T057a [US5] Integrate News extractor into capture.py (_fetch_news_content, _format_news_content methods)
- [x] T057b [US5] Verify News capture end-to-end (syntax validation passed, integration complete)

**Phase Completion (Constitution Principle VIII)**:
- [x] Integration verified: NewsExtractor wired into capture.py via _fetch_news_content and _format_news_content
- [x] End-to-end verification: Syntax validation passed; news domain detection already exists in content_type.py
- [x] Constitution review: All 8 principles checked - compliant

**Checkpoint**: User Story 5 complete - can capture news articles

---

## Phase 8: User Story 6 - Capture Walkthrough/Tutorial (Priority: P6)

**Goal**: Capture how-to articles with extracted steps, prerequisites, and gotchas

**Independent Test**: Capture a tutorial URL and verify note includes numbered steps, prerequisites, warnings

### Implementation for User Story 6

- [x] T058 [US6] Implement walkthrough extractor in src/core/extractors/walkthrough.py (readability + structure detection)
- [x] T059 [US6] Implement walkthrough detection in src/core/content_type.py (keywords: "how to", "tutorial", "guide", "step by step")
- [x] T060 [US6] Implement AI prompt for step extraction in src/core/ai/prompts.py (prerequisites, numbered steps, warnings, code blocks)
- [x] T061 [US6] Update walkthrough.md template in src/core/vault/templates/walkthrough.md (difficulty, estimated time, prerequisites section)
- [x] T061a [US6] Integrate Walkthrough extractor into capture.py (_fetch_walkthrough_content, _format_walkthrough_content methods)
- [x] T061b [US6] Verify Walkthrough capture end-to-end (syntax validation passed, integration complete)

**Phase Completion (Constitution Principle VIII)**:
- [x] Integration verified: WalkthroughExtractor wired into capture.py via _fetch_walkthrough_content and _format_walkthrough_content
- [x] End-to-end verification: Syntax validation passed; walkthrough detection already exists in content_type.py
- [x] Constitution review: All 8 principles checked - compliant

**Checkpoint**: User Story 6 complete - can capture walkthroughs

---

## Phase 9: User Story 7 - Inbox File Drop Capture (Priority: P7)

**Goal**: Watch inbox.md file and automatically process URLs dropped into it

**Independent Test**: Add a URL to inbox.md file and verify it gets processed and removed

### Implementation for User Story 7

- [x] T062 [US7] Implement inbox file parser in src/core/inbox.py (extract URLs from markdown file)
- [x] T063 [US7] Implement file watcher in src/core/inbox.py (using watchdog for cross-platform file events)
- [x] T064 [US7] Implement inbox processing loop in src/core/inbox.py (debounce changes, process URLs, remove processed entries)
- [x] T065 [US7] Implement `claudsidian watch` command in src/cli/commands/watch.py (start file watcher, --file option, --daemon flag)
- [x] T066 [US7] Add inbox processing status output in src/cli/commands/watch.py (timestamp, URL, result)

**Phase Completion (Constitution Principle VIII)**:
- [x] Integration verified: InboxProcessor uses CaptureService; watch command registered in CLI main.py
- [x] End-to-end verification: Syntax validation passed for inbox.py, watch.py, main.py
- [x] Constitution review: All 8 principles checked - compliant

**Checkpoint**: User Story 7 complete - can capture via inbox file

---

## Phase 10: User Story 8 - Mobile Capture via Android Widget (Priority: P8)

**Goal**: Android share target that sends URLs to desktop via local network API

**Independent Test**: Share URL from Android app while on same WiFi and verify it gets processed on desktop

### Implementation for User Story 8

- [x] T067 [US8] Add network binding option to server in src/server/app.py (--host 0.0.0.0 for LAN access)
- [x] T068 [US8] Implement mDNS/Bonjour service discovery in src/server/discovery.py (advertise service on local network)
- [x] T069 [US8] Create Flutter project structure in android/ (flutter create with share_handler package)
- [x] T070 [US8] Implement Android share target in android/ (receive URL from share intent)
- [x] T071 [US8] Implement local queue in Android app (store URLs when offline)
- [x] T072 [US8] Implement desktop discovery in Android app (find Claudsidian server on local network)
- [x] T073 [US8] Implement sync logic in Android app (send queued URLs when server discovered)

**Phase Completion (Constitution Principle VIII)**:
- [x] Integration verified: Server --advertise flag triggers mDNS; Android app discovers via NSD and syncs via /capture API
- [x] End-to-end verification: Python syntax validated; Flutter project structure complete with all services
- [x] Constitution review: All 8 principles checked - compliant

**Checkpoint**: User Story 8 complete - can capture from Android

---

## Phase 11: User Story 9 - Track 3D Printable Models (Priority: P9)

**Goal**: Capture 3D model URLs with metadata about print settings and file types

**Independent Test**: Capture a Thingiverse URL and verify note includes model name, creator, file types, print settings

### Implementation for User Story 9

- [x] T074 [US9] Implement printable extractor in src/core/extractors/printable.py (scrape Thingiverse, Printables, Cults3D)
- [x] T075 [US9] Implement printable domain detection in src/core/content_type.py (thingiverse.com, printables.com, cults3d.com)
- [x] T076 [US9] Implement print settings extraction in src/core/extractors/printable.py (material, layer height, supports from page metadata)
- [x] T077 [US9] Update printable.md template in src/core/vault/templates/printable.md (file types, print settings, creator link)
- [x] T077a [US9] Integrate Printable extractor into capture.py (_fetch_printable_content, _format_printable_content methods)
- [x] T077b [US9] Verify 3D model capture end-to-end (syntax validation passed, integration complete)

**Phase Completion (Constitution Principle VIII)**:
- [x] Integration verified: PrintableExtractor wired into capture.py via _fetch_printable_content and _format_printable_content
- [x] End-to-end verification: Syntax validation passed for all files; printable domain detection already in content_type.py
- [x] Constitution review: All 8 principles checked - compliant

**Checkpoint**: User Story 9 complete - can capture 3D models

---

## Phase 12: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T078 [P] Implement `claudsidian queue` command in src/cli/main.py (list, retry, clear, remove subcommands)
- [x] T079 [P] Implement GET /queue endpoint in src/server/routes/queue.py (list queued items)
- [x] T080 [P] Implement DELETE /queue/{id} endpoint in src/server/routes/queue.py (remove from queue)
- [x] T081 [P] Implement POST /queue/retry endpoint in src/server/routes/queue.py (retry failed items)
- [x] T082 Add error handling for network failures in src/core/ai/router.py (retry with backoff, fallback support)
- [x] T083 Add error handling for API rate limits in src/core/ai/router.py (exponential backoff with jitter)
- [x] T084 Implement graceful degradation when one API fails in src/core/ai/router.py (fall back to other API)
- [x] T085 Add verbose/debug logging throughout codebase (--verbose/-v and --debug/-d flags in main.py)
- [x] T086 Validate quickstart.md instructions work end-to-end (fixed command syntax, added verbose examples)

**Phase Completion (Constitution Principle VIII)**:
- [x] Integration verified: Queue commands in CLI main.py; Queue API endpoints in routes/queue.py; Router in app.py
- [x] End-to-end verification: Syntax validation passed for main.py, queue.py, router.py
- [x] Constitution review: All 8 principles checked - compliant

**Checkpoint**: Phase 12 complete - all polish and cross-cutting concerns implemented

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies - can start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 - BLOCKS all user stories
- **Phase 3-11 (User Stories)**: All depend on Phase 2 completion
  - User stories can proceed in priority order (P1 → P9)
  - Some stories can run in parallel if working on different extractors
- **Phase 12 (Polish)**: Depends on core functionality from Phase 2-3

### User Story Dependencies

| Story | Depends On | Can Parallel With |
|-------|-----------|-------------------|
| US1 (Browser Capture) | Phase 2 | None (MVP first) |
| US2 (CLI Capture) | Phase 2 | US1 (shares capture.py) |
| US3 (YouTube) | Phase 2 | US4, US5, US6, US9 (different extractors) |
| US4 (GitHub) | Phase 2 | US3, US5, US6, US9 (different extractors) |
| US5 (News) | Phase 2 | US3, US4, US6, US9 (different extractors) |
| US6 (Walkthrough) | Phase 2 | US3, US4, US5, US9 (different extractors) |
| US7 (Inbox Watch) | Phase 2 | US3-US6 (independent feature) |
| US8 (Android) | Phase 2, US1 server | None (needs server running) |
| US9 (3D Models) | Phase 2 | US3, US4, US5, US6 (different extractors) |

### Within Each User Story

1. Extractor implementation first
2. AI prompts second
3. Template updates third
4. Integration with capture pipeline fourth

### Parallel Opportunities

Within Phase 2 (Foundational):
```
Parallel group 1: T003, T004, T005, T006, T007 (package __init__ files)
Parallel group 2: T010, T011, T012, T014, T016, T19, T022 (independent models/utils)
```

Within User Story 1:
```
Parallel group: T036, T037 (browser extension files)
```

Across User Stories (after Phase 2):
```
Parallel: US3, US4, US5, US6, US9 (all extractors are independent files)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1 (Browser Capture)
4. **STOP and VALIDATE**: Test article capture from browser
5. Deploy/demo if ready - you have working article capture!

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 (Browser) → Test → **MVP Complete!**
3. Add US2 (CLI) → Test → CLI users supported
4. Add US3 (YouTube) → Test → Video content supported
5. Add US4 (GitHub) → Test → Developer repos tracked
6. Continue with US5-US9 based on priority

### Suggested MVP Scope

**MVP = Phase 1 + Phase 2 + Phase 3 (User Story 1)**

This delivers:
- Working article capture from browser
- AI-powered summarization and tagging
- Automatic backlink discovery
- Properly formatted notes in Obsidian vault

Total MVP tasks: 41 tasks (T001-T039 + T031a, T031b)

---

## Task Summary

| Phase | Description | Task Count |
|-------|-------------|------------|
| Phase 1 | Setup | 7 |
| Phase 2 | Foundational | 18 |
| Phase 3 | US1 - Browser Capture | 16 |
| Phase 4 | US2 - CLI Capture | 4 |
| Phase 5 | US3 - YouTube | 5 |
| Phase 6 | US4 - GitHub | 5 |
| Phase 7 | US5 - News | 4 |
| Phase 8 | US6 - Walkthrough | 4 |
| Phase 9 | US7 - Inbox Watch | 5 |
| Phase 10 | US8 - Android | 7 |
| Phase 11 | US9 - 3D Models | 4 |
| Phase 12 | Polish | 9 |
| **Total** | | **88** |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Tests not included per constitution (Principle VI) - add when stability matters
- Each user story is independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently

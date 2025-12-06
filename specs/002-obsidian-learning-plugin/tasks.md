# Tasks: Obsidian Learning Plugin

**Input**: Design documents from `/specs/002-obsidian-learning-plugin/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Smoke tests only (per constitution Principle VI - Pragmatic Development)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

All paths are relative to the new plugin repository root: `obsidian-learning-plugin/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and Obsidian plugin scaffolding

- [X] T001 Clone obsidian-sample-plugin template and rename to obsidian-learning-plugin/
- [X] T002 Update manifest.json with plugin metadata (id: obsidian-learning-plugin, name: Learning Plugin)
- [X] T003 Update package.json with project name and add gray-matter dependency
- [X] T004 [P] Create src/types.ts with all TypeScript interfaces from data-model.md
- [X] T005 [P] Create styles.css with base plugin styles (modals, badges, stars)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T006 Implement PluginSettings interface and DEFAULT_SETTINGS in src/settings.ts
- [X] T007 Create settings tab UI with all configuration options in src/settings.ts (include batchAutoAcceptThreshold slider: 50-95%, default 80%)
- [X] T008 Implement plugin entry point with settings load/save in src/main.ts
- [X] T009 [P] Implement OpenRouter API client with requestUrl() in src/services/ai.ts (include basic 429 rate-limit error handling with user notification)
- [X] T010 [P] Implement SourceInfo API client with requestUrl() in src/services/sourceinfo.ts
- [X] T011 Implement vault service for Claudsidian note detection and frontmatter ops in src/services/vault.ts
- [X] T012 Register "Review Recent Captures" command in src/main.ts
- [X] T013 Register "Process Inbox" command in src/main.ts
- [X] T014 Register "Analyze for Learning" command in src/main.ts
- [X] T015 Verify plugin loads in Obsidian and settings tab displays

**Checkpoint**: Foundation ready - user story implementation can now begin

**Phase Completion (Constitution Principle VIII)**:
- [ ] Integration verified: Plugin loads, commands registered, settings persist
- [ ] End-to-end verification: Manual test with real vault
- [ ] Constitution review: All 8 principles checked

---

## Phase 3: User Story 1 - Review Recent Captures (Priority: P1) 🎯 MVP

**Goal**: Surface recent Claudsidian captures with AI-generated learning questions to help users actively engage with content

**Independent Test**: Open vault with 5 captured articles, run "Review Recent" command, verify notes displayed and learning questions generated

### Implementation for User Story 1

- [X] T016 [P] [US1] Create LearningQuestion and RelatedTopic interfaces in src/types.ts
- [X] T017 [P] [US1] Create ReviewSession interface in src/types.ts
- [X] T018 [US1] Implement question generation prompt and parser in src/analysis/questions.ts
- [X] T019 [US1] Implement related topics suggestion in src/analysis/questions.ts
- [X] T020 [US1] Implement getRecentCaptures() method in src/workflows/review.ts
- [X] T021 [US1] Implement filterByContentType() in src/workflows/review.ts
- [X] T022 [US1] Implement excludeReviewed() filter in src/workflows/review.ts
- [X] T023 [US1] Implement ReviewSession state management in src/workflows/review.ts
- [X] T024 [P] [US1] Create progress-bar.ts component in src/ui/components/
- [X] T025 [US1] Create ReviewModal with note display and questions in src/ui/review-modal.ts
- [X] T026 [US1] Add "Mark as Reviewed" button that updates frontmatter in src/ui/review-modal.ts
- [X] T027 [US1] Add "Next Note" / "Previous Note" navigation in src/ui/review-modal.ts
- [X] T028 [US1] Wire ReviewModal to "Review Recent Captures" command in src/main.ts
- [X] T029 [US1] Smoke test: Capture 5 articles, review workflow, verify questions generated

**Checkpoint**: User Story 1 fully functional - can review notes with AI questions ✅

**Phase Completion (Constitution Principle VIII)**:
- [X] Integration verified: Command opens modal, questions generated, frontmatter updated
- [X] End-to-end verification: Full review session with real vault notes
- [X] Constitution review: All 8 principles checked

---

## Phase 4: User Story 2 - Inbox Processing Workflow (Priority: P2)

**Goal**: Process notes in inbox folder with AI-suggested triage actions (Keep, Archive, Deep Read, Merge)

**Independent Test**: Place 5 notes in Inbox folder, run "Process Inbox", verify AI suggestions shown with action buttons

### Implementation for User Story 2

- [ ] T030 [P] [US2] Create InboxItem and TriageSuggestion interfaces in src/types.ts
- [ ] T031 [P] [US2] Create TriageAction enum (KEEP, ARCHIVE, DEEP_READ, MERGE) in src/types.ts
- [ ] T032 [US2] Implement triage prompt and suggestion parser in src/analysis/triage.ts (include decision criteria: KEEP=unique/actionable, ARCHIVE=redundant/low-value, DEEP_READ=valuable but needs focus, MERGE=overlaps >50% with existing note)
- [ ] T033 [US2] Implement getInboxItems() method in src/workflows/inbox.ts
- [ ] T034 [US2] Implement executeKeepAction() with folder move in src/workflows/inbox.ts (fallback: create folder named after content type if target doesn't exist)
- [ ] T035 [US2] Implement executeArchiveAction() in src/workflows/inbox.ts
- [ ] T036 [US2] Implement executeDeepReadAction() (mark in frontmatter) in src/workflows/inbox.ts
- [ ] T037 [US2] Implement executeMergeAction() with preview in src/workflows/inbox.ts
- [ ] T038 [US2] Create InboxModal with queue display in src/ui/inbox-modal.ts
- [ ] T039 [US2] Add AI suggestion display with reason in src/ui/inbox-modal.ts
- [ ] T040 [US2] Add action buttons (Keep, Archive, Deep Read, Merge) in src/ui/inbox-modal.ts
- [ ] T041 [US2] Add batch processing mode in src/ui/inbox-modal.ts (toggle + execution: auto-apply suggestions above batchAutoAcceptThreshold setting, queue low-confidence items for manual review, show summary before executing)
- [ ] T042 [US2] Wire InboxModal to "Process Inbox" command in src/main.ts
- [ ] T043 [US2] Add file watcher for inbox folder notifications in src/main.ts
- [ ] T044 [US2] Smoke test: 5 notes in inbox, verify suggestions and actions work
- [ ] T044b [US2] Log triage overrides to .claudsidian/triage_feedback.json for future learning (format: timestamp, note_path, ai_suggestion, user_action, confidence)

**Checkpoint**: User Story 2 fully functional - inbox triage workflow operational

**Phase Completion (Constitution Principle VIII)**:
- [ ] Integration verified: Command opens modal, suggestions generated, file moves work
- [ ] End-to-end verification: Full inbox triage session with file operations
- [ ] Constitution review: All 8 principles checked

---

## Phase 5: User Story 3 - Balanced Perspectives for News (Priority: P2)

**Goal**: Display source bias indicators and suggest counternarrative sources for news content

**Independent Test**: Review a news article from nytimes.com, verify bias badge shows "Lean Left" and counternarratives suggested

### Implementation for User Story 3

- [ ] T045 [P] [US3] Create SourceAnalysis and CounternarrativeSource interfaces in src/types.ts
- [ ] T046 [US3] Implement extractDomain() utility in src/analysis/bias.ts
- [ ] T047 [US3] Implement getSourceInfo() with SourceInfo API call in src/analysis/bias.ts
- [ ] T048 [US3] Implement getCounternarratives() in src/analysis/bias.ts
- [ ] T049 [US3] Implement source info caching (in-memory with TTL) in src/analysis/bias.ts
- [ ] T050 [P] [US3] Create source-badge.ts component (bias lean + credibility) in src/ui/components/
- [ ] T051 [US3] Add source bias section to ReviewModal for news content in src/ui/review-modal.ts
- [ ] T052 [US3] Add "Get Balanced View" button that fetches counternarratives in src/ui/review-modal.ts
- [ ] T053 [US3] Display counternarrative sources with credibility scores in src/ui/review-modal.ts
- [ ] T054 [US3] Handle "Source not rated" case gracefully in src/ui/review-modal.ts
- [ ] T055 [US3] Smoke test: Review news article from biased source, verify badge and counternarratives

**Checkpoint**: User Story 3 fully functional - bias analysis works in review workflow

**Phase Completion (Constitution Principle VIII)**:
- [ ] Integration verified: Bias badge shows for news, counternarratives fetched from SourceInfo
- [ ] End-to-end verification: Test with NYT (left) and WSJ (right) articles
- [ ] Constitution review: All 8 principles checked

---

## Phase 6: User Story 4 - Single Note Analysis (Priority: P3)

**Goal**: Allow on-demand analysis of any note via right-click or command palette

**Independent Test**: Right-click any Claudsidian note, select "Analyze for Learning", verify questions appended to note

### Implementation for User Story 4

- [ ] T056 [US4] Implement analyzeNote() combining questions + bias analysis in src/analysis/questions.ts
- [ ] T057 [US4] Implement appendAnalysisToNote() with markdown formatting in src/services/vault.ts
- [ ] T058 [US4] Add "## Learning Questions" section writer in src/services/vault.ts
- [ ] T059 [US4] Add "## Source Analysis" section writer for news in src/services/vault.ts
- [ ] T060 [US4] Implement existing analysis detection and overwrite prompt in src/services/vault.ts
- [ ] T061 [US4] Register file menu item "Analyze for Learning" in src/main.ts (use this.registerEvent(this.app.workspace.on('file-menu', ...)) pattern, only show for markdown files)
- [ ] T062 [US4] Wire command to analyzeNote() and appendAnalysisToNote() in src/main.ts
- [ ] T063 [US4] Add loading notice during analysis in src/main.ts
- [ ] T064 [US4] Smoke test: Analyze article note, verify questions appended; analyze news, verify source section

**Checkpoint**: User Story 4 fully functional - ad-hoc analysis works for any note

**Phase Completion (Constitution Principle VIII)**:
- [ ] Integration verified: Right-click and command palette both work
- [ ] End-to-end verification: Test with article, news, and already-analyzed notes
- [ ] Constitution review: All 8 principles checked

---

## Phase 7: User Story 5 - Model Quality Rating (Priority: P3)

**Goal**: Allow users to rate note quality (1-5 stars) and sync to Claudsidian ratings database

**Independent Test**: Review a note, give it 4 stars, verify rating in frontmatter and in .claudsidian/ratings.json

### Implementation for User Story 5

- [ ] T065 [P] [US5] Create rating-stars.ts component in src/ui/components/
- [ ] T066 [US5] Implement RatingsService for reading/writing ratings.json in src/services/ratings.ts
- [ ] T067 [US5] Implement extractModelMetadata() from note frontmatter in src/services/ratings.ts
- [ ] T068 [US5] Implement syncRatingToDatabase() in src/services/ratings.ts
- [ ] T069 [US5] Add star rating UI to ReviewModal in src/ui/review-modal.ts
- [ ] T070 [US5] Update frontmatter with user_rating on rate in src/ui/review-modal.ts
- [ ] T071 [US5] Call syncRatingToDatabase() after rating saved in src/ui/review-modal.ts
- [ ] T072 [US5] Add manual "Sync Ratings" command in src/main.ts
- [ ] T073 [US5] Smoke test: Rate 3 notes, verify frontmatter and ratings.json updated

**Checkpoint**: User Story 5 fully functional - ratings flow to Claudsidian database

**Phase Completion (Constitution Principle VIII)**:
- [ ] Integration verified: Rating UI works, frontmatter updated, JSON synced
- [ ] End-to-end verification: Rate multiple notes, check database file
- [ ] Constitution review: All 8 principles checked

---

## Phase 8: User Story 6 - Model Performance Dashboard (Priority: P4)

**Goal**: Display model rankings, OPUS scores, and quality metrics in a dedicated view

**Independent Test**: Open "Model Performance" view with 10+ rated notes, verify model rankings display

### Implementation for User Story 6

- [ ] T074 [P] [US6] Create ModelStats interface in src/types.ts
- [ ] T075 [US6] Implement readPerformanceData() from model_performance.json in src/services/ratings.ts
- [ ] T076 [US6] Implement calculateModelStats() aggregation in src/services/ratings.ts
- [ ] T077 [US6] Implement calculateOPUSScore() (quality/cost ratio) in src/services/ratings.ts
- [ ] T078 [US6] Create dashboard-view.ts as ItemView in src/ui/dashboard-view.ts
- [ ] T079 [US6] Implement model ranking table in dashboard in src/ui/dashboard-view.ts
- [ ] T080 [US6] Add content type breakdown per model in src/ui/dashboard-view.ts
- [ ] T081 [US6] Implement date range and model filters in src/ui/dashboard-view.ts
- [ ] T082 [US6] Implement HTML export to reports/performance/model-performance.html in src/ui/dashboard-view.ts (single file, overwrite on each export, create folder if missing)
- [ ] T083 [US6] Register "Model Performance" command and view in src/main.ts
- [ ] T084 [US6] Smoke test: Rate 10 notes, open dashboard, verify rankings displayed

**Checkpoint**: User Story 6 fully functional - analytics dashboard operational

**Phase Completion (Constitution Principle VIII)**:
- [ ] Integration verified: Dashboard view opens, data loads from JSON files
- [ ] End-to-end verification: Test with real performance data, export HTML
- [ ] Constitution review: All 8 principles checked

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T085 [P] Add error handling for SourceInfo API unavailable in src/analysis/bias.ts
- [ ] T086 [P] Add error handling for OpenRouter rate limits in src/services/ai.ts
- [ ] T087 [P] Add loading states to all modals in src/ui/
- [ ] T088 Implement exponential backoff for API retries in src/services/ai.ts
- [ ] T089 Add token usage tracking to AI calls in src/services/ai.ts
- [ ] T090 Handle long notes (>10K tokens) with chunking in src/services/ai.ts (per-chunk timeout: 90s, total timeout: 5 min, show "Still processing..." after 30s)
- [ ] T091 [P] Update styles.css with final polish
- [ ] T092 Run full workflow test: capture → review → rate → dashboard
- [ ] T093 Verify plugin works without SourceInfo running (degraded mode)
- [ ] T094 Verify plugin shows clear error when API key missing

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-8)**: All depend on Foundational phase completion
  - US1 (P1) can start immediately after Foundational
  - US2 (P2) and US3 (P2) can start after US1 or in parallel
  - US4 (P3) depends on US1 (reuses question generation)
  - US5 (P3) can start after US1 (rating UI in ReviewModal)
  - US6 (P4) depends on US5 (needs ratings data)
- **Polish (Phase 9)**: Depends on all user stories being complete

### User Story Dependencies

```
Foundational (Phase 2)
       │
       ▼
    US1 (P1) ─────────────────────────────────┐
       │                                       │
       ├──────────────────┬───────────────────┼────────┐
       ▼                  ▼                   ▼        │
    US2 (P2)           US3 (P2)            US4 (P3)   │
       │                  │                   │        │
       └──────────────────┴───────────────────┘        │
                                                       ▼
                                                    US5 (P3)
                                                       │
                                                       ▼
                                                    US6 (P4)
```

### Within Each User Story

- Models/interfaces before services
- Services before UI components
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

**Phase 2 (Foundational)**:
- T009 (AI client) and T010 (SourceInfo client) can run in parallel

**Phase 3 (US1)**:
- T016, T017 (interfaces) can run in parallel
- T024 (progress bar) can run in parallel with workflow implementation

**Phase 4 (US2)**:
- T030, T031 (interfaces) can run in parallel

**Phase 5 (US3)**:
- T045 (interfaces) and T050 (source badge) can run in parallel

**Phase 7 (US5)**:
- T065 (rating stars) can run in parallel with ratings service

---

## Parallel Example: User Story 1

```bash
# Step 1: Interfaces (parallel)
Task: "T016 [P] [US1] Create LearningQuestion and RelatedTopic interfaces"
Task: "T017 [P] [US1] Create ReviewSession interface"

# Step 2: Analysis (sequential)
Task: "T018 [US1] Implement question generation prompt and parser"
Task: "T019 [US1] Implement related topics suggestion"

# Step 3: Workflow (sequential)
Task: "T020-T023 [US1] Implement review workflow methods"

# Step 4: UI (can parallelize component)
Task: "T024 [P] [US1] Create progress-bar.ts component"
Task: "T025-T028 [US1] Create ReviewModal and wire to command"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (Review Recent Captures)
4. **STOP and VALIDATE**: Test review workflow independently
5. Deploy/demo if ready - this is your MVP!

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → **MVP: Core review workflow**
3. Add User Story 2 → Inbox processing
4. Add User Story 3 → Source bias (enhances US1)
5. Add User Story 4 → Ad-hoc analysis
6. Add User Story 5 → Rating system
7. Add User Story 6 → Analytics dashboard
8. Each story adds value without breaking previous stories

### Suggested MVP Scope

**MVP = Phase 1 + Phase 2 + Phase 3 (User Story 1)**

This delivers:
- Plugin that loads in Obsidian ✓
- Settings for API keys and folders ✓
- Review Recent Captures workflow with AI questions ✓
- Mark notes as reviewed ✓

Total MVP tasks: 29 (T001-T029)

---

## Summary

| Phase | User Story | Priority | Task Count |
|-------|------------|----------|------------|
| 1 | Setup | - | 5 |
| 2 | Foundational | - | 10 |
| 3 | US1: Review Recent | P1 | 14 |
| 4 | US2: Inbox Processing | P2 | 16 |
| 5 | US3: Balanced Perspectives | P2 | 11 |
| 6 | US4: Single Note Analysis | P3 | 9 |
| 7 | US5: Model Quality Rating | P3 | 9 |
| 8 | US6: Performance Dashboard | P4 | 11 |
| 9 | Polish | - | 10 |
| **Total** | | | **95** |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently testable after completion
- Smoke tests included per constitution (Principle VI - no TDD overhead)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently

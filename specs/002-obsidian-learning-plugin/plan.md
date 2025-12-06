# Implementation Plan: Obsidian Learning Plugin

**Branch**: `002-obsidian-learning-plugin` | **Date**: 2025-12-05 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-obsidian-learning-plugin/spec.md`

## Summary

An Obsidian plugin that transforms passive content capture into active learning. The plugin integrates with Claudsidian-captured notes to provide AI-generated learning questions, balanced news perspectives via SourceInfo API, and model performance tracking. Built with TypeScript using the standard Obsidian plugin architecture, it reads/modifies vault files and makes HTTP calls to OpenRouter for AI analysis and SourceInfo for source bias data.

## Technical Context

**Language/Version**: TypeScript 5.x, Node.js 16+
**Primary Dependencies**: obsidian (API), gray-matter (YAML parsing), esbuild (bundling)
**Storage**: Obsidian vault files (markdown + JSON in `.claudsidian/`)
**Testing**: Jest + jest-environment-obsidian (smoke tests per constitution)
**Target Platform**: Obsidian Desktop (Windows, macOS, Linux)
**Project Type**: Single Obsidian plugin
**Performance Goals**: Learning questions within 10 seconds, dashboard render <3 seconds
**Constraints**: No cloud dependencies beyond AI APIs, must use Obsidian's requestUrl() for CORS bypass
**Scale/Scope**: Single vault, up to 1000 rated notes, ~220 SourceInfo sources

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design. Re-check at end of EVERY implementation phase.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Frictionless Capture | N/A | Plugin consumes captures, doesn't create them |
| II. Automation First | PASS | AI handles question generation, bias analysis, triage suggestions |
| III. Simplicity Over Elegance | PASS | Using standard Obsidian plugin patterns, no complex abstractions |
| IV. Proactive AI Collaboration | PASS | This plan documents decisions before implementation |
| V. Local-First | PASS | All data in vault, only external calls are to AI/SourceInfo APIs |
| VI. Pragmatic Development | PASS | Smoke tests planned, no TDD overhead |
| VII. Content-Type Aware | PASS | Different handling for news (bias analysis) vs. general articles |
| VIII. Phase Integration & Verification | PASS | Each phase includes integration + verification tasks |

**Phase Completion Reminder**: At the end of each phase, review the Phase Completion Checklist in `.specify/memory/constitution.md` to ensure integration, verification, and constitution compliance before proceeding.

## Project Structure

### Documentation (this feature)

```text
specs/002-obsidian-learning-plugin/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── openrouter.yaml  # OpenRouter API contract
│   └── sourceinfo.yaml  # SourceInfo API contract
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (new plugin repository)

```text
obsidian-learning-plugin/
├── src/
│   ├── main.ts                    # Plugin entry point
│   ├── settings.ts                # Settings tab and configuration
│   ├── types.ts                   # TypeScript interfaces
│   ├── services/
│   │   ├── ai.ts                  # OpenRouter API client
│   │   ├── sourceinfo.ts          # SourceInfo API client
│   │   ├── vault.ts               # Vault operations (read/write notes)
│   │   └── ratings.ts             # Claudsidian ratings sync
│   ├── workflows/
│   │   ├── review.ts              # Review Recent workflow logic
│   │   └── inbox.ts               # Inbox Processing workflow logic
│   ├── analysis/
│   │   ├── questions.ts           # Learning question generation
│   │   ├── bias.ts                # Source bias analysis
│   │   └── triage.ts              # Inbox triage suggestions
│   └── ui/
│       ├── review-modal.ts        # Review workflow modal
│       ├── inbox-modal.ts         # Inbox processing modal
│       ├── dashboard-view.ts      # Model performance dashboard
│       └── components/
│           ├── rating-stars.ts    # Star rating component
│           ├── source-badge.ts    # Source bias indicator
│           └── progress-bar.ts    # Review progress indicator
├── tests/
│   └── smoke.test.ts              # Basic smoke tests
├── manifest.json                  # Plugin manifest
├── package.json
├── tsconfig.json
├── esbuild.config.mjs
├── styles.css
└── versions.json
```

**Structure Decision**: Single Obsidian plugin following the official sample-plugin template structure. The plugin is a standalone project that integrates with Claudsidian via file-based data exchange (vault files, `.claudsidian/` JSON files).

## Complexity Tracking

No constitution violations requiring justification. The architecture follows standard Obsidian plugin patterns without introducing unnecessary complexity.

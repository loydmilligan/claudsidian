<!--
================================================================================
SYNC IMPACT REPORT
================================================================================
Version change: 1.0.0 → 1.1.0 (MINOR - expanded guidance on testing and integration)

Modified principles:
- Principle VI "Pragmatic Development" → clarified testing approach
- Governance "Compliance" → expanded with Phase Completion Checklist

Added sections:
- Principle VIII "Phase Integration & Verification"
- Phase Completion Checklist in Governance

Removed sections: None

Templates requiring updates:
- .specify/templates/plan-template.md: ✅ updated (added Phase Completion gate reference)
- .specify/templates/spec-template.md: ✅ compatible (no changes needed)
- .specify/templates/tasks-template.md: ✅ updated (added Phase Completion checklist to each phase)

Follow-up TODOs: None
================================================================================
-->

# Claudsidian Constitution

## Core Principles

### I. Frictionless Capture

Content capture MUST require minimal steps regardless of input source. The system MUST support multiple capture methods:
- CLI commands for terminal users
- Browser extension for web content
- Inbox file watching for drag-and-drop workflows
- Android widget/share target for mobile capture

Every capture path MUST result in properly formatted markdown in the Obsidian vault within seconds, not minutes. If a capture method requires more than 3 user actions, it MUST be simplified.

### II. Automation First

AI handles the cognitive load of organization. The system MUST:
- Auto-generate tags based on content analysis
- Auto-assign folder locations based on content type
- Auto-create backlinks to related notes
- Auto-generate summaries for quick scanning

Users SHOULD NOT need to manually organize captured content. Claude API handles complex organization tasks (summarization, tagging, linking). OpenRouter API handles simpler tasks to optimize costs.

### III. Simplicity Over Elegance

Architecture decisions MUST favor simplicity over cleverness:
- External tool writing markdown files directly to vault (no plugin required for core functionality)
- Flat or shallow folder hierarchies preferred over deep nesting
- Single-purpose modules over multi-responsibility abstractions
- Direct file operations over complex sync mechanisms

UI MUST serve function over aesthetics. If a feature works from CLI, a fancy GUI is optional.

When facing architectural choices, ask: "What is the simplest thing that could possibly work?" and implement that first.

### IV. Proactive AI Collaboration

During development, Claude MUST engage in proactive discussion before implementing significant decisions:
- Present options with tradeoffs before choosing an approach
- Explain reasoning for architectural decisions
- Surface potential issues early rather than discovering them during implementation
- Ask clarifying questions when requirements are ambiguous

This is NOT about asking permission for every action - it's about treating development as a collaborative design conversation.

### V. Local-First

This tool operates entirely on local machines and local network. The system:
- MUST NOT require cloud services beyond AI APIs (OpenRouter, Claude)
- MUST NOT phone home or collect telemetry
- MUST NOT require user accounts or authentication
- MUST store all data in user-controlled locations (the Obsidian vault)

Security hardening is NOT a priority - the threat model assumes trusted local environment.

### VI. Pragmatic Development

Development practices MUST prioritize shipping over ceremony:
- **Testing**: Basic end-to-end verification after each phase is REQUIRED. Avoid TDD and extensive unit test suites - these add overhead without proportional value. The goal is smoke tests that verify the feature works, not comprehensive test coverage.
- **Documentation**: Optional unless it solves a real problem
- **Refactoring**: Happens when code becomes painful, not preemptively
- Perfect is the enemy of working

No timeline pressure - features ship when they're ready, not when deadlines demand.

**Testing Clarification**: "Optional testing" means no TDD, no mandated coverage percentages, no test-before-code requirements. It does NOT mean no testing at all. Each phase MUST include at minimum a manual or automated smoke test proving the feature works end-to-end.

### VII. Content-Type Aware

The system MUST provide specialized handling for different content types:

| Content Type | Processing | Output |
|--------------|-----------|--------|
| Articles | Full summary, key points, source link | Learning note with spaced repetition hooks |
| YouTube | Transcript extraction, summary, timestamps | Video note with chapter markers |
| GitHub Repos | README extraction, tech stack, purpose | Project tracking note |
| News | Summary, key facts, source credibility | News digest entry |
| Walkthroughs | Step extraction, prerequisites, gotchas | How-to guide with code blocks |
| 3D Models | Source link, file type, print settings | Printables tracking note |

Each content type MAY have its own template and processing pipeline.

### VIII. Phase Integration & Verification

**Every phase MUST be fully integrated before being marked complete.**

This principle exists because building isolated components without integration creates invisible gaps that compound into system-wide failures. A feature that "works" in isolation but isn't wired into the main flow provides zero user value.

Requirements for phase completion:
1. **Integration**: All components built in the phase MUST be connected to the main application flow
2. **Verification**: A working end-to-end test (manual or automated) MUST demonstrate the feature functions
3. **Constitution Review**: The phase MUST be checked against all constitution principles before sign-off

**Anti-pattern to avoid**: Building an extractor module, marking the task "done", but never wiring it into `capture.py`. The extractor exists but users can't use it.

**Required pattern**: Every extractor phase includes:
- The extractor implementation tasks
- An integration task wiring it into the capture flow
- A verification task testing the complete path

## Content Types

The system organizes knowledge into these primary categories:

- **Learning Notes**: Articles and educational content for building understanding
- **Video Notes**: YouTube and video content with timestamps and summaries
- **Project Tracking**: GitHub repos and tools to track interesting projects
- **News Digest**: Tech, political, and business news that matters
- **Walkthroughs**: How-to guides extracted from instructional content
- **Printables**: 3D model files for printing projects

Each category supports the core goal: reducing friction between discovering something interesting and having it organized in Obsidian.

## Development Workflow

### AI API Strategy

- **Claude API**: Complex tasks requiring deep reasoning - content summarization, tag generation, relationship mapping, multi-step organization
- **OpenRouter API**: Simpler tasks - basic text extraction, formatting, template filling

Cost optimization: Route to OpenRouter by default, escalate to Claude when quality requires it.

### Capture Architecture

```
[Input Sources]                    [Processing]              [Output]

Browser Extension  ──┐
CLI Command        ──┼──▶  Local Service  ──▶  AI Processing  ──▶  Vault/
Inbox File Watch   ──┤         (or CLI)          (OpenRouter       markdown
Android Widget     ──┘                            + Claude)        files
```

The system operates outside Obsidian, writing directly to the vault folder. Obsidian's strength is reading any markdown - we leverage that rather than building inside the plugin system.

### Decision Protocol

When facing implementation choices:
1. State the options clearly
2. List tradeoffs for each
3. Recommend an approach with reasoning
4. Wait for confirmation on significant decisions
5. Proceed autonomously on minor details

## Governance

This constitution defines the non-negotiable principles for Claudsidian development. All implementation decisions MUST be evaluated against these principles.

### Amendment Process

1. Propose amendment with rationale
2. Evaluate impact on existing architecture
3. Update constitution with new version number
4. Propagate changes to affected templates

### Version Policy

- **MAJOR**: Principle additions, removals, or fundamental redefinitions
- **MINOR**: Expanded guidance, new sections, clarifications that change behavior
- **PATCH**: Typo fixes, wording improvements, non-behavioral changes

### Compliance

Before implementing any feature, verify:
- [ ] Capture requires ≤3 user actions (Principle I)
- [ ] AI handles organization, not user (Principle II)
- [ ] Simplest viable architecture chosen (Principle III)
- [ ] Significant decisions discussed first (Principle IV)
- [ ] No cloud dependencies beyond AI APIs (Principle V)
- [ ] Basic smoke test planned, no over-testing (Principle VI)
- [ ] Content type has appropriate handling (Principle VII)
- [ ] Integration and verification tasks included (Principle VIII)

### Phase Completion Checklist

**MEMORY: Review this checklist at the end of EVERY phase before marking it complete.**

At the end of each implementation phase:

1. **Integration Check**
   - [ ] All new components are wired into the main application flow
   - [ ] No "orphan" modules exist that users can't access
   - [ ] Entry points (CLI commands, API endpoints) actually call the new code

2. **Verification Check**
   - [ ] End-to-end test demonstrates the feature works
   - [ ] Test uses realistic inputs (real URLs, real data)
   - [ ] Test verifies output is correct (note created, content accurate)

3. **Constitution Check**
   - [ ] Re-read all 8 principles
   - [ ] Verify phase doesn't violate any principle
   - [ ] Document any principle exceptions with justification

4. **Sign-off**
   - [ ] All above checks pass
   - [ ] Phase can be marked complete

**Failure to complete this checklist before moving to the next phase is a constitution violation.**

**Version**: 1.1.0 | **Ratified**: 2025-12-01 | **Last Amended**: 2025-12-02

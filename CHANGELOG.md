# Changelog

All notable changes to Claudsidian are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

#### Model Comparison System
- **`compare run`** - A/B test AI models with side-by-side comparisons
- **`compare models`** - List available model presets
- **`compare cleanup`** - Remove test notes and run directories
- HTML report generation with expandable quality analysis
- Gold standard comparison for objective quality scoring
- Timestamped run directories for comparison history
- `--include-printable` flag for 3D model testing (requires Playwright)
- `--require-gold` flag to only test fixtures with gold standards

#### Performance Tracking
- **Automatic performance tracking** on every capture
- Cost, time, and token usage logged to performance database
- **OPUS metric** - quality-adjusted cost efficiency ranking
- Quality scores from compare runs saved to database
- `{vault}/.claudsidian/model_performance.json` database file

#### Ratings & Analytics Commands
- **`ratings performance`** - View model performance summary
- **`ratings recent`** - View recent captures with costs/times
- **`ratings process`** - Collect user ratings from note frontmatter
- **`ratings report`** - Generate quality report
- **`ratings stats`** - Show rating statistics
- **`ratings list`** - List all collected ratings

#### 3D Model Extraction (Playwright)
- **Playwright browser automation** for Thingiverse and Printables
- **Vision AI integration** for screenshot analysis
- Non-headless mode to bypass Cloudflare bot protection
- Screenshot capture and embedding in notes
- Configurable vision model via `vision_model` config option

#### New CLI Commands
- **`test-capture`** - Test capture functionality with fixtures
- Test fixtures file support (`test-captures.md` in vault)

#### Configuration
- **`vision_model`** config option for image analysis model
- Support for custom OpenRouter model IDs
- Model preset system with friendly names

### Changed

#### Default Models (Breaking Change)
- **Summary model**: Changed from `claude-sonnet-4` to `openrouter-grok-fast` (`x-ai/grok-4.1-fast`)
- **Tags model**: Unchanged (`openrouter-haiku` / `anthropic/claude-3-haiku`)
- **Vision model**: Changed from `claude` to `google/gemini-2.0-flash-exp:free`
- **Comparison model**: Set to `google/gemini-2.0-flash-exp:free`

All models now default to OpenRouter - no direct Claude API calls unless explicitly configured.

#### OpenRouter Client
- Added image/vision message support for multimodal models
- Added `enable_reasoning` parameter to control reasoning mode
- Added fallback for models that return content in `message.reasoning`
- Fixed reasoning mode causing empty responses from Gemini models

#### Note Frontmatter
- Added `user_rating` field (null by default) for user feedback
- Added `rating_processed` field to track rating collection
- Added `time_seconds` to AI usage metrics

### Fixed

- **Gemini empty summaries** - Handle models returning content in reasoning field
- **Media Extended timestamps** - Convert `[MM:SS]` to clickable video links
- **HTML report expand buttons** - Fixed JavaScript f-string escaping
- **Quality score extraction** - Handle `[Model A]: X/5` format from AI analysis
- **Playwright timeout** - Increased to 60s, changed wait strategy for slow sites
- **Config attribute error** - Fixed `anthropic_api_key` vs `claude_api_key`

### Technical

#### New Files
- `src/cli/commands/compare.py` - Model comparison system
- `src/cli/commands/ratings.py` - Ratings and analytics CLI
- `src/cli/commands/test_capture.py` - Test capture functionality
- `src/core/ai/vision.py` - Vision AI integration
- `src/core/extractors/printable_playwright.py` - Browser-based extraction
- `src/models/model_performance.py` - Performance tracking database
- `src/models/ratings.py` - User ratings database

#### Dependencies
- Added `playwright` as optional dependency for 3D model capture

---

## [0.1.0] - 2025-12-01

### Added
- Initial release
- CLI capture command
- HTTP server for browser extension
- Inbox file watching
- Content type detection (article, video, repo, news, walkthrough, printable)
- AI-powered summarization and tagging
- Backlink discovery
- Queue management with retry
- Browser extension support
- Android share target support

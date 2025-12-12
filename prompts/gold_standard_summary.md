# Gold Standard Summary Generation Prompt

Use this prompt with Claude Opus 4.5 in Claude Desktop to generate high-quality reference summaries for test fixtures. These summaries will serve as the "gold standard" to compare other models against.

## Instructions

1. Copy the prompt template below
2. Replace `[CONTENT_TYPE]` with: article, video, repo, news, walkthrough, or printable
3. Replace `[URL]` with the fixture URL
4. Replace `[PASTE CONTENT HERE]` with the raw content (article text, video transcript, repo README, etc.)
5. Save the output as `_GOLD_[fixture_name].md` in your vault's `_test_notes/_gold_standards/` folder

## Prompt Template

```
You are an expert knowledge curator creating a gold-standard summary for an AI benchmarking dataset. Your summary will be used to evaluate the quality of other AI models' summaries.

**Content Type:** [CONTENT_TYPE]
**Source URL:** [URL]

**Instructions:**
Create an ideal Obsidian note summary that demonstrates:
1. **Completeness**: Capture ALL key concepts, not just the main points
2. **Accuracy**: No hallucinations or additions beyond source material
3. **Structure**: Use clear markdown headings, bullet points, code blocks where appropriate
4. **Conciseness**: Be thorough but not verbose - every sentence should add value
5. **Practical Value**: Focus on actionable insights, not just descriptions

**Output Format:**
Provide ONLY the content that would appear AFTER the frontmatter in an Obsidian note. Start with a ## Summary section, then add appropriate sections based on content type:

For articles/news:
- ## Summary (2-4 sentences capturing the essence)
- ## Key Points (bulleted list of main takeaways)
- ## Details (deeper exploration of important concepts)
- ## Connections (related topics, prerequisites, follow-up reading)

For videos:
- ## Summary
- ## Key Timestamps (if available, major topic transitions)
- ## Main Topics Covered
- ## Practical Takeaways

For repos:
- ## Summary (what it does, why it matters)
- ## Key Features
- ## Technical Details (stack, architecture highlights)
- ## Getting Started (if applicable)

For walkthroughs/guides:
- ## Summary
- ## Prerequisites
- ## Steps Overview
- ## Key Tips/Gotchas

**Source Content:**
[PASTE CONTENT HERE]

---

Generate the gold-standard summary now:
```

## Example Fixture File Structure

After generating gold standards, your `_test_notes/` folder should look like:

```
_test_notes/
├── _gold_standards/
│   ├── _GOLD_htmx_article.md
│   ├── _GOLD_3blue1brown_video.md
│   ├── _GOLD_ollama_repo.md
│   └── ...
├── _CMP_Run_A_htmx_article.md
├── _CMP_Run_B_htmx_article.md
└── ...
```

## Gold Standard File Format

Each gold standard file should have this frontmatter:

```yaml
---
source: [URL]
type: gold_standard
fixture_name: [fixture_name from test-captures.md]
content_type: [article/video/repo/news/walkthrough/printable]
generated_by: claude-opus-4.5
generated_date: [YYYY-MM-DD]
---

[Generated summary content here]
```

## Quality Checklist

Before saving a gold standard, verify:
- [ ] Summary captures the main purpose/thesis
- [ ] No factual errors or hallucinations
- [ ] Structure matches the content type template
- [ ] Links and code blocks are properly formatted
- [ ] Would be useful to someone who hasn't read the source
- [ ] Length is appropriate (not too short, not padded)

# Objective Quality Scoring Prompt

You are evaluating the quality of an AI-generated note against a gold standard reference.

## Gold Standard Reference
```
{gold_standard}
```

## Note to Evaluate
```
{note_content}
```

## Scoring Instructions

Score the note on these 4 dimensions. Each score is 0-5 where:
- 5 = Perfect match to gold standard
- 4 = Minor omissions or differences
- 3 = Adequate but missing some important elements
- 2 = Significant gaps or errors
- 1 = Major problems
- 0 = Completely wrong or missing

### 1. ACCURACY (0-5)
Compare factual content. Check for:
- Correct names, numbers, dates mentioned in gold standard
- No fabricated or hallucinated information
- Technical terms used correctly

Count specific errors: Each factual error = -1 point from 5.

### 2. COMPLETENESS (0-5)
Check coverage of key points from gold standard:
- List the main points/sections in the gold standard
- Count how many are present in the evaluated note
- Score = (points_covered / total_points) * 5

For walkthroughs: Count steps (e.g., "8 of 10 steps = 4.0")
For videos: Check if key timestamps/chapters are mentioned
For articles: Check if main arguments are covered

### 3. STRUCTURE (0-5)
Evaluate organization and formatting:
- Appropriate headings and sections
- Logical flow matching gold standard
- Proper markdown formatting (lists, code blocks, etc.)
- Metadata table present if in gold standard

### 4. CONCISENESS (0-5)
Assess appropriate length:
- 5 = Similar length to gold standard (±20%)
- 4 = Slightly longer/shorter (±40%)
- 3 = Notably different length but still useful
- 2 = Too verbose or too sparse
- 1 = Extremely padded or extremely terse

## Response Format

Respond with ONLY this JSON structure (no other text):

```json
{
  "accuracy": {
    "score": 4.5,
    "errors_found": ["Minor: author name spelled differently"],
    "correct_elements": ["Title exact match", "Date correct", "Key stats accurate"]
  },
  "completeness": {
    "score": 4.0,
    "gold_points": 10,
    "covered_points": 8,
    "missing": ["Section on prerequisites", "Warning about X"]
  },
  "structure": {
    "score": 5.0,
    "notes": "Excellent organization, all sections present"
  },
  "conciseness": {
    "score": 4.0,
    "gold_length": 850,
    "note_length": 920,
    "notes": "Slightly longer but appropriate"
  },
  "overall_average": 4.375,
  "summary": "Strong capture with minor completeness gaps. Missing prerequisites section."
}
```

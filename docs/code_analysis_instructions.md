# Code Analysis Instructions

## Your Task
You are reviewing Python files in the Claudsidian codebase to create a comprehensive manifest of what's built.

## For Each File, Provide:

1. **file_path**: The full path to the file
2. **purpose**: 2-3 sentence description of what this file does
3. **status**: One of:
   - `complete` - Fully implemented and working
   - `partial` - Some features implemented, others TODO/incomplete
   - `stub` - Minimal implementation, mostly placeholder
4. **classes**: List of classes with brief descriptions
5. **functions**: List of top-level functions with brief descriptions
6. **imports_from**: List of other project files this file imports from
7. **imported_by**: List of files that likely import this (if known)
8. **key_features**: List of notable features/capabilities
9. **todos_or_incomplete**: Any TODO comments, incomplete features, or dead code found
10. **external_dependencies**: External packages used (httpx, click, etc.)

## Output Format (JSON)
```json
{
  "file_path": "src/path/to/file.py",
  "purpose": "Description of what this file does",
  "status": "complete|partial|stub",
  "classes": [
    {"name": "ClassName", "description": "What it does", "methods": ["method1", "method2"]}
  ],
  "functions": [
    {"name": "function_name", "description": "What it does"}
  ],
  "imports_from": ["src/models/note.py", "src/core/ai/router.py"],
  "imported_by": ["src/cli/commands/capture.py"],
  "key_features": ["Feature 1", "Feature 2"],
  "todos_or_incomplete": ["TODO: implement X", "Unused function Y"],
  "external_dependencies": ["httpx", "click", "pydantic"]
}
```

## Special Focus Areas
Pay attention to:
- **Quality/Ratings systems**: Any code related to user ratings, quality scores, model evaluation
- **Model comparison**: A/B testing, gold standards, comparison reports
- **Performance tracking**: Cost tracking, token counting, timing
- **Partially built features**: Code that exists but isn't fully wired up

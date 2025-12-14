"""Backlink discovery and tag utilities for vault operations."""

from dataclasses import dataclass
from pathlib import Path
from collections import Counter
import re

import yaml


def get_existing_tags(vault_path: str | Path, limit: int = 100) -> list[str]:
    """Get the most commonly used tags from the vault.

    Scans all markdown files in the vault and returns the most frequently
    used tags, sorted by frequency (most common first).

    Args:
        vault_path: Path to the Obsidian vault root directory
        limit: Maximum number of tags to return (default: 100)

    Returns:
        List of tag strings, sorted by frequency (most common first)

    Example:
        >>> tags = get_existing_tags("/path/to/vault", limit=50)
        >>> print(tags[:5])
        ['python', 'ai', 'tutorial', 'web-development', 'javascript']
    """
    vault_path = Path(vault_path)
    tag_counter: Counter = Counter()

    # Find all markdown files
    for md_file in vault_path.glob("**/*.md"):
        try:
            content = md_file.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue

        # Parse frontmatter
        if not content.startswith('---'):
            continue

        pattern = r'^---\s*\n(.*?)\n---\s*\n'
        match = re.match(pattern, content, re.DOTALL)
        if not match:
            continue

        try:
            frontmatter = yaml.safe_load(match.group(1))
            if not isinstance(frontmatter, dict):
                continue

            tags = frontmatter.get('tags', [])
            if isinstance(tags, list):
                for tag in tags:
                    if isinstance(tag, str) and tag.strip():
                        # Normalize to lowercase
                        tag_counter[tag.lower().strip()] += 1
        except yaml.YAMLError:
            continue

    # Return most common tags
    return [tag for tag, _ in tag_counter.most_common(limit)]


@dataclass
class RelatedNote:
    """A note related by shared tags.

    Attributes:
        path: Relative path to the note in the vault
        title: Title of the note
        shared_tags: List of tags that are shared with the query
        match_score: Number of shared tags (higher = more related)
    """

    path: str
    title: str
    shared_tags: list[str]
    match_score: int


class BacklinkFinder:
    """Finds related notes in the vault based on shared tags.

    This class searches through all markdown files in an Obsidian vault,
    parses their YAML frontmatter, and identifies notes that share tags
    with a given list. Results are ranked by the number of shared tags.

    Attributes:
        _vault_path: Path object pointing to the vault root directory
    """

    def __init__(self, vault_path: str | Path) -> None:
        """Initialize the BacklinkFinder with a vault path.

        Args:
            vault_path: Path to the Obsidian vault root directory
        """
        self._vault_path = Path(vault_path)

    def find_related(
        self,
        tags: list[str],
        exclude_path: str | None = None,
        min_shared: int = 2
    ) -> list[RelatedNote]:
        """Find notes that share tags with the given list.

        Searches all markdown files in the vault, parses their frontmatter,
        and returns notes that share at least min_shared tags with the
        provided tag list. Results are sorted by match score (descending)
        and limited to the top 10 results.

        Args:
            tags: List of tags to search for
            exclude_path: Optional path to exclude from results (e.g., current note)
            min_shared: Minimum number of shared tags required (default: 2)

        Returns:
            List of RelatedNote objects, sorted by match_score descending,
            limited to top 10 results

        Example:
            >>> finder = BacklinkFinder("/path/to/vault")
            >>> related = finder.find_related(["python", "ai", "tools"], min_shared=2)
            >>> for note in related:
            ...     print(f"{note.title}: {note.match_score} shared tags")
        """
        if not tags:
            return []

        # Normalize tags for case-insensitive comparison
        normalized_query_tags = {tag.lower() for tag in tags}
        related_notes: list[RelatedNote] = []

        # Find all markdown files in the vault
        markdown_files = self._vault_path.glob("**/*.md")

        for md_file in markdown_files:
            # Get relative path for comparison and storage
            try:
                relative_path = str(md_file.relative_to(self._vault_path))
            except ValueError:
                # File is not within vault_path, skip it
                continue

            # Skip excluded path if specified
            if exclude_path and relative_path == exclude_path:
                continue

            # Read and parse the file
            try:
                content = md_file.read_text(encoding='utf-8')
            except (OSError, UnicodeDecodeError):
                # Skip files that can't be read
                continue

            # Parse frontmatter
            frontmatter = self._parse_frontmatter(content)
            if not frontmatter:
                continue

            # Extract tags from frontmatter
            note_tags = frontmatter.get('tags', [])
            if not note_tags or not isinstance(note_tags, list):
                continue

            # Normalize note tags for comparison
            normalized_note_tags = {tag.lower() for tag in note_tags if isinstance(tag, str)}

            # Find shared tags
            shared = normalized_query_tags & normalized_note_tags

            # Check if meets minimum threshold
            if len(shared) >= min_shared:
                # Extract title from frontmatter or use filename
                title = frontmatter.get('title', md_file.stem)

                related_notes.append(RelatedNote(
                    path=relative_path,
                    title=title,
                    shared_tags=sorted(list(shared)),
                    match_score=len(shared)
                ))

        # Sort by match score (descending) and limit to top 10
        related_notes.sort(key=lambda x: x.match_score, reverse=True)
        return related_notes[:10]

    def _parse_frontmatter(self, content: str) -> dict:
        """Extract YAML frontmatter from markdown content.

        Parses the YAML frontmatter block enclosed in --- delimiters
        at the beginning of a markdown file.

        Args:
            content: Complete markdown file content

        Returns:
            Dictionary containing parsed YAML frontmatter, or empty dict
            if no valid frontmatter is found

        Example:
            >>> finder = BacklinkFinder("/path/to/vault")
            >>> content = '''---
            ... title: My Note
            ... tags:
            ...   - python
            ...   - ai
            ... ---
            ...
            ... Content here.
            ... '''
            >>> fm = finder._parse_frontmatter(content)
            >>> print(fm['title'])
            My Note
            >>> print(fm['tags'])
            ['python', 'ai']
        """
        # Check if content starts with frontmatter delimiter
        if not content.startswith('---'):
            return {}

        # Use regex to extract frontmatter block
        # Match from start --- to next --- on its own line
        pattern = r'^---\s*\n(.*?)\n---\s*\n'
        match = re.match(pattern, content, re.DOTALL)

        if not match:
            return {}

        yaml_content = match.group(1)

        try:
            frontmatter = yaml.safe_load(yaml_content)
            # Ensure we return a dict
            if not isinstance(frontmatter, dict):
                return {}
            return frontmatter
        except yaml.YAMLError:
            return {}

    def format_backlinks(self, related: list[RelatedNote]) -> str:
        """Format related notes as markdown backlinks.

        Generates a markdown list of wiki-style links to related notes,
        including information about shared tags for context.

        Args:
            related: List of RelatedNote objects to format

        Returns:
            Formatted markdown string with backlinks, or empty string if no notes

        Example:
            >>> finder = BacklinkFinder("/path/to/vault")
            >>> related = [
            ...     RelatedNote(
            ...         path="notes/example.md",
            ...         title="Example Note",
            ...         shared_tags=["python", "ai"],
            ...         match_score=2
            ...     )
            ... ]
            >>> print(finder.format_backlinks(related))
            ## Related Notes
            <BLANKLINE>
            - [[Example Note]] (2 shared tags: python, ai)
        """
        if not related:
            return ""

        lines = ["## Related Notes", ""]

        for note in related:
            # Format shared tags as comma-separated list
            tags_str = ", ".join(note.shared_tags)

            # Create wiki-link with shared tags info
            link_line = f"- [[{note.title}]] ({note.match_score} shared tags: {tags_str})"
            lines.append(link_line)

        return "\n".join(lines)

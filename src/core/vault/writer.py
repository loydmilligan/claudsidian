"""Vault writer - handles writing notes to Obsidian vault."""

import re
from pathlib import Path

from src.models.note import Note
from src.models.config import Configuration


class VaultWriter:
    """Writes notes to the Obsidian vault.

    This class handles the creation of note files in the Obsidian vault,
    including filename sanitization, directory creation, and file writing.

    Attributes:
        _config: Configuration object containing vault settings
        _vault_path: Path object for the vault root directory
    """

    def __init__(self, config: Configuration) -> None:
        """Initialize the VaultWriter with configuration.

        Args:
            config: Configuration object containing vault_path and folder settings
        """
        self._config = config
        self._vault_path = Path(config.vault_path)

    def _sanitize_filename(self, title: str) -> str:
        r"""Remove invalid filename characters with enhanced sanitization.

        Performs comprehensive filename sanitization:
        - Removes/replaces invalid filename characters: / \ : * ? " < > |
        - Truncates long titles (max 200 characters with smart word boundary)
        - Collapses multiple spaces/underscores into single space
        - Strips leading/trailing whitespace and dots
        - Replaces reserved Windows names (CON, PRN, AUX, NUL, COM1-9, LPT1-9)
        - Handles empty/whitespace-only titles with fallback to "Untitled"

        Args:
            title: The title to sanitize for use as a filename

        Returns:
            Sanitized filename without invalid characters

        Example:
            >>> writer = VaultWriter(config)
            >>> writer._sanitize_filename("My Note: A Test")
            'My Note A Test'
            >>> writer._sanitize_filename("File/With\\Invalid:Chars")
            'FileWithInvalidChars'
            >>> writer._sanitize_filename("CON")
            'CON_'
            >>> writer._sanitize_filename("")
            'Untitled'
        """
        # Handle empty or whitespace-only titles
        if not title or not title.strip():
            return "Untitled"

        # Remove invalid filename characters
        sanitized = re.sub(r'[/\\:*?"<>|]', '', title)

        # Collapse multiple spaces and underscores into single space
        sanitized = re.sub(r'[\s_]+', ' ', sanitized)

        # Strip leading/trailing whitespace and dots
        sanitized = sanitized.strip().strip('.')

        # Handle case where all characters were invalid
        if not sanitized:
            return "Untitled"

        # Check for reserved Windows names
        reserved_names = {
            'CON', 'PRN', 'AUX', 'NUL',
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        }

        # Check if the sanitized name (without extension) is a reserved name
        name_upper = sanitized.upper()
        if name_upper in reserved_names:
            sanitized = sanitized + '_'

        # Truncate long titles (max 200 characters) with smart word boundary
        max_length = 200
        if len(sanitized) > max_length:
            # Try to truncate at word boundary
            truncated = sanitized[:max_length]
            last_space = truncated.rfind(' ')

            # If we found a space in the last 20% of the string, use it
            if last_space > max_length * 0.8:
                sanitized = truncated[:last_space]
            else:
                # Otherwise just truncate at max_length
                sanitized = truncated

            # Strip any trailing whitespace or dots after truncation
            sanitized = sanitized.strip().strip('.')

        return sanitized

    def _get_unique_path(self, path: Path) -> Path:
        """Find the next available unique path if the file already exists.

        Appends a counter suffix like (2), (3), etc. before the file extension
        to find an available filename.

        Args:
            path: The original path that may already exist

        Returns:
            Path object that doesn't exist (either original or with counter suffix)

        Example:
            >>> writer = VaultWriter(config)
            >>> path = Path("/vault/Note.md")
            >>> # If Note.md exists, returns Path("/vault/Note (2).md")
            >>> # If Note (2).md also exists, returns Path("/vault/Note (3).md")
            >>> unique = writer._get_unique_path(path)
        """
        if not path.exists():
            return path

        # Split the path into stem and suffix
        stem = path.stem
        suffix = path.suffix
        parent = path.parent

        counter = 2
        while True:
            new_name = f"{stem} ({counter}){suffix}"
            new_path = parent / new_name
            if not new_path.exists():
                return new_path
            counter += 1

    def get_note_path(self, title: str, subfolder: str | None = None) -> Path:
        """Get the full path for a note.

        Constructs the full file path for a note based on its title and optional
        subfolder. The title is sanitized to create a valid filename.

        Args:
            title: The note title to use for the filename
            subfolder: Optional subfolder path relative to vault root

        Returns:
            Complete Path object for the note file with .md extension

        Example:
            >>> writer = VaultWriter(config)
            >>> writer.get_note_path("My Note", "Articles")
            Path('/path/to/vault/Articles/My Note.md')
            >>> writer.get_note_path("My Note")
            Path('/path/to/vault/My Note.md')
        """
        filename = self._sanitize_filename(title) + ".md"

        if subfolder:
            return self._vault_path / subfolder / filename
        else:
            return self._vault_path / filename

    def note_exists(self, title: str, subfolder: str | None = None) -> bool:
        """Check if a note already exists.

        Determines if a note file with the given title already exists in the
        vault at the specified location.

        Args:
            title: The note title to check
            subfolder: Optional subfolder path relative to vault root

        Returns:
            True if the note file exists, False otherwise

        Example:
            >>> writer = VaultWriter(config)
            >>> writer.note_exists("Existing Note", "Articles")
            True
            >>> writer.note_exists("New Note")
            False
        """
        note_path = self.get_note_path(title, subfolder)
        return note_path.exists()

    def write_note(
        self, note: Note, subfolder: str | None = None, overwrite: bool = False
    ) -> Path:
        """Write a note to the vault.

        Writes the note to the vault, creating any necessary subdirectories.
        The note is converted to markdown format using its to_markdown() method
        before writing. If a note with the same name exists, either overwrites
        it or creates a new file with a counter suffix based on the overwrite flag.

        Args:
            note: The Note object to write to the vault
            subfolder: Optional subfolder path relative to vault root
            overwrite: If True, overwrites existing file. If False (default),
                      creates a new file with counter suffix like (2), (3), etc.

        Returns:
            Path object pointing to where the note was written

        Raises:
            OSError: If there are issues creating directories or writing the file

        Example:
            >>> writer = VaultWriter(config)
            >>> note = Note(title="My Note", content="Content...", ...)
            >>> # First write creates Note.md
            >>> path = writer.write_note(note, "Articles")
            >>> print(path)
            Path('/path/to/vault/Articles/My Note.md')
            >>> # Second write creates Note (2).md (no overwrite)
            >>> path2 = writer.write_note(note, "Articles")
            >>> print(path2)
            Path('/path/to/vault/Articles/My Note (2).md')
            >>> # With overwrite=True, replaces existing file
            >>> path3 = writer.write_note(note, "Articles", overwrite=True)
            >>> print(path3)
            Path('/path/to/vault/Articles/My Note.md')
        """
        # Get the full path for the note
        note_path = self.get_note_path(note.title, subfolder)

        # Handle duplicate filenames if overwrite is False
        if not overwrite:
            note_path = self._get_unique_path(note_path)

        # Create parent directory if it doesn't exist
        note_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert note to markdown and write to file
        markdown_content = note.to_markdown()
        note_path.write_text(markdown_content, encoding='utf-8')

        return note_path

"""Obsidian vault operations - writing notes, managing backlinks."""

from src.core.vault.backlinks import BacklinkFinder, RelatedNote
from src.core.vault.writer import VaultWriter

__all__ = ["BacklinkFinder", "RelatedNote", "VaultWriter"]

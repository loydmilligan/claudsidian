"""Research subjects API routes.

This module provides endpoints for listing and creating research subjects
for use by the browser extension.
"""

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.models.config import load_config, config_exists

logger = logging.getLogger(__name__)
router = APIRouter(tags=["subjects"])


class SubjectInfo(BaseModel):
    """Research subject information."""
    name: str
    folder_path: str
    status: str
    note_count: int
    has_wizard_complete: bool  # Whether the wizard has been run


class SubjectsResponse(BaseModel):
    """Response for listing subjects."""
    subjects: list[SubjectInfo]
    vault_path: str


class CreateSubjectRequest(BaseModel):
    """Request to create a new subject."""
    name: str


class CreateSubjectResponse(BaseModel):
    """Response after creating a subject."""
    success: bool
    name: str
    folder_path: str
    message: str


def parse_subject_file(subject_file: Path) -> dict:
    """Parse a _subject.md file to extract status and wizard completion.

    Args:
        subject_file: Path to the _subject.md file

    Returns:
        Dict with status and has_wizard_complete
    """
    status = "active"
    has_wizard_complete = False

    try:
        content = subject_file.read_text(encoding='utf-8')

        # Check frontmatter for status
        if content.startswith('---'):
            end_idx = content.find('---', 3)
            if end_idx > 0:
                frontmatter = content[3:end_idx]
                for line in frontmatter.split('\n'):
                    if line.startswith('status:'):
                        status = line.split(':', 1)[1].strip()
                        break

        # Check if wizard has been completed
        # Wizard completion markers: has ## Research Plan or ## Done When with actual content
        has_research_plan = '## Research Plan' in content and content.split('## Research Plan')[1].strip()[:50] != ''
        has_done_when = '## Done When' in content

        # Check if Done When has actual checkboxes (not just placeholder)
        if has_done_when:
            done_section = content.split('## Done When')[1].split('##')[0] if '## Done When' in content else ''
            has_done_items = '- [ ]' in done_section or '- [x]' in done_section
            has_wizard_complete = has_done_items or has_research_plan

    except Exception as e:
        logger.warning(f"Failed to parse subject file {subject_file}: {e}")

    return {
        "status": status,
        "has_wizard_complete": has_wizard_complete
    }


@router.get("/subjects", response_model=SubjectsResponse)
async def list_subjects() -> SubjectsResponse:
    """List all research subjects in the vault.

    Returns:
        SubjectsResponse: List of subjects with their info
    """
    if not config_exists():
        raise HTTPException(status_code=500, detail="Configuration not found")

    config = load_config()
    if not config:
        raise HTTPException(status_code=500, detail="Failed to load configuration")

    vault_path = Path(config.vault_path)
    subject_matter_path = vault_path / "SubjectMatter"

    subjects: list[SubjectInfo] = []

    if subject_matter_path.exists() and subject_matter_path.is_dir():
        for folder in subject_matter_path.iterdir():
            if folder.is_dir():
                subject_file = folder / "_subject.md"
                if subject_file.exists():
                    # Parse the subject file
                    parsed = parse_subject_file(subject_file)

                    # Count notes in folder (excluding _subject.md)
                    note_count = len([
                        f for f in folder.glob("*.md")
                        if f.name != "_subject.md"
                    ])

                    subjects.append(SubjectInfo(
                        name=folder.name,
                        folder_path=str(folder.relative_to(vault_path)),
                        status=parsed["status"],
                        note_count=note_count,
                        has_wizard_complete=parsed["has_wizard_complete"]
                    ))

    # Sort by name
    subjects.sort(key=lambda s: s.name.lower())

    return SubjectsResponse(
        subjects=subjects,
        vault_path=config.vault_path
    )


@router.post("/subjects", response_model=CreateSubjectResponse)
async def create_subject(request: CreateSubjectRequest) -> CreateSubjectResponse:
    """Create a new research subject folder with minimal _subject.md.

    This creates just the folder and a basic _subject.md file.
    The full wizard will be run when the user opens the Research tab in Obsidian.

    Args:
        request: CreateSubjectRequest with subject name

    Returns:
        CreateSubjectResponse: Success status and folder path
    """
    if not config_exists():
        raise HTTPException(status_code=500, detail="Configuration not found")

    config = load_config()
    if not config:
        raise HTTPException(status_code=500, detail="Failed to load configuration")

    vault_path = Path(config.vault_path)

    # Sanitize name for folder
    safe_name = request.name.strip()
    # Replace spaces with hyphens, remove unsafe characters
    folder_name = "".join(c if c.isalnum() or c in ' -_' else '' for c in safe_name)
    folder_name = folder_name.replace(' ', '-')

    if not folder_name:
        raise HTTPException(status_code=400, detail="Invalid subject name")

    # Create folder path
    subject_folder = vault_path / "SubjectMatter" / folder_name

    # Check if already exists
    if subject_folder.exists():
        return CreateSubjectResponse(
            success=False,
            name=folder_name,
            folder_path=str(subject_folder.relative_to(vault_path)),
            message=f"Subject '{folder_name}' already exists"
        )

    try:
        # Create folder
        subject_folder.mkdir(parents=True, exist_ok=True)

        # Create minimal _subject.md (wizard not complete)
        from datetime import datetime
        subject_file = subject_folder / "_subject.md"
        content = f"""---
created: {datetime.now().isoformat()}
status: active
wizard_pending: true
---

# {safe_name}

## Goals
_(Wizard not yet completed - open Research tab in Obsidian to set up this subject)_

## Discovered Goals
_(Goals discovered during research will appear here)_

## Notes
"""
        subject_file.write_text(content, encoding='utf-8')

        return CreateSubjectResponse(
            success=True,
            name=folder_name,
            folder_path=str(subject_folder.relative_to(vault_path)),
            message=f"Created subject '{folder_name}' - open Research tab to complete setup"
        )

    except Exception as e:
        logger.error(f"Failed to create subject: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create subject: {str(e)}")

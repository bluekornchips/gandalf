"""
Project utils for consistent project name handling and sanitization.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

from src.utils.security import SecurityValidator


@dataclass
class ProjectContext:
    """
    Project context with sanitized names and metadata.
    This is used to store the project context for the current session.
    """

    root: Path
    raw_name: str
    sanitized_name: str
    was_sanitized: bool

    @classmethod
    def from_path(cls, project_root: Path) -> "ProjectContext":
        """Create project context from a path."""
        raw_name = project_root.name
        sanitized_name = SecurityValidator.sanitize_project_name(raw_name)
        was_sanitized = raw_name != sanitized_name

        return cls(
            root=project_root,
            raw_name=raw_name,
            sanitized_name=sanitized_name,
            was_sanitized=was_sanitized,
        )

    def get_transparency_fields(self) -> dict:
        """
        Get transparency fields for project info responses.
        Transparency is for if we replace the project name with a sanitized one.
        """
        fields = {"sanitized": self.was_sanitized}

        if self.was_sanitized:
            fields["raw_project_name"] = self.raw_name

        return fields


def get_project_names(project_root: Path) -> Tuple[str, str, bool]:
    """Get raw and sanitized project names, with sanitization flag."""
    raw_name = project_root.name
    sanitized_name = SecurityValidator.sanitize_project_name(raw_name)
    was_sanitized = raw_name != sanitized_name

    return raw_name, sanitized_name, was_sanitized


def get_sanitized_project_name(project_root: Path) -> str:
    """Get just the sanitized project name."""
    return SecurityValidator.sanitize_project_name(project_root.name)

"""
Project utilities for the Gandalf MCP server.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.utils.access_control import AccessValidator


def _extract_project_names(project_root: Path) -> tuple[str, str, bool]:
    """Extract raw and sanitized project names from a Path."""
    if not isinstance(project_root, Path):
        raise TypeError(f"Expected Path object, got {type(project_root)}")

    try:
        raw_name = project_root.name
        sanitized_name = AccessValidator.sanitize_project_name(raw_name)
        was_sanitized = raw_name != sanitized_name

        return raw_name, sanitized_name, was_sanitized
    except (OSError, AttributeError) as e:
        raise ValueError(f"Failed to extract project names from {project_root}: {e}")


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
        try:
            raw_name, sanitized_name, was_sanitized = _extract_project_names(
                project_root
            )

            return cls(
                root=project_root,
                raw_name=raw_name,
                sanitized_name=sanitized_name,
                was_sanitized=was_sanitized,
            )
        except TypeError:
            # Re-raise TypeError for type validation errors
            raise
        except ValueError as e:
            raise ValueError(
                f"Failed to create ProjectContext from {project_root}: {e}"
            )

    def get_transparency_fields(self) -> dict[str, Any]:
        """Get transparency fields for project info responses."""
        fields: dict[str, Any] = {"sanitized": self.was_sanitized}

        if self.was_sanitized:
            fields["raw_project_name"] = self.raw_name

        return fields


def get_project_names(project_root: Path) -> tuple[str, str, bool]:
    """Get raw and sanitized project names, with sanitization flag."""
    try:
        return _extract_project_names(project_root)
    except TypeError:
        # Re-raise TypeError for type validation errors
        raise
    except ValueError as e:
        raise ValueError(f"Failed to get project names for {project_root}: {e}")


def get_sanitized_project_name(project_root: Path) -> str:
    """Get just the sanitized project name."""
    try:
        _, sanitized_name, _ = _extract_project_names(project_root)
        return sanitized_name
    except TypeError:
        # Re-raise TypeError for type validation errors
        raise
    except ValueError as e:
        raise ValueError(
            f"Failed to get sanitized project name for {project_root}: {e}"
        )

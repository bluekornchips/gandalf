"""
Base adapter interface for IDE-ish-specific implementations.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional


class IDEAdapter(ABC):
    """Abstract base class for IDE-specific adapters."""

    def __init__(self, project_root: Optional[Path] = None):
        """Initialize the adapter with optional project root."""
        self.project_root = project_root
        self._detected_ide = None

    @property
    @abstractmethod
    def ide_name(self) -> str:
        """Return the name of the IDE this adapter supports."""

    @abstractmethod
    def detect_ide(self) -> bool:
        """Detect if this IDE is currently running or configured."""

    @abstractmethod
    def detect_conversation_databases(self) -> bool:
        """Detect if this IDE has accessible conversation databases."""

    @abstractmethod
    def get_workspace_folders(self) -> List[Path]:
        """Get workspace folder paths for the IDE."""

    @abstractmethod
    def resolve_project_root(
        self, explicit_root: Optional[str] = None
    ) -> Path:
        """Resolve the project root directory."""

    @abstractmethod
    def get_conversation_tools(self) -> Dict[str, Any]:
        """Get IDE-specific conversation tool definitions."""

    @abstractmethod
    def get_conversation_handlers(self) -> Dict[str, Any]:
        """Get IDE-specific conversation tool handlers."""

    @abstractmethod
    def get_configuration_paths(self) -> Dict[str, Path]:
        """Get IDE-specific configuration file paths."""

    def supports_conversations(self) -> bool:
        """Return whether this adapter supports conversation tools."""
        return len(self.get_conversation_tools()) > 0

    def get_environment_info(self) -> Dict[str, Any]:
        """Get environment information for debugging."""
        return {
            "ide_name": self.ide_name,
            "detected": self.detect_ide(),
            "project_root": (
                str(self.project_root) if self.project_root else None
            ),
            "workspace_folders": [
                str(p) for p in self.get_workspace_folders()
            ],
            "supports_conversations": self.supports_conversations(),
        }

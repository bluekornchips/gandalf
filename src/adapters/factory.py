"""
Factory for creating IDE adapters based on environment detection.
"""

import os
from typing import Optional, List

from src.config.constants.system import SUPPORTED_IDES
from src.utils.common import log_debug, log_info

from .base import IDEAdapter
from .claude_code import ClaudeCodeAdapter
from .cursor import CursorAdapter


class AdapterFactory:
    """Factory class for creating appropriate IDE adapters."""

    @staticmethod
    def create_adapter(
        explicit_ide: Optional[str] = None, project_root: Optional[str] = None
    ) -> IDEAdapter:
        """Create an appropriate IDE adapter based on environment detection.

        Args:
            explicit_ide: Force a specific IDE adapter ("cursor" or "claude-code")
            project_root: Optional project root path to pass to adapter

        Returns:
            IDEAdapter: The appropriate adapter for the detected or specified IDE

        Raises:
            ValueError: If explicit_ide is specified but not supported
        """
        # If explicitly specified, use that adapter
        if explicit_ide:
            if explicit_ide.lower() in ["cursor", "cursor-ide"]:
                log_info("Using explicit Cursor adapter")
                return CursorAdapter(project_root)
            elif explicit_ide.lower() in [
                "claude-code",
                "claude_code",
                "claudecode",
            ]:
                log_info("Using explicit Claude Code adapter")
                return ClaudeCodeAdapter(project_root)
            else:
                raise ValueError(f"Unsupported IDE: {explicit_ide}")

        # Auto detect based on environment
        return AdapterFactory._detect_ide(project_root)

    @staticmethod
    def _detect_ide(project_root: Optional[str] = None) -> IDEAdapter:
        """Detect which IDE is currently active and return appropriate adapter."""

        # Check for Claude Code first with more specific environment variables
        claude_adapter = ClaudeCodeAdapter(project_root)
        if claude_adapter.detect_ide():
            log_info("Detected Claude Code environment")
            return claude_adapter

        # Check for Cursor
        cursor_adapter = CursorAdapter(project_root)
        if cursor_adapter.detect_ide():
            log_info("Detected Cursor environment")
            return cursor_adapter

        # Default fallback logic
        fallback_ide = AdapterFactory._get_fallback_ide()
        log_info(f"No IDE detected, using fallback: {fallback_ide}")

        if fallback_ide == "claude-code":
            return ClaudeCodeAdapter(project_root)
        else:
            return CursorAdapter(project_root)

    @staticmethod
    def _get_fallback_ide() -> str:
        """Determine fallback IDE when no clear detection is possible."""

        # Environment variable override
        fallback_env = os.environ.get("GANDALF_FALLBACK_IDE", "").lower()
        if fallback_env in SUPPORTED_IDES:
            log_debug(f"Using fallback IDE from environment: {fallback_env}")
            return fallback_env

        log_debug("No IDE detected; using default")
        return "cursor"

    @staticmethod
    def get_supported_ides() -> List[str]:
        """Get list of supported IDE types."""
        return SUPPORTED_IDES.copy()

    @staticmethod
    def detect_current_ide() -> Optional[str]:
        """Detect the current IDE without creating an adapter."""
        claude_adapter = ClaudeCodeAdapter()
        if claude_adapter.detect_ide():
            return "claude-code"

        cursor_adapter = CursorAdapter()
        if cursor_adapter.detect_ide():
            return "cursor"

        return None

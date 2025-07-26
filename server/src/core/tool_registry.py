"""
Simplified tool registry for agentic tools.

This module provides simple function-based tool registration without
unnecessary abstractions or complex patterns.
"""

from pathlib import Path

from src.core.database_scanner import DatabaseScanner, ToolType
from src.utils.common import log_error


def get_available_tools(project_root: Path) -> list[str]:
    """Get list of available agentic tools for project."""
    try:
        scanner = DatabaseScanner(project_root)
        available_tools = []

        for tool_type in ToolType:
            try:
                if scanner._find_database_path(tool_type):
                    available_tools.append(tool_type.value)
            except Exception as e:
                log_error(e, f"checking database path for {tool_type.value}")
                continue

        return available_tools
    except Exception as e:
        log_error(e, "getting available tools")
        return []


def get_registered_agentic_tools() -> list[str]:
    """Get list of registered agentic tool names."""
    return get_available_tools(Path.cwd())

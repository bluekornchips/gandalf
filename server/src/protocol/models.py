"""
Custom type definitions for Gandalf.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ToolResult:
    """Result from tool execution."""

    type: str = "text"
    text: str = ""
    data: Optional[Dict[str, Any]] = None


@dataclass
class ToolDefinition:
    """Tool definition for registration."""

    name: str
    description: str
    input_schema: Dict[str, Any]


@dataclass
class ServerCapabilities:
    """Server capabilities definition."""

    tools: Dict[str, bool]
    logging: Dict[str, Any]

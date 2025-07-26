"""
Database scanner for detecting conversation databases across different agentic tools.

This module provides a unified scanner that consolidates all tool-specific logic
into a single, maintainable class without unnecessary abstractions.
"""

import json
import signal
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from src.config.core_constants import (
    DATABASE_SCANNER_TIMEOUT,
)
from src.config.tool_config import (
    CLAUDE_CODE_DATABASE_PATHS,
    CURSOR_DATABASE_PATHS,
    WINDSURF_DATABASE_PATHS,
)
from src.utils.common import log_error, log_info


@contextmanager
def timeout_context(seconds: int) -> Any:
    """Context manager to timeout operations that might hang."""

    def timeout_handler(_signum: int, _frame: Any) -> None:
        raise TimeoutError(f"Operation timed out after {seconds} seconds")

    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


class ToolType(Enum):
    """Supported agentic tool types."""

    CURSOR = "cursor"
    CLAUDE_CODE = "claude-code"
    WINDSURF = "windsurf"


@dataclass(frozen=True)
class ScanResult:
    """Result of database scanning operation."""

    tool_type: ToolType
    conversations: list[dict[str, Any]]
    database_path: Path
    scan_time: float
    error: str | None = None


class DatabaseScanner:
    """Unified database scanner for all agentic tools."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self._cache: dict[str, ScanResult] = {}
        self._cache_time: float = 0.0

    def scan_tool_databases(
        self, tool_types: list[ToolType] | None = None, max_conversations: int = 1000
    ) -> list[ScanResult]:
        """Scan databases for specified tool types."""
        if tool_types is None:
            tool_types = list(ToolType)

        results = []
        for tool_type in tool_types:
            result = self._scan_tool_database(tool_type, max_conversations)
            if result:
                results.append(result)

        return results

    def _scan_tool_database(
        self, tool_type: ToolType, max_conversations: int
    ) -> ScanResult | None:
        """Scan database for specific tool type."""
        start_time = time.time()

        try:
            db_path = self._find_database_path(tool_type)
            if not db_path or not db_path.exists():
                return None

            conversations = self._extract_conversations(
                tool_type, db_path, max_conversations
            )
            scan_time = time.time() - start_time

            return ScanResult(
                tool_type=tool_type,
                conversations=conversations,
                database_path=db_path,
                scan_time=scan_time,
            )

        except Exception as e:
            return ScanResult(
                tool_type=tool_type,
                conversations=[],
                database_path=Path(),
                scan_time=time.time() - start_time,
                error=str(e),
            )

    def _find_database_path(self, tool_type: ToolType) -> Path | None:
        """Find database path for tool type."""
        path_configs = {
            ToolType.CURSOR: CURSOR_DATABASE_PATHS,
            ToolType.CLAUDE_CODE: CLAUDE_CODE_DATABASE_PATHS,
            ToolType.WINDSURF: WINDSURF_DATABASE_PATHS,
        }

        for path_pattern in path_configs[tool_type]:
            resolved_path = Path(path_pattern.format(home=Path.home()))
            if resolved_path.exists():
                return resolved_path

        return None

    def _extract_conversations(
        self, tool_type: ToolType, db_path: Path, max_conversations: int
    ) -> list[dict[str, Any]]:
        """Extract conversations from database with tool-specific logic."""
        if tool_type == ToolType.CURSOR:
            return self._extract_cursor_conversations(db_path, max_conversations)
        elif tool_type == ToolType.CLAUDE_CODE:
            return self._extract_claude_code_conversations(db_path, max_conversations)
        elif tool_type == ToolType.WINDSURF:
            return self._extract_windsurf_conversations(db_path, max_conversations)

        # All enum values are handled above
        raise ValueError(f"Unhandled tool type: {tool_type}")

    def _extract_cursor_conversations(
        self, db_path: Path, max_conversations: int
    ) -> list[dict[str, Any]]:
        """Extract conversations from Cursor database."""
        conversations = []

        try:
            with timeout_context(DATABASE_SCANNER_TIMEOUT):
                conn = sqlite3.connect(str(db_path))
                conn.row_factory = sqlite3.Row

                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, title, timestamp, data
                    FROM conversations
                    ORDER BY timestamp DESC
                    LIMIT ?
                """,
                    (max_conversations,),
                )

                for row in cursor.fetchall():
                    conversations.append(
                        {
                            "id": row["id"],
                            "title": row["title"] or "Untitled Conversation",
                            "timestamp": row["timestamp"],
                            "content": row["data"] or "",
                            "tool": "cursor",
                        }
                    )

                conn.close()

        except Exception as e:
            log_error(e, f"extracting Cursor conversations from {db_path}")

        return conversations

    def _extract_claude_code_conversations(
        self, db_path: Path, max_conversations: int
    ) -> list[dict[str, Any]]:
        """Extract conversations from Claude Code database."""
        conversations = []

        try:
            with timeout_context(DATABASE_SCANNER_TIMEOUT):
                if db_path.suffix == ".jsonl":
                    with open(db_path, encoding="utf-8") as f:
                        for i, line in enumerate(f):
                            if i >= max_conversations:
                                break
                            try:
                                data = json.loads(line.strip())
                                conversations.append(
                                    {
                                        "id": data.get("id", f"conv_{i}"),
                                        "title": data.get(
                                            "title", "Claude Code Session"
                                        ),
                                        "timestamp": data.get("timestamp"),
                                        "content": json.dumps(data.get("messages", [])),
                                        "tool": "claude-code",
                                    }
                                )
                            except json.JSONDecodeError:
                                continue
                elif db_path.suffix == ".json":
                    with open(db_path, encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            for i, conv in enumerate(data[:max_conversations]):
                                conversations.append(
                                    {
                                        "id": conv.get("id", f"conv_{i}"),
                                        "title": conv.get(
                                            "title", "Claude Code Session"
                                        ),
                                        "timestamp": conv.get("timestamp"),
                                        "content": json.dumps(conv.get("messages", [])),
                                        "tool": "claude-code",
                                    }
                                )

        except Exception as e:
            log_error(e, f"extracting Claude Code conversations from {db_path}")

        return conversations

    def _extract_windsurf_conversations(
        self, db_path: Path, max_conversations: int
    ) -> list[dict[str, Any]]:
        """Extract conversations from Windsurf database."""
        conversations = []

        try:
            with timeout_context(DATABASE_SCANNER_TIMEOUT):
                conn = sqlite3.connect(str(db_path))
                conn.row_factory = sqlite3.Row

                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, title, timestamp, content
                    FROM windsurf_conversations
                    ORDER BY timestamp DESC
                    LIMIT ?
                """,
                    (max_conversations,),
                )

                for row in cursor.fetchall():
                    conversations.append(
                        {
                            "id": row["id"],
                            "title": row["title"] or "Windsurf Session",
                            "timestamp": row["timestamp"],
                            "content": row["content"] or "",
                            "tool": "windsurf",
                        }
                    )

                conn.close()

        except Exception as e:
            log_error(e, f"extracting Windsurf conversations from {db_path}")

        return conversations


def get_available_agentic_tools(silent: bool = False) -> list[str]:
    """Get list of agentic tools that have conversation databases available."""
    try:
        with timeout_context(45):
            scanner = DatabaseScanner(Path.cwd())
            available_tools = []

            for tool_type in ToolType:
                db_path = scanner._find_database_path(tool_type)
                if db_path and db_path.exists():
                    # Quick check for database accessibility
                    if db_path.stat().st_size > 1024:  # > 1KB
                        available_tools.append(tool_type.value)
                        if not silent:
                            log_info(f"Found accessible database for {tool_type.value}")

            return available_tools

    except TimeoutError as e:
        if not silent:
            log_error(e, "detecting available agentic tools timed out after 45 seconds")
        return []
    except Exception as e:
        if not silent:
            log_error(e, "detecting available agentic tools")
        return []


def quick_scan_available_tools() -> dict[str, Any]:
    """Quick scan to get available tools without full database analysis."""
    scanner = DatabaseScanner(Path.cwd())
    available_tools = []
    tool_info = {}

    for tool_type in ToolType:
        db_path = scanner._find_database_path(tool_type)
        if db_path and db_path.exists():
            stat = db_path.stat()
            tool_info[tool_type.value] = {
                "database_path": str(db_path),
                "size_bytes": stat.st_size,
                "last_modified": stat.st_mtime,
            }
            if stat.st_size > 1024:
                available_tools.append(tool_type.value)

    return {
        "available_tools": available_tools,
        "tool_info": tool_info,
        "scan_timestamp": time.time(),
    }

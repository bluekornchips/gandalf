"""
Database scanner for detecting conversation databases across different agentic tools.

This module scans the filesystem for conversation databases from supported
agentic tools like Cursor, Claude Code, and other supported agentic tools
without requiring them to be running.
"""

import signal
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from config.constants import (
    CLAUDE_CONVERSATION_PATTERNS,
    CLAUDE_SCANNER_PATHS,
    CURSOR_DB_PATTERNS,
    CURSOR_SCANNER_PATHS,
    WINDSURF_DB_PATTERNS,
    WINDSURF_SCANNER_PATHS,
    DATABASE_OPERATION_TIMEOUT,
    DATABASE_SCANNER_CACHE_TTL,
    DATABASE_SCANNER_TIMEOUT,
    SUPPORTED_AGENTIC_TOOLS,
    AGENTIC_TOOL_CURSOR,
    AGENTIC_TOOL_CLAUDE_CODE,
    AGENTIC_TOOL_WINDSURF,
)
from utils.common import log_debug, log_error, log_info


@contextmanager
def timeout_context(seconds: int):
    """Context manager to timeout operations that might hang."""

    def timeout_handler(_signum, _frame):
        raise TimeoutError(f"Operation timed out after {seconds} seconds")

    # Set the signal handler and a alarm
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)

    try:
        yield
    finally:
        # Restore the old signal handler and cancel the alarm
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


@dataclass
class ConversationDatabase:
    """Represents a conversation database found during scanning."""

    path: str
    tool_type: str
    size_bytes: int
    last_modified: float
    conversation_count: Optional[int] = None
    is_accessible: bool = True
    error_message: Optional[str] = None


class DatabaseScanner:
    """Scanner for detecting conversation databases across agentic tools."""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self.databases: List[ConversationDatabase] = []
        self._scan_cache: Dict[str, List[ConversationDatabase]] = {}
        self._last_scan_time: float = 0.0
        self._cache_ttl: float = DATABASE_SCANNER_CACHE_TTL
        self._scan_timeout: int = DATABASE_SCANNER_TIMEOUT

    def _should_rescan(self) -> bool:
        """Determine if a rescan is needed based on cache age."""
        return time.time() - self._last_scan_time > self._cache_ttl

    def _count_conversations_sqlite(self, db_path: Path) -> Optional[int]:
        """Count conversations in a SQLite database safely."""
        try:
            with timeout_context(DATABASE_OPERATION_TIMEOUT):
                with sqlite3.connect(str(db_path), timeout=2.0) as conn:
                    cursor = conn.cursor()

                    # Try common table names for conversation counting
                    table_names = ["conversations", "messages", "chat_sessions"]
                    for table_name in table_names:
                        try:
                            cursor.execute(
                                f"SELECT COUNT(*) FROM {table_name}"  # nosec B608
                            )
                            count = cursor.fetchone()[0]
                            log_debug(
                                f"Found {count} conversations in {db_path} "
                                f"(table: {table_name})"
                            )
                            return count
                        except sqlite3.OperationalError:
                            continue

                    log_debug(f"No recognizable conversation table found in {db_path}")
                    return 0

        except (
            TimeoutError,
            sqlite3.Error,
            OSError,
            ValueError,
            AttributeError,
        ) as e:
            log_error(e, f"counting conversations in {db_path}")
            return None

    def _scan_cursor_databases(self) -> List[ConversationDatabase]:
        """Scan for Cursor conversation databases with timeout protection."""
        databases = []

        try:
            with timeout_context(self._scan_timeout):
                # Common Cursor paths - directly to workspaceStorage
                cursor_paths = CURSOR_SCANNER_PATHS

                for workspace_storage in cursor_paths:
                    if not workspace_storage.exists():
                        continue

                    log_debug(f"Scanning Cursor workspace storage: {workspace_storage}")

                    try:
                        # Use a set to track found files and avoid duplicates
                        found_files = set()

                        # Search only 2 levels deep to avoid infinite recursion
                        for item in workspace_storage.iterdir():
                            if item.is_dir():
                                for sub_item in item.iterdir():
                                    if sub_item.is_file() and any(
                                        sub_item.name.endswith(p.lstrip("*"))
                                        for p in CURSOR_DB_PATTERNS
                                    ):
                                        found_files.add(sub_item)
                                    elif sub_item.is_dir():
                                        # Go one more level deep
                                        try:
                                            for deep_item in sub_item.iterdir():
                                                if deep_item.is_file() and any(
                                                    deep_item.name.endswith(
                                                        p.lstrip("*")
                                                    )
                                                    for p in CURSOR_DB_PATTERNS
                                                ):
                                                    found_files.add(deep_item)
                                        except (PermissionError, OSError):
                                            continue
                            elif item.is_file() and any(
                                item.name.endswith(p.lstrip("*"))
                                for p in CURSOR_DB_PATTERNS
                            ):
                                found_files.add(item)

                        for db_file in found_files:
                            try:
                                stat = db_file.stat()
                                conversation_count = self._count_conversations_sqlite(
                                    db_file
                                )

                                database = ConversationDatabase(
                                    path=str(db_file),
                                    tool_type="cursor",
                                    size_bytes=stat.st_size,
                                    last_modified=stat.st_mtime,
                                    conversation_count=conversation_count,
                                    is_accessible=conversation_count is not None,
                                )

                                if conversation_count is None:
                                    database.error_message = "Could not access database"

                                databases.append(database)
                                log_debug(f"Found Cursor database: {db_file}")

                            except (OSError, ValueError, AttributeError) as e:
                                log_error(e, f"processing Cursor database {db_file}")
                                databases.append(
                                    ConversationDatabase(
                                        path=str(db_file),
                                        tool_type="cursor",
                                        size_bytes=0,
                                        last_modified=0.0,
                                        is_accessible=False,
                                        error_message=str(e),
                                    )
                                )
                    except (PermissionError, OSError) as e:
                        log_debug(
                            f"Cannot access workspace storage {workspace_storage}: {e}"
                        )
                        continue

        except TimeoutError:
            log_error(
                None,
                f"Cursor database scan timed out after {self._scan_timeout} seconds",
            )
        except (OSError, ValueError, AttributeError) as e:
            log_error(e, "scanning Cursor databases")

        return databases

    def _scan_claude_databases(self) -> List[ConversationDatabase]:
        """Scan for Claude Code conversation files with timeout protection."""
        databases = []

        try:
            with timeout_context(self._scan_timeout):
                # Common Claude Code paths
                claude_paths = CLAUDE_SCANNER_PATHS

                for base_path in claude_paths:
                    if not base_path.exists():
                        continue

                    log_debug(f"Scanning Claude Code path: {base_path}")

                    try:
                        # Use a set to track found files and avoid duplicates
                        found_files = set()

                        for pattern in CLAUDE_CONVERSATION_PATTERNS:
                            try:
                                if "/" in pattern:
                                    # Handle patterns like "conversations/*.json"
                                    dir_part, file_part = pattern.split("/", 1)
                                    target_dir = base_path / dir_part
                                    if target_dir.exists() and target_dir.is_dir():
                                        for item in target_dir.iterdir():
                                            if item.is_file() and item.name.endswith(
                                                file_part.lstrip("*")
                                            ):
                                                found_files.add(item)
                                else:
                                    # Handle patterns like "*.json"
                                    for item in base_path.iterdir():
                                        if item.is_file() and item.name.endswith(
                                            pattern.lstrip("*")
                                        ):
                                            found_files.add(item)
                            except (PermissionError, OSError) as e:
                                log_debug(f"Permission error scanning {base_path}: {e}")
                                continue

                        for conv_file in found_files:
                            try:
                                stat = conv_file.stat()

                                # For JSON files, we could count sessions
                                conversation_count = (
                                    1  # Each file is typically one session
                                )

                                database = ConversationDatabase(
                                    path=str(conv_file),
                                    tool_type="claude-code",
                                    size_bytes=stat.st_size,
                                    last_modified=stat.st_mtime,
                                    conversation_count=conversation_count,
                                    is_accessible=True,
                                )

                                databases.append(database)
                                log_debug(f"Found Claude Code file: {conv_file}")

                            except (OSError, ValueError, AttributeError) as e:
                                log_error(
                                    e,
                                    f"processing Claude Code file {conv_file}",
                                )
                                databases.append(
                                    ConversationDatabase(
                                        path=str(conv_file),
                                        tool_type="claude-code",
                                        size_bytes=0,
                                        last_modified=0.0,
                                        is_accessible=False,
                                        error_message=str(e),
                                    )
                                )
                    except (PermissionError, OSError) as e:
                        log_debug(f"Cannot access Claude path {base_path}: {e}")
                        continue

        except TimeoutError:
            log_error(
                None,
                f"Claude database scan timed out after {self._scan_timeout} seconds",
            )
        except (OSError, ValueError, AttributeError) as e:
            log_error(e, "scanning Claude databases")

        return databases

    def _scan_windsurf_databases(self) -> List[ConversationDatabase]:
        """Scan for Windsurf conversation databases with timeout protection."""
        databases = []

        try:
            with timeout_context(self._scan_timeout):
                # Common Windsurf workspace paths
                windsurf_paths = WINDSURF_SCANNER_PATHS

                for base_path in windsurf_paths:
                    if not base_path.exists():
                        continue

                    log_debug(f"Scanning Windsurf path: {base_path}")

                    try:
                        # Windsurf uses workspace-specific directories similar to Cursor
                        for workspace_dir in base_path.iterdir():
                            if not workspace_dir.is_dir():
                                continue

                            try:
                                # Look for database files in workspace directory
                                for pattern in WINDSURF_DB_PATTERNS:
                                    for db_file in workspace_dir.glob(pattern):
                                        if db_file.is_file():
                                            try:
                                                stat = db_file.stat()

                                                # Try to count conversations in the database
                                                conversation_count = (
                                                    self._count_conversations_sqlite(
                                                        db_file
                                                    )
                                                )

                                                database = ConversationDatabase(
                                                    path=str(db_file),
                                                    tool_type="windsurf",
                                                    size_bytes=stat.st_size,
                                                    last_modified=stat.st_mtime,
                                                    conversation_count=conversation_count,
                                                    is_accessible=True,
                                                )

                                                databases.append(database)
                                                log_debug(
                                                    f"Found Windsurf database: {db_file}"
                                                )

                                            except (
                                                OSError,
                                                ValueError,
                                                AttributeError,
                                            ) as e:
                                                log_error(
                                                    e,
                                                    f"processing Windsurf database {db_file}",
                                                )
                                                databases.append(
                                                    ConversationDatabase(
                                                        path=str(db_file),
                                                        tool_type="windsurf",
                                                        size_bytes=0,
                                                        last_modified=0.0,
                                                        is_accessible=False,
                                                        error_message=str(e),
                                                    )
                                                )

                            except (PermissionError, OSError) as e:
                                log_debug(
                                    f"Cannot access workspace {workspace_dir}: {e}"
                                )
                                continue

                    except (PermissionError, OSError) as e:
                        log_debug(f"Cannot access Windsurf path {base_path}: {e}")
                        continue

        except TimeoutError:
            log_error(
                None,
                f"Windsurf database scan timed out after {self._scan_timeout} seconds",
            )
        except (OSError, ValueError, AttributeError) as e:
            log_error(e, "scanning Windsurf databases")

        return databases

    def scan(self, force_rescan: bool = False) -> List[ConversationDatabase]:
        """Scan for conversation databases across all supported agentic tools."""
        if not force_rescan and not self._should_rescan() and self.databases:
            log_debug("Using cached database scan results")
            return self.databases

        log_info("Scanning for conversation databases across agentic tools")
        start_time = time.time()

        all_databases = []

        try:
            with timeout_context(
                self._scan_timeout * 2
            ):  # Double timeout for full scan
                # Scan each supported agentic tool type
                for tool_type in SUPPORTED_AGENTIC_TOOLS:
                    try:
                        if tool_type == AGENTIC_TOOL_CURSOR:
                            databases = self._scan_cursor_databases()
                        elif tool_type == AGENTIC_TOOL_CLAUDE_CODE:
                            databases = self._scan_claude_databases()
                        elif tool_type == AGENTIC_TOOL_WINDSURF:
                            databases = self._scan_windsurf_databases()
                        else:
                            log_debug(
                                f"Unknown agentic tool type for scanning: {tool_type}"
                            )
                            continue

                        all_databases.extend(databases)
                        log_info(f"Found {len(databases)} databases for {tool_type}")
                    except (OSError, ValueError, AttributeError) as e:
                        log_error(e, f"scanning {tool_type} databases")
                        continue

            self.databases = all_databases
            self._last_scan_time = time.time()

            scan_duration = time.time() - start_time
            log_info(
                f"Database scan completed in {scan_duration:.2f}s, "
                f"found {len(all_databases)} total databases"
            )

        except TimeoutError:
            log_error(
                None,
                f"Full database scan timed out after {self._scan_timeout * 2} seconds",
            )
        except (OSError, ValueError, AttributeError) as e:
            log_error(e, "scanning all databases")

        return all_databases

    def get_databases_by_tool(self, tool_type: str) -> List[ConversationDatabase]:
        """Get databases filtered by agentic tool type."""
        if not self.databases:
            self.scan()

        return [db for db in self.databases if db.tool_type == tool_type]

    def get_summary(self) -> Dict[str, any]:
        """Get a summary of discovered databases."""
        if not self.databases:
            self.scan()

        summary = {
            "total_databases": len(self.databases),
            "accessible_databases": len(
                [db for db in self.databases if db.is_accessible]
            ),
            "total_conversations": sum(
                db.conversation_count or 0 for db in self.databases
            ),
            "tools": {},
        }

        # Group by agentic tool type
        for tool_type in SUPPORTED_AGENTIC_TOOLS:
            tool_databases = self.get_databases_by_tool(tool_type)
            if tool_databases:  # Only include tools that have databases
                summary["tools"][tool_type] = {
                    "database_count": len(tool_databases),
                    "conversation_count": sum(
                        db.conversation_count or 0 for db in tool_databases
                    ),
                    "accessible_count": len(
                        [db for db in tool_databases if db.is_accessible]
                    ),
                }

        return summary


def get_available_agentic_tools(silent: bool = False) -> List[str]:
    """Get list of agentic tools that have conversation databases available."""
    try:
        with timeout_context(45):  # 45 second timeout for the full operation
            scanner = DatabaseScanner()
            databases = scanner.scan()

            available_tools = set()
            for db in databases:
                if db.is_accessible and (db.conversation_count or 0) > 0:
                    available_tools.add(db.tool_type)

            result = list(available_tools)
            if not silent:
                log_info(f"Found conversation data for agentic tools: {result}")

            return result

    except TimeoutError:
        if not silent:
            log_error(
                None,
                "detecting available agentic tools timed out after 45 seconds",
            )
        return []
    except (OSError, ValueError, AttributeError) as e:
        if not silent:
            log_error(e, "detecting available agentic tools")
        return []

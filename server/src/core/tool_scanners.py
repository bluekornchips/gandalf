"""
Tool-specific database scanners for different agentic tools.

This module contains specialized scanners for Cursor, Claude Code,
and Windsurf conversation databases.
"""

from pathlib import Path
from typing import Any

from src.config.config_data import (
    CLAUDE_CONVERSATION_PATTERNS,
    CURSOR_DB_PATTERNS,
    WINDSURF_DB_PATTERNS,
)
from src.config.constants.paths import (
    CLAUDE_HOME,
    CURSOR_WORKSPACE_STORAGE,
    WINDSURF_WORKSPACE_STORAGE,
)
from src.core.database_counter import ConversationCounter
from src.core.database_scanner_base import (
    ConversationDatabase,
    create_error_database,
    timeout_context,
)
from src.utils.common import log_debug, log_error


class CursorScanner:
    """Scanner specialized for Cursor IDE databases."""

    def __init__(self, scan_timeout: int = 30) -> None:
        """Initialize Cursor scanner with timeout."""
        self.scan_timeout = scan_timeout

    def scan_databases(self) -> list[ConversationDatabase]:
        """Scan for Cursor conversation databases with timeout protection."""
        databases = []

        try:
            with timeout_context(self.scan_timeout):
                cursor_paths = CURSOR_WORKSPACE_STORAGE

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
                                    if (
                                        sub_item.is_file()
                                        and self._matches_cursor_pattern(sub_item)
                                    ):
                                        found_files.add(sub_item)
                                    elif sub_item.is_dir():
                                        # Go one more level deep
                                        try:
                                            for deep_item in sub_item.iterdir():
                                                if (
                                                    deep_item.is_file()
                                                    and self._matches_cursor_pattern(
                                                        deep_item
                                                    )
                                                ):
                                                    found_files.add(deep_item)
                                        except (PermissionError, OSError):
                                            continue
                            elif item.is_file() and self._matches_cursor_pattern(item):
                                found_files.add(item)

                        for db_file in found_files:
                            try:
                                database = self._create_cursor_database(db_file)
                                databases.append(database)
                                log_debug(f"Found Cursor database: {db_file}")

                            except (OSError, ValueError, AttributeError) as e:
                                log_error(e, f"processing Cursor database {db_file}")
                                databases.append(
                                    create_error_database(str(db_file), "cursor", e)
                                )
                    except (PermissionError, OSError) as e:
                        log_debug(
                            f"Cannot access workspace storage {workspace_storage}: {e}"
                        )
                        continue

        except TimeoutError as e:
            log_error(
                e,
                f"Cursor database scan timed out after {self.scan_timeout} seconds",
            )
        except (OSError, ValueError, AttributeError) as e:
            log_error(e, "scanning Cursor databases")

        return databases

    def _matches_cursor_pattern(self, file_path: Path) -> bool:
        """Check if file matches Cursor database patterns."""
        return any(
            file_path.name.endswith(pattern.lstrip("*"))
            for pattern in CURSOR_DB_PATTERNS
        )

    def _create_cursor_database(self, db_file: Path) -> ConversationDatabase:
        """Create ConversationDatabase entry for Cursor database."""
        stat = db_file.stat()
        conversation_count = ConversationCounter.count_conversations_sqlite(db_file)

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

        return database


class ClaudeScanner:
    """Scanner specialized for Claude Code conversation files."""

    def __init__(self, scan_timeout: int = 30) -> None:
        """Initialize Claude scanner with timeout."""
        self.scan_timeout = scan_timeout

    def scan_databases(self) -> list[ConversationDatabase]:
        """Scan for Claude Code conversation files with timeout protection."""
        databases = []

        try:
            with timeout_context(self.scan_timeout):
                claude_paths = CLAUDE_HOME

                for base_path in claude_paths:
                    if not base_path.exists():
                        continue

                    log_debug(f"Scanning Claude Code path: {base_path}")

                    try:
                        # Use a set to track found files and avoid duplicates
                        found_files = set()

                        for pattern in CLAUDE_CONVERSATION_PATTERNS:
                            try:
                                if "**" in pattern:
                                    # Handle recursive patterns like "projects/**/*.jsonl"
                                    parts = pattern.split("**")
                                    if len(parts) == 2:
                                        prefix = parts[0].rstrip("/")
                                        suffix = parts[1].lstrip("/")
                                        target_dir = (
                                            base_path / prefix if prefix else base_path
                                        )
                                        if target_dir.exists():
                                            # Use rglob for recursive search
                                            for item in target_dir.rglob(suffix):
                                                if item.is_file():
                                                    found_files.add(item)
                                elif "/" in pattern:
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
                                database = self._create_claude_database(conv_file)
                                databases.append(database)
                                log_debug(f"Found Claude Code file: {conv_file}")

                            except (OSError, ValueError, AttributeError) as e:
                                log_error(
                                    e,
                                    f"processing Claude Code file {conv_file}",
                                )
                                databases.append(
                                    create_error_database(
                                        str(conv_file), "claude-code", e
                                    )
                                )
                    except (PermissionError, OSError) as e:
                        log_debug(f"Cannot access Claude path {base_path}: {e}")
                        continue

        except TimeoutError as e:
            log_error(
                e,
                f"Claude database scan timed out after {self.scan_timeout} seconds",
            )
        except (OSError, ValueError, AttributeError) as e:
            log_error(e, "scanning Claude databases")

        return databases

    def _create_claude_database(self, conv_file: Path) -> ConversationDatabase:
        """Create ConversationDatabase entry for Claude Code file."""
        stat = conv_file.stat()

        # For JSON files, we could count sessions
        conversation_count = ConversationCounter.count_json_conversations(conv_file)

        return ConversationDatabase(
            path=str(conv_file),
            tool_type="claude-code",
            size_bytes=stat.st_size,
            last_modified=stat.st_mtime,
            conversation_count=conversation_count,
            is_accessible=True,
        )


class WindsurfScanner:
    """Scanner specialized for Windsurf IDE databases."""

    def __init__(self, scan_timeout: int = 30) -> None:
        """Initialize Windsurf scanner with timeout."""
        self.scan_timeout = scan_timeout

    def scan_databases(self) -> list[ConversationDatabase]:
        """Scan for Windsurf conversation databases with timeout protection."""
        databases = []

        try:
            with timeout_context(self.scan_timeout):
                windsurf_paths = WINDSURF_WORKSPACE_STORAGE

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
                                                database = (
                                                    self._create_windsurf_database(
                                                        db_file
                                                    )
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
                                                    create_error_database(
                                                        str(db_file), "windsurf", e
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

        except TimeoutError as e:
            log_error(
                e,
                f"Windsurf database scan timed out after {self.scan_timeout} seconds",
            )
        except (OSError, ValueError, AttributeError) as e:
            log_error(e, "scanning Windsurf databases")

        return databases

    def _create_windsurf_database(self, db_file: Path) -> ConversationDatabase:
        """Create ConversationDatabase entry for Windsurf database."""
        stat = db_file.stat()

        # Try to count conversations in the database
        conversation_count = ConversationCounter.count_conversations_sqlite(db_file)

        return ConversationDatabase(
            path=str(db_file),
            tool_type="windsurf",
            size_bytes=stat.st_size,
            last_modified=stat.st_mtime,
            conversation_count=conversation_count,
            is_accessible=conversation_count is not None,
        )


class ScannerFactory:
    """Factory for creating tool-specific scanners."""

    @staticmethod
    def create_cursor_scanner(scan_timeout: int = 30) -> CursorScanner:
        """Create Cursor scanner with specified timeout."""
        return CursorScanner(scan_timeout)

    @staticmethod
    def create_claude_scanner(scan_timeout: int = 30) -> ClaudeScanner:
        """Create Claude scanner with specified timeout."""
        return ClaudeScanner(scan_timeout)

    @staticmethod
    def create_windsurf_scanner(scan_timeout: int = 30) -> WindsurfScanner:
        """Create Windsurf scanner with specified timeout."""
        return WindsurfScanner(scan_timeout)

    @staticmethod
    def create_all_scanners(scan_timeout: int = 30) -> dict[str, Any]:
        """Create all available scanners."""
        return {
            "cursor": CursorScanner(scan_timeout),
            "claude-code": ClaudeScanner(scan_timeout),
            "windsurf": WindsurfScanner(scan_timeout),
        }

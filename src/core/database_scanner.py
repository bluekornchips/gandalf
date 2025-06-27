"""
Database scanner for Gandalf MCP server.

This module provides IDE-agnostic conversation database discovery across
Cursor, Claude Code, and other supported IDEs without requiring them to be running.
"""

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config.constants.database import (
    CLAUDE_CODE_LOCATIONS,
    CURSOR_COMPOSER_QUERY,
    CURSOR_LOCATIONS,
)
from src.config.constants.system import SUPPORTED_IDES
from src.utils.common import log_debug, log_error, log_info


@dataclass
class ConversationDatabase:
    """Represents a discovered conversation database."""

    ide_type: str
    database_path: Path
    conversation_count: int
    last_modified: float
    metadata: Dict[str, Any]


class DatabaseScanner:
    """Scanner for conversation databases across all IDEs."""

    def __init__(self, silent: bool = False):
        """Initialize the database scanner."""
        self.silent = silent
        self._discovered_databases: List[ConversationDatabase] = []

    def scan_all_databases(self) -> List[ConversationDatabase]:
        """Scan for all conversation databases across IDEs."""
        if not self.silent:
            log_info("Scanning for conversation databases...")

        self._discovered_databases = []

        # Scan Cursor databases
        for location in CURSOR_LOCATIONS:
            expanded_path = Path(location).expanduser()
            if expanded_path.exists():
                self._scan_cursor_location(expanded_path)

        # Scan Claude Code databases
        for location in CLAUDE_CODE_LOCATIONS:
            expanded_path = Path(location).expanduser()
            if expanded_path.exists():
                self._scan_claude_code_location(expanded_path)

        if not self.silent:
            log_info(
                f"Database scanner found {len(self._discovered_databases)} conversation databases"
            )

        return self._discovered_databases

    def _scan_cursor_location(self, location: Path) -> None:
        """Scan a Cursor workspace storage location for conversation databases."""
        try:
            for workspace_dir in location.iterdir():
                if workspace_dir.is_dir():
                    # Look for conversation database files
                    for db_file in workspace_dir.glob("*.vscdb"):
                        db_info = self._analyze_cursor_database(db_file)
                        if db_info:
                            self._discovered_databases.append(db_info)

                    for db_file in workspace_dir.glob("*.db"):
                        db_info = self._analyze_cursor_database(db_file)
                        if db_info:
                            self._discovered_databases.append(db_info)

        except (OSError, PermissionError) as e:
            if not self.silent:
                log_debug(f"Cannot access Cursor location {location}: {e}")

    def _scan_claude_code_location(self, location: Path) -> None:
        """Scan a Claude Code storage location for conversation data."""
        try:
            db_info = self._analyze_claude_code_storage(location)
            if db_info:
                self._discovered_databases.append(db_info)

        except (OSError, PermissionError) as e:
            if not self.silent:
                log_debug(
                    f"Cannot access Claude Code location {location}: {e}"
                )

    def _analyze_cursor_database(
        self, db_path: Path
    ) -> Optional[ConversationDatabase]:
        """Analyze a Cursor database file for conversation data."""
        try:
            with sqlite3.connect(str(db_path)) as conn:
                cursor = conn.cursor()

                # Check if this is a conversation database
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
                tables = [row[0] for row in cursor.fetchall()]

                if "ItemTable" in tables:
                    # Look for conversation data
                    cursor.execute(CURSOR_COMPOSER_QUERY)
                    result = cursor.fetchone()

                    if result:
                        try:
                            composer_data = json.loads(result[0])
                            if "allComposers" in composer_data:
                                conversation_count = len(
                                    composer_data["allComposers"]
                                )
                                last_modified = db_path.stat().st_mtime

                                return ConversationDatabase(
                                    ide_type="cursor",
                                    database_path=db_path,
                                    conversation_count=conversation_count,
                                    last_modified=last_modified,
                                    metadata={
                                        "tables": tables,
                                        "workspace": db_path.parent.name,
                                    },
                                )
                        except (json.JSONDecodeError, KeyError):
                            pass

        except (sqlite3.Error, OSError) as e:
            if not self.silent:
                log_debug(f"Cannot analyze Cursor database {db_path}: {e}")

        return None

    def _analyze_claude_code_storage(
        self, storage_path: Path
    ) -> Optional[ConversationDatabase]:
        """Analyze Claude Code storage for conversation files."""
        try:
            conversation_files = []
            for pattern in ["*.json", "*.md", "*.txt"]:
                conversation_files.extend(storage_path.glob(pattern))

            if conversation_files:
                last_modified = max(
                    f.stat().st_mtime for f in conversation_files
                )

                return ConversationDatabase(
                    ide_type="claude-code",
                    database_path=storage_path,
                    conversation_count=len(conversation_files),
                    last_modified=last_modified,
                    metadata={
                        "file_count": len(conversation_files),
                        "storage_type": "file_based",
                    },
                )

        except (OSError, PermissionError) as e:
            if not self.silent:
                log_debug(
                    f"Cannot analyze Claude Code storage {storage_path}: {e}"
                )

        return None

    def get_databases_by_ide(
        self, ide_type: str
    ) -> List[ConversationDatabase]:
        """Get all databases for a specific IDE."""
        return [
            db for db in self._discovered_databases if db.ide_type == ide_type
        ]

    def get_total_conversation_count(self) -> int:
        """Get total conversation count across all databases."""
        return sum(db.conversation_count for db in self._discovered_databases)

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of discovered databases."""
        summary = {
            "total_databases": len(self._discovered_databases),
            "total_conversations": self.get_total_conversation_count(),
            "ides": {},
        }

        for ide_type in SUPPORTED_IDES:
            ide_databases = self.get_databases_by_ide(ide_type)
            if ide_databases:
                summary["ides"][ide_type] = {
                    "database_count": len(ide_databases),
                    "conversation_count": sum(
                        db.conversation_count for db in ide_databases
                    ),
                    "last_activity": max(
                        db.last_modified for db in ide_databases
                    ),
                }

        return summary


# Convenience functions for external use
def scan_conversation_databases(
    silent: bool = False,
) -> List[ConversationDatabase]:
    """Scan for conversation databases across all IDEs."""
    scanner = DatabaseScanner(silent=silent)
    return scanner.scan_all_databases()


def get_available_ides(silent: bool = False) -> List[str]:
    """Get list of IDEs that have conversation databases available."""
    try:
        databases = scan_conversation_databases(silent=silent)
        available_ides = list(set(db.ide_type for db in databases))
        return sorted(available_ides)
    except Exception as e:
        if not silent:
            log_error(e, "detecting available IDEs via database scan")
        return []

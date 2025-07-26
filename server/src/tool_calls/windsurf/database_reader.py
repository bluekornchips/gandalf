"""
Database operations for Windsurf IDE conversation data.

This module handles database connectivity and data extraction
from Windsurf workspace databases.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any

from src.config.tool_config import (
    SQL_CHECK_ITEMTABLE_EXISTS,
    SQL_COUNT_ITEMTABLE_ROWS,
    SQL_GET_ALL_KEYS,
    SQL_GET_TABLE_NAMES,
    SQL_GET_VALUE_BY_KEY,
    WINDSURF_CONVERSATION_PATTERNS,
)
from src.utils.common import log_error
from src.utils.database_pool import get_database_connection


class DatabaseReader:
    """Handles database operations for Windsurf workspace data."""

    def __init__(self, silent: bool = False) -> None:
        """Initialize database reader with optional silent mode."""
        self.silent = silent

    def get_data(self, db_path: Path, key: str) -> Any | None:
        """Extract data from database using a specific key."""
        try:
            with get_database_connection(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(SQL_GET_VALUE_BY_KEY, (key,))
                result = cursor.fetchone()
                return json.loads(result[0]) if result else None
        except (sqlite3.Error, json.JSONDecodeError, OSError) as e:
            if not self.silent:
                log_error(e, f"reading from database {db_path}")
            return None

    def get_all_keys(self, db_path: Path) -> list[str]:
        """Get all keys from a database."""
        try:
            with get_database_connection(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(SQL_GET_ALL_KEYS)
                return [row[0] for row in cursor.fetchall()]
        except (sqlite3.Error, OSError) as e:
            if not self.silent:
                log_error(e, f"reading keys from database {db_path}")
            return []

    def find_conversation_keys(self, db_path: Path) -> list[str]:
        """Find database keys that might contain conversation data."""
        all_keys = self.get_all_keys(db_path)
        return [
            key
            for key in all_keys
            if any(pattern in key.lower() for pattern in WINDSURF_CONVERSATION_PATTERNS)
        ]

    def check_database_accessibility(self, db_path: Path) -> bool:
        """Check if database is accessible and has expected structure."""
        try:
            if not db_path.exists() or not db_path.is_file():
                return False

            with get_database_connection(db_path) as conn:
                cursor = conn.cursor()

                # Check if ItemTable exists
                cursor.execute(SQL_CHECK_ITEMTABLE_EXISTS)
                table_exists = cursor.fetchone() is not None

                if not table_exists:
                    if not self.silent:
                        # Use a ValueError for missing table since no exception was caught
                        log_error(
                            ValueError("ItemTable not found"),
                            f"ItemTable not found in database {db_path}",
                        )
                    return False

                return True

        except (sqlite3.Error, OSError) as e:
            if not self.silent:
                log_error(e, f"checking database accessibility: {db_path}")
            return False

    def get_database_metadata(self, db_path: Path) -> dict[str, Any]:
        """Get metadata about a database file."""
        metadata: dict[str, Any] = {
            "path": str(db_path),
            "exists": db_path.exists(),
            "is_file": db_path.is_file() if db_path.exists() else False,
            "accessible": False,
            "total_keys": 0,
            "conversation_keys": 0,
            "tables": [],
        }

        if not metadata["exists"] or not metadata["is_file"]:
            return metadata

        try:
            with get_database_connection(db_path) as conn:
                cursor = conn.cursor()

                # Get table names
                cursor.execute(SQL_GET_TABLE_NAMES)
                metadata["tables"] = [row[0] for row in cursor.fetchall()]

                # Check if accessible (has ItemTable)
                metadata["accessible"] = "ItemTable" in metadata["tables"]

                if metadata["accessible"]:
                    # Get key counts
                    all_keys = self.get_all_keys(db_path)
                    metadata["total_keys"] = len(all_keys)
                    metadata["conversation_keys"] = len(
                        self.find_conversation_keys(db_path)
                    )

        except (sqlite3.Error, OSError) as e:
            if not self.silent:
                log_error(e, f"getting database metadata: {db_path}")

        return metadata

    def test_database_connection(self, db_path: Path) -> dict[str, Any]:
        """Test database connection and return diagnostic information."""
        result: dict[str, Any] = {
            "success": False,
            "error": None,
            "metadata": self.get_database_metadata(db_path),
        }

        try:
            if not db_path.exists():
                result["error"] = f"Database file does not exist: {db_path}"
                return result

            if not db_path.is_file():
                result["error"] = f"Path is not a file: {db_path}"
                return result

            with get_database_connection(db_path) as conn:
                cursor = conn.cursor()

                # Test basic query
                cursor.execute(SQL_COUNT_ITEMTABLE_ROWS)
                row_count = cursor.fetchone()[0]

                result["success"] = True
                result["metadata"]["row_count"] = row_count

        except sqlite3.Error as e:
            result["error"] = f"SQLite error: {str(e)}"
        except OSError as e:
            result["error"] = f"OS error: {str(e)}"
        except Exception as e:
            result["error"] = f"Unexpected error: {str(e)}"

        return result

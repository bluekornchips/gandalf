"""
Database conversation counting utilities.

This module provides utilities for counting conversations in various
database formats across different agentic tools.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any

from src.config.core_constants import DATABASE_OPERATION_TIMEOUT
from src.config.tool_config import (
    CONVERSATION_TABLE_NAMES,
    CURSOR_CONVERSATION_KEYS,
    SQL_CHECK_ITEMTABLE_EXISTS,
    SQL_COUNT_TABLE_ROWS,
    SQL_GET_ALL_KEYS,
    SQL_GET_TABLE_NAMES,
    SQL_GET_VALUE_BY_KEY,
    WINDSURF_KEY_CHAT_SESSION_STORE,
)
from src.core.database_scanner import timeout_context
from src.utils.common import log_debug, log_error
from src.utils.database_pool import get_database_connection


class ConversationCounter:
    """Handles counting conversations in various database formats."""

    @staticmethod
    def count_conversations_sqlite(db_path: Path) -> int | None:
        """Count conversations in a SQLite database safely using connection pool."""
        try:
            with timeout_context(DATABASE_OPERATION_TIMEOUT):
                with get_database_connection(db_path) as conn:
                    cursor = conn.cursor()

                    # Log detailed diagnostic info
                    log_debug(f"Analyzing database structure: {db_path}")

                    # Get table information for diagnostics
                    try:
                        cursor.execute(SQL_GET_TABLE_NAMES)
                        tables = [row[0] for row in cursor.fetchall()]
                        log_debug(f"Available tables in {db_path.name}: {tables}")
                    except sqlite3.OperationalError as e:
                        log_debug(f"Could not get table list from {db_path}: {e}")
                        tables = []

                    # Check if this is a Cursor/Windsurf database with ItemTable
                    try:
                        cursor.execute(SQL_CHECK_ITEMTABLE_EXISTS)
                        if cursor.fetchone():
                            log_debug(f"Found ItemTable structure in {db_path}")
                            count = ConversationCounter._count_vscode_conversations(
                                cursor
                            )
                            log_debug(f"VSCode conversation count result: {count}")
                            return count
                    except sqlite3.OperationalError as e:
                        log_debug(f"ItemTable check failed for {db_path}: {e}")

                    # Try standard conversation tables
                    for table_name in CONVERSATION_TABLE_NAMES:
                        try:
                            cursor.execute(
                                SQL_COUNT_TABLE_ROWS.format(table_name=table_name)
                            )
                            count = int(cursor.fetchone()[0])
                            log_debug(
                                f"Found {count} conversations in {db_path} "
                                f"(table: {table_name})"
                            )
                            return count
                        except sqlite3.OperationalError as e:
                            log_debug(f"Table {table_name} not found in {db_path}: {e}")
                            continue

                    # If we found tables but no conversation data, provide info
                    if tables:
                        log_debug(
                            f"Database {db_path} has tables {tables} "
                            f"but no recognizable conversation data"
                        )
                        # Try to get ItemTable keys for diagnostic
                        if "ItemTable" in tables:
                            try:
                                cursor.execute(f"{SQL_GET_ALL_KEYS} LIMIT 10")
                                keys = [row[0] for row in cursor.fetchall()]
                                log_debug(
                                    f"ItemTable keys in {db_path.name}: "
                                    f"{keys[:5]}{'...' if len(keys) > 5 else ''}"
                                )
                            except sqlite3.OperationalError:
                                pass
                    else:
                        log_debug(f"No tables found in {db_path}")

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

    @staticmethod
    def _count_vscode_conversations(cursor: Any) -> int:
        """Count conversations in a Cursor/Windsurf database using ItemTable."""
        try:
            # Modern Cursor format, try multiple keys for version compatibility
            log_debug("Checking for Cursor conversation data")
            for key in CURSOR_CONVERSATION_KEYS:
                cursor.execute(SQL_GET_VALUE_BY_KEY, (key,))
                result = cursor.fetchone()
                if result:
                    try:
                        data = json.loads(result[0])
                        if key == "composer.composerData" and isinstance(data, dict):
                            # Modern composer format
                            all_composers = data.get("allComposers", [])
                            if all_composers:
                                log_debug(
                                    f"Found {len(all_composers)} Cursor conversations "
                                    f"via composer.composerData"
                                )
                                return len(all_composers)
                        elif key == "interactive.sessions" and isinstance(data, list):
                            # Interactive sessions format
                            if data:
                                log_debug(
                                    f"Found {len(data)} Cursor conversations "
                                    f"via interactive.sessions"
                                )
                                return len(data)
                    except (json.JSONDecodeError, TypeError, KeyError) as e:
                        log_debug(f"Failed to parse {key}: {e}")
                        continue

            log_debug("No Cursor conversation data found")

            # Modern Windsurf format, try multiple keys for compatibility
            log_debug("Checking for Windsurf chat session store")
            chat_data = None
            for key in WINDSURF_KEY_CHAT_SESSION_STORE:
                cursor.execute(SQL_GET_VALUE_BY_KEY, (key,))
                result = cursor.fetchone()
                if result:
                    try:
                        potential_data = json.loads(result[0])
                        if isinstance(potential_data, dict) and potential_data.get(
                            "entries"
                        ):
                            chat_data = potential_data
                            log_debug(f"Found Windsurf data using key: {key}")
                            break
                    except (json.JSONDecodeError, TypeError):
                        continue

            if chat_data:
                entries = chat_data.get("entries", {})
                if isinstance(entries, dict | list):
                    log_debug(f"Found {len(entries)} Windsurf conversations")
                    return len(entries)
                else:
                    log_debug(f"Windsurf entries is not list/dict: {type(entries)}")
                    return 0
            else:
                log_debug("No Windsurf chat session store found")
                return 0

        except (sqlite3.Error, ValueError, TypeError) as e:
            log_debug(f"Error counting Cursor conversations: {e}")
            return 0

    @staticmethod
    def count_json_conversations(file_path: Path) -> int:
        """Count conversations in a JSON file (for Claude Code)."""
        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)

            # Handle different JSON structures
            if isinstance(data, list):
                # Array of conversations
                return len(data)
            elif isinstance(data, dict):
                # Object with conversations field
                conversations = data.get("conversations", data.get("sessions", []))
                if isinstance(conversations, list) and conversations:
                    return len(conversations)
                # Single conversation object (or empty conversations list)
                return 1
            else:
                # Unknown format, assume single conversation
                return 1

        except (json.JSONDecodeError, OSError, KeyError) as e:
            log_debug(f"Error counting JSON conversations in {file_path}: {e}")
            return 1  # Assume file exists so at least 1 conversation

    @staticmethod
    def estimate_conversations_from_file_size(file_path: Path, tool_type: str) -> int:
        """Estimate conversation count based on file size and tool type."""
        try:
            size_bytes = file_path.stat().st_size

            # Rough estimates based on typical conversation sizes
            if tool_type == "cursor":
                # Cursor conversations are typically larger due to code context
                avg_conversation_kb = 50
            elif tool_type == "claude-code":
                # Claude Code conversations vary widely
                avg_conversation_kb = 30
            elif tool_type == "windsurf":
                # Windsurf similar to Cursor
                avg_conversation_kb = 40
            else:
                # Default estimate
                avg_conversation_kb = 35

            estimated_count = max(1, size_bytes // (avg_conversation_kb * 1024))

            log_debug(
                f"Estimated {estimated_count} conversations in {file_path} "
                f"based on {size_bytes} bytes ({tool_type})"
            )

            return estimated_count

        except (OSError, ValueError) as e:
            log_debug(f"Error estimating conversations for {file_path}: {e}")
            return 1

    @staticmethod
    def validate_database_structure(db_path: Path) -> bool:
        """Validate that a database has the expected structure for conversations."""
        try:
            with timeout_context(5):  # Short timeout for structure check
                with get_database_connection(db_path) as conn:
                    cursor = conn.cursor()

                    # Check for any recognizable table structure
                    cursor.execute(SQL_GET_TABLE_NAMES)
                    tables = [row[0] for row in cursor.fetchall()]

                    # Check for ItemTable (Cursor/Windsurf) or conversation tables
                    has_item_table = "ItemTable" in tables
                    has_conversation_tables = any(
                        table in tables for table in CONVERSATION_TABLE_NAMES
                    )

                    return has_item_table or has_conversation_tables

        except (sqlite3.Error, OSError, TimeoutError) as e:
            log_debug(f"Error validating database structure {db_path}: {e}")
            return False

    @staticmethod
    def get_database_info(db_path: Path) -> dict[str, Any]:
        """Get detailed information about a database."""
        info = {
            "path": str(db_path),
            "exists": False,
            "size_bytes": 0,
            "tables": [],
            "conversation_count": None,
            "structure_valid": False,
            "error": None,
        }

        try:
            info["exists"] = db_path.exists()

            if not info["exists"]:
                info["error"] = "File does not exist"
                return info

            # Get size first, before validation
            info["size_bytes"] = db_path.stat().st_size

            # Validate structure but don't let it stop other info gathering
            try:
                info["structure_valid"] = (
                    ConversationCounter.validate_database_structure(db_path)
                )
            except Exception as validation_error:
                # If validation fails, record error but continue gathering info
                info["error"] = str(validation_error)
                info["structure_valid"] = False

            if info["structure_valid"]:
                info["conversation_count"] = (
                    ConversationCounter.count_conversations_sqlite(db_path)
                )

            # Always try to get table information for debugging
            try:
                with get_database_connection(db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(SQL_GET_TABLE_NAMES)
                    info["tables"] = [row[0] for row in cursor.fetchall()]
            except (sqlite3.Error, OSError, TimeoutError) as e:
                # If we can't get tables, leave empty list and log debug info
                log_debug(f"Could not get table information from {db_path}: {e}")
                info["tables"] = []

            # Set error only if structure invalid AND no basic info AND no error set
            if not info["structure_valid"] and not info["tables"] and not info["error"]:
                info["error"] = "Database structure is invalid or corrupted"

        except Exception as e:
            # For stat errors, we may still know the file exists
            if "Stat failed" in str(e):
                info["exists"] = True
            # Only set error if not already set by validation
            if not info["error"]:
                info["error"] = str(e)

        return info

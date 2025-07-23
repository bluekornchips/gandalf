"""
Database conversation counting utilities.

This module provides utilities for counting conversations in various
database formats across different agentic tools.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any

from src.config.constants.database import (
    CONVERSATION_TABLE_NAMES,
    CURSOR_KEY_AI_CONVERSATIONS,
    CURSOR_KEY_AI_GENERATIONS,
    CURSOR_KEY_AI_PROMPTS,
    CURSOR_KEY_COMPOSER_DATA,
    SQL_CHECK_ITEMTABLE_EXISTS,
    SQL_COUNT_TABLE_ROWS,
    SQL_GET_VALUE_BY_KEY,
    WINDSURF_KEY_CHAT_SESSION_INDEX,
    WINDSURF_KEY_CHAT_SESSION_STORE,
)
from src.config.constants.limits import DATABASE_OPERATION_TIMEOUT
from src.core.database_scanner_base import timeout_context
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

                    # Check if this is a Cursor/Windsurf database with 'ItemTable' structure
                    try:
                        cursor.execute(SQL_CHECK_ITEMTABLE_EXISTS)
                        if cursor.fetchone():
                            return ConversationCounter._count_vscode_conversations(
                                cursor
                            )
                    except sqlite3.OperationalError:
                        pass

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

    @staticmethod
    def _count_vscode_conversations(cursor: Any) -> int:  # noqa: C901
        """Count conversations in a Cursor/Windsurf database using ItemTable structure."""
        try:
            # Check for composer data (newer format)
            cursor.execute(SQL_GET_VALUE_BY_KEY, (CURSOR_KEY_COMPOSER_DATA,))
            result = cursor.fetchone()
            if result:
                try:
                    composer_data = json.loads(result[0])
                    if isinstance(composer_data, dict):
                        all_composers = composer_data.get("allComposers", [])
                        if all_composers:
                            log_debug(
                                f"Found {len(all_composers)} conversations in "
                                f"composer.composerData"
                            )
                            return len(all_composers)
                except (json.JSONDecodeError, TypeError, KeyError):
                    pass

            # Fallback: Check for aiConversations (older format)
            cursor.execute(SQL_GET_VALUE_BY_KEY, (CURSOR_KEY_AI_CONVERSATIONS,))
            result = cursor.fetchone()
            if result:
                try:
                    ai_conversations = json.loads(result[0])
                    if isinstance(ai_conversations, list):
                        log_debug(
                            f"Found {len(ai_conversations)} conversations in "
                            f"aiConversations"
                        )
                        return len(ai_conversations)
                except (json.JSONDecodeError, TypeError):
                    pass

            cursor.execute(SQL_GET_VALUE_BY_KEY, (WINDSURF_KEY_CHAT_SESSION_INDEX,))
            result = cursor.fetchone()
            if result:
                try:
                    chat_data = json.loads(result[0])
                    if isinstance(chat_data, dict):
                        entries = chat_data.get("entries", {})
                        if entries:
                            log_debug(f"Found {len(entries)} Windsurf chat sessions")
                            return len(entries)
                except (json.JSONDecodeError, TypeError, KeyError):
                    pass

            # Check alternative Windsurf key
            cursor.execute(SQL_GET_VALUE_BY_KEY, (WINDSURF_KEY_CHAT_SESSION_STORE,))
            result = cursor.fetchone()
            if result:
                try:
                    chat_data = json.loads(result[0])
                    if isinstance(chat_data, dict):
                        sessions = chat_data.get(
                            "sessions", chat_data.get("entries", [])
                        )
                        if isinstance(sessions, list):
                            log_debug(f"Found {len(sessions)} Windsurf conversations")
                            return len(sessions)
                        elif isinstance(sessions, dict):
                            log_debug(f"Found {len(sessions)} Windsurf conversations")
                            return len(sessions)
                except (json.JSONDecodeError, TypeError, KeyError):
                    pass

            # Check for prompts/generations that could be reconstructed into conversations
            cursor.execute(SQL_GET_VALUE_BY_KEY, (CURSOR_KEY_AI_PROMPTS,))
            prompts_result = cursor.fetchone()
            cursor.execute(SQL_GET_VALUE_BY_KEY, (CURSOR_KEY_AI_GENERATIONS,))
            generations_result = cursor.fetchone()

            prompts_count = 0
            generations_count = 0

            if prompts_result:
                try:
                    prompts = json.loads(prompts_result[0])
                    if isinstance(prompts, list):
                        prompts_count = len(prompts)
                except (json.JSONDecodeError, TypeError):
                    pass

            if generations_result:
                try:
                    generations = json.loads(generations_result[0])
                    if isinstance(generations, list):
                        generations_count = len(generations)
                except (json.JSONDecodeError, TypeError):
                    pass

            # If we have prompts or generations, estimate conversations
            if prompts_count > 0 or generations_count > 0:
                estimated_conversations = max(
                    1, (prompts_count + generations_count) // 4
                )
                log_debug(
                    f"Estimated {estimated_conversations} conversations from "
                    f"{prompts_count} prompts and {generations_count} generations"
                )
                return estimated_conversations

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
                if isinstance(conversations, list):
                    return len(conversations)
                # Single conversation object
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
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
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
            "exists": db_path.exists(),
            "size_bytes": 0,
            "tables": [],
            "conversation_count": None,
            "structure_valid": False,
            "error": None,
        }

        if not info["exists"]:
            info["error"] = "File does not exist"
            return info

        try:
            info["size_bytes"] = db_path.stat().st_size
            info["structure_valid"] = ConversationCounter.validate_database_structure(
                db_path
            )

            if info["structure_valid"]:
                info["conversation_count"] = (
                    ConversationCounter.count_conversations_sqlite(db_path)
                )

                # Get table information
                with get_database_connection(db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    info["tables"] = [row[0] for row in cursor.fetchall()]

        except Exception as e:
            info["error"] = str(e)

        return info

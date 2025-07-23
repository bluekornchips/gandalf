"""
Main query interface for Windsurf IDE conversation data.

This module provides the primary interface for querying and searching
Windsurf conversation data across workspace databases.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from src.config.constants.database import (
    WINDSURF_KEY_CHAT_SESSION_STORE,
)
from src.config.constants.paths import (
    WINDSURF_GLOBAL_STORAGE,
    WINDSURF_WORKSPACE_STORAGE,
)
from src.tool_calls.windsurf.conversation_extractor import ConversationExtractor
from src.tool_calls.windsurf.database_reader import DatabaseReader
from src.tool_calls.windsurf.query_validator import ConversationValidator
from src.utils.common import log_error


class WindsurfQuery:
    """Main query interface for Windsurf conversation data."""

    def __init__(self, silent: bool = False) -> None:
        """Initialize with workspace storage and components."""
        self.silent = silent
        self.workspace_storage = WINDSURF_WORKSPACE_STORAGE
        self.global_storage = WINDSURF_GLOBAL_STORAGE
        self.db_reader = DatabaseReader(silent)
        self.validator = ConversationValidator()
        self.extractor = ConversationExtractor(self.db_reader, self.validator, self)

    def get_data_from_db(self, db_path: Path, key: str) -> Any | None:
        """Extract data from database using a specific key."""
        try:
            return self.db_reader.get_data(db_path, key)
        except (sqlite3.Error, json.JSONDecodeError, OSError) as e:
            if not self.silent:
                log_error(e, f"querying database {db_path}")
            return None

    def find_workspace_databases(self) -> list[Path]:
        """Find all workspace and global database files."""
        return self._find_workspace_databases()

    def query_conversations_from_db(self, db_path: Path) -> dict[str, Any]:
        """Query all conversation data from a single database."""
        # Try chat sessions first (most reliable)
        conversations = self.extractor.extract_from_chat_sessions(db_path)

        # Fall back to database key scanning if no chat sessions found
        if not conversations:
            conversations = self.extractor.extract_from_database_keys(db_path)

        return self._create_db_response(conversations, db_path)

    def query_all_conversations(self) -> dict[str, Any]:
        """Query conversations from all database sources."""
        all_conversations = []
        databases = self._find_workspace_databases()

        for db_path in databases:
            try:
                db_data = self.query_conversations_from_db(db_path)
                all_conversations.extend(db_data.get("conversations", []))
            except (sqlite3.Error, json.JSONDecodeError, OSError) as e:
                if not self.silent:
                    log_error(e, f"querying database {db_path}")

        return {
            "conversations": all_conversations,
            "total_conversations": len(all_conversations),
            "total_databases": len(databases),
            "sources_scanned": ["databases"],
            "query_timestamp": datetime.now().isoformat(),
        }

    def search_conversations(
        self, query: str, project_root: Path | None = None, limit: int = 20
    ) -> list[dict[str, Any]]:
        """Search conversations for specific content."""
        all_data = self.query_all_conversations()
        conversations = all_data.get("conversations", [])

        return self._search_in_conversations(conversations, query, limit)

    def get_conversation_by_id(self, conversation_id: str) -> dict[str, Any] | None:
        """Get a specific conversation by ID."""
        all_data = self.query_all_conversations()
        conversations = all_data.get("conversations", [])

        for conv in conversations:
            if isinstance(conv, dict) and conv.get("id") == conversation_id:
                return conv

        return None

    def get_workspace_summary(self) -> dict[str, Any]:
        """Get summary of all workspaces and their conversation data."""
        databases = self._find_workspace_databases()
        workspace_summary: dict[str, Any] = {
            "total_databases": len(databases),
            "workspaces": [],
            "global_storage_found": False,
            "summary_timestamp": datetime.now().isoformat(),
        }

        for db_path in databases:
            try:
                workspace_info = {
                    "workspace_id": db_path.parent.name,
                    "database_path": str(db_path),
                    "accessible": self.db_reader.check_database_accessibility(db_path),
                    "extraction_stats": self.extractor.get_extraction_stats(db_path),
                }

                # Check if this is global storage
                if self.global_storage in db_path.parents:
                    workspace_summary["global_storage_found"] = True
                    workspace_info["is_global"] = True
                else:
                    workspace_info["is_global"] = False

                workspace_summary["workspaces"].append(workspace_info)

            except Exception as e:
                if not self.silent:
                    log_error(e, f"getting workspace summary for {db_path}")

        return workspace_summary

    def _find_workspace_databases(self) -> list[Path]:
        """Find all workspace and global database files."""
        databases = []

        # Search workspace storage
        for storage_path in self.workspace_storage:
            if storage_path.exists():
                try:
                    for workspace_dir in storage_path.iterdir():
                        if workspace_dir.is_dir():
                            db_file = workspace_dir / "state.vscdb"
                            if db_file.exists():
                                databases.append(db_file)
                except (OSError, PermissionError) as e:
                    if not self.silent:
                        log_error(
                            e,
                            f"scanning Windsurf workspace storage {storage_path}",
                        )

        # Search global storage
        if self.global_storage.exists():
            try:
                global_db_file = self.global_storage / "state.vscdb"
                if global_db_file.exists():
                    databases.append(global_db_file)
            except (OSError, PermissionError) as e:
                if not self.silent:
                    log_error(
                        e,
                        f"scanning Windsurf global storage {self.global_storage}",
                    )

        return databases

    def _create_db_response(
        self, conversations: list[dict[str, Any]], db_path: Path
    ) -> dict[str, Any]:
        """Create a standardized database response."""
        chat_sessions = self.db_reader.get_data(
            db_path, WINDSURF_KEY_CHAT_SESSION_STORE
        )

        return {
            "conversations": conversations,
            "total_conversations": len(conversations),
            "database_path": str(db_path),
            "query_timestamp": datetime.now().isoformat(),
            "has_chat_sessions": bool(chat_sessions and chat_sessions.get("entries")),
            "chat_session_empty": bool(
                chat_sessions and not chat_sessions.get("entries")
            ),
        }

    def _search_in_conversations(
        self, conversations: list[dict[str, Any]], query: str, limit: int
    ) -> list[dict[str, Any]]:
        """Search for query string in conversation data."""
        matching_conversations = []
        query_lower = query.lower()

        for conv in conversations:
            matches = self._find_matches_in_conversation(conv, query_lower)
            if matches:
                matching_conversations.append(
                    {
                        "conversation": conv,
                        "matches": matches,
                        "match_count": len(matches),
                    }
                )

                if len(matching_conversations) >= limit:
                    break

        return matching_conversations

    def _find_matches_in_conversation(
        self, conv: dict[str, Any], query_lower: str
    ) -> list[dict[str, str]]:
        """Find all matches for a query in a single conversation."""
        matches = []

        # Search in session data
        session_data = conv.get("session_data", {})
        if isinstance(session_data, dict):
            session_text = json.dumps(session_data, default=str).lower()
            if query_lower in session_text:
                matches.append(
                    {
                        "type": "session_data",
                        "content": self._truncate_content(str(session_data), 200),
                    }
                )

        # Search in other fields
        search_fields = ["title", "content", "messages", "text"]
        for field in search_fields:
            if field in conv:
                field_matches = self._search_in_field(conv[field], field, query_lower)
                matches.extend(field_matches)

        return matches

    def _search_in_field(
        self, field_value: Any, field_name: str, query_lower: str
    ) -> list[dict[str, str]]:
        """Search for query in a specific field."""
        matches = []

        if isinstance(field_value, str) and query_lower in field_value.lower():
            matches.append(
                {
                    "type": field_name,
                    "content": self._truncate_content(field_value, 200),
                }
            )
        elif isinstance(field_value, list | dict):
            field_text = json.dumps(field_value, default=str).lower()
            if query_lower in field_text:
                matches.append(
                    {
                        "type": field_name,
                        "content": self._truncate_content(str(field_value), 200),
                    }
                )

        return matches

    @staticmethod
    def _truncate_content(content: str, max_length: int) -> str:
        """Truncate content to specified length with ellipsis."""
        return content[:max_length] + "..." if len(content) > max_length else content

    def test_connectivity(self) -> dict[str, Any]:
        """Test connectivity to all Windsurf databases."""
        databases = self._find_workspace_databases()
        connectivity_results: dict[str, Any] = {
            "total_databases_found": len(databases),
            "successful_connections": 0,
            "failed_connections": 0,
            "database_results": [],
            "test_timestamp": datetime.now().isoformat(),
        }

        for db_path in databases:
            test_result = self.db_reader.test_database_connection(db_path)
            connectivity_results["database_results"].append(test_result)

            if test_result["success"]:
                connectivity_results["successful_connections"] += 1
            else:
                connectivity_results["failed_connections"] += 1

        return connectivity_results

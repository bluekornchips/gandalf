"""
Windsurf conversation query tool.

Provides focused access to actual Windsurf IDE conversation data from workspace databases,
with strict validation to avoid false positives from non-conversation data.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config.constants.conversation import (
    CONVERSATION_CONTENT_KEYS,
    CONVERSATION_FALSE_POSITIVE_INDICATORS,
    CONVERSATION_FALSE_POSITIVE_RATIO_THRESHOLD,
    CONVERSATION_MAX_ANALYSIS_LENGTH,
    CONVERSATION_MAX_LIST_ITEMS_TO_CHECK,
    CONVERSATION_MESSAGE_INDICATORS,
    CONVERSATION_MIN_CONTENT_LENGTH,
    CONVERSATION_STRONG_INDICATORS,
)
from src.config.constants.database import (
    WINDSURF_KEY_CHAT_SESSION_STORE,
)
from src.config.constants.paths import (
    WINDSURF_GLOBAL_STORAGE,
    WINDSURF_WORKSPACE_STORAGE,
)
from src.utils.access_control import AccessValidator
from src.utils.common import log_error

# Windsurf-specific constants (different from generic database constants)
WINDSURF_CONVERSATION_PATTERNS = {
    "chat",
    "conversation",
    "message",
    "session",
    "dialog",
    "ai",
    "assistant",
    "windsurf",
    "cascade",
    "codeium",
    "history",
    "input",
    "output",
    "response",
    "query",
    "prompt",
    "brain",
    "config",
}

WINDSURF_STRONG_CONVERSATION_INDICATORS = {
    "messages",
    "content",
    "text",
    "input",
    "output",
    "prompt",
    "response",
    "user",
    "assistant",
    "ai",
    "human",
    "question",
    "answer",
    "chat",
    "conversation",
    "brain",
    "config",
    "session",
    "entries",
}

WINDSURF_FALSE_POSITIVE_INDICATORS = {
    "workbench",
    "panel",
    "view",
    "container",
    "storage",
    "settings",
    "layout",
    "editor",
    "terminal",
    "debug",
    "extension",
    "plugin",
    "theme",
    "color",
    "font",
    "keybinding",
    "menu",
    "toolbar",
    "statusbar",
    "sidebar",
    "explorer",
    "search",
}

WINDSURF_CONTENT_KEYS = {
    "messages",
    "content",
    "text",
    "input",
    "output",
    "body",
    "message",
    "entries",
    "data",
}

WINDSURF_MESSAGE_INDICATORS = {
    "message",
    "content",
    "text",
    "user",
    "assistant",
    "conversation",
    "chat",
}


class ConversationValidator:
    """Validates whether data represents actual conversation content."""

    @staticmethod
    def is_valid_conversation(data: Any) -> bool:
        """Check if data represents a valid conversation with strict validation."""
        if not isinstance(data, (dict, list)):
            return False

        # Limit string analysis for performance
        data_str = str(data)[:CONVERSATION_MAX_ANALYSIS_LENGTH].lower()

        # Check for strong conversation indicators
        strong_count = sum(
            1 for indicator in CONVERSATION_STRONG_INDICATORS if indicator in data_str
        )
        if strong_count == 0:
            return False

        # Reject if too many false positive indicators
        false_positive_count = sum(
            1
            for indicator in CONVERSATION_FALSE_POSITIVE_INDICATORS
            if indicator in data_str
        )
        if (
            false_positive_count
            > strong_count * CONVERSATION_FALSE_POSITIVE_RATIO_THRESHOLD
        ):
            return False

        return ConversationValidator._validate_structure(data)

    @staticmethod
    def _validate_structure(data: Any) -> bool:
        """Validate the internal structure of potential conversation data."""
        if isinstance(data, dict):
            return ConversationValidator._validate_dict_structure(data)
        elif isinstance(data, list):
            return ConversationValidator._validate_list_structure(data)
        return False

    @staticmethod
    def _validate_dict_structure(data: Dict[str, Any]) -> bool:
        """Validate dictionary structure for conversation content."""
        # Check for direct content keys at top level
        has_content = any(key in data for key in CONVERSATION_CONTENT_KEYS)
        if has_content:
            # Check if content is meaningful, relatively meaningful, human thing idk this is hard to qualify
            for key in CONVERSATION_CONTENT_KEYS:
                if key in data:
                    content = data[key]
                    if (
                        isinstance(content, str)
                        and len(content.strip()) > CONVERSATION_MIN_CONTENT_LENGTH
                    ):
                        return True
                    elif isinstance(content, (list, dict)) and content:
                        return True

        for key, value in data.items():
            if isinstance(value, list) and value:
                for item in value:
                    if isinstance(item, dict):
                        item_has_content = any(
                            content_key in item
                            for content_key in CONVERSATION_CONTENT_KEYS
                        )
                        if item_has_content:
                            return True

        return False

    @staticmethod
    def _validate_list_structure(data: List[Any]) -> bool:
        """Validate list structure for conversation messages."""
        if not data:
            return False

        message_like_items = 0
        for item in data[:CONVERSATION_MAX_LIST_ITEMS_TO_CHECK]:
            if isinstance(item, dict):
                item_str = str(item).lower()
                has_message_indicators = any(
                    indicator in item_str
                    for indicator in CONVERSATION_MESSAGE_INDICATORS
                )
                has_content_keys = any(key in item for key in CONVERSATION_CONTENT_KEYS)
                # Count as message-like if it has content keys, with or without message indicators
                if has_content_keys and (has_message_indicators or len(item) > 0):
                    message_like_items += 1

        return message_like_items > 0


class DatabaseReader:
    """Handles database operations for Windsurf workspace data."""

    def __init__(self, silent: bool = False):
        self.silent = silent

    def get_data(self, db_path: Path, key: str) -> Optional[Any]:
        """Extract data from database using a specific key."""
        try:
            with sqlite3.connect(str(db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM ItemTable WHERE key = ?", (key,))
                result = cursor.fetchone()
                return json.loads(result[0]) if result else None
        except (sqlite3.Error, json.JSONDecodeError, OSError) as e:
            if not self.silent:
                log_error(e, f"reading from database {db_path}")
            return None

    def get_all_keys(self, db_path: Path) -> List[str]:
        """Get all keys from a database."""
        try:
            with sqlite3.connect(str(db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT key FROM ItemTable")
                return [row[0] for row in cursor.fetchall()]
        except (sqlite3.Error, OSError) as e:
            if not self.silent:
                log_error(e, f"reading keys from database {db_path}")
            return []

    def find_conversation_keys(self, db_path: Path) -> List[str]:
        """Find database keys that might contain conversation data."""
        all_keys = self.get_all_keys(db_path)
        return [
            key
            for key in all_keys
            if any(pattern in key.lower() for pattern in WINDSURF_CONVERSATION_PATTERNS)
        ]


class ConversationExtractor:
    """Extracts and structures conversation data from various sources."""

    def __init__(
        self,
        db_reader: DatabaseReader,
        validator: ConversationValidator,
        query_instance: "WindsurfQuery" = None,
    ):
        self.db_reader = db_reader
        self.validator = validator
        self.query_instance = query_instance

    def extract_from_chat_sessions(self, db_path: Path) -> List[Dict[str, Any]]:
        """Extract conversations from Windsurf chat session store."""
        if self.query_instance:
            chat_sessions = self.query_instance.get_data_from_db(
                db_path, WINDSURF_KEY_CHAT_SESSION_STORE
            )
        else:
            chat_sessions = self.db_reader.get_data(
                db_path, WINDSURF_KEY_CHAT_SESSION_STORE
            )

        if not chat_sessions or not isinstance(chat_sessions, dict):
            return []

        conversations = []
        entries = chat_sessions.get("entries", {})

        for session_id, session_data in entries.items():
            if isinstance(session_data, dict) and self.validator.is_valid_conversation(
                session_data
            ):
                conversations.append(
                    self._create_conversation_entry(
                        session_id,
                        session_data,
                        "windsurf_chat_session",
                        db_path,
                    )
                )

        return conversations

    def extract_from_database_keys(self, db_path: Path) -> List[Dict[str, Any]]:
        """Extract conversations from database keys that might contain conversation data."""
        conversation_keys = self.db_reader.find_conversation_keys(db_path)
        conversations = []

        for key in conversation_keys:
            if self.query_instance:
                data = self.query_instance.get_data_from_db(db_path, key)
            else:
                data = self.db_reader.get_data(db_path, key)

            if data:
                conversations.extend(
                    self._extract_from_data_structure(key, data, db_path)
                )

        return conversations

    def _extract_from_data_structure(
        self, key: str, data: Any, db_path: Path
    ) -> List[Dict[str, Any]]:
        """Extract conversations from various data structures."""
        conversations = []

        try:
            if isinstance(data, dict):
                conversations.extend(self._extract_from_dict(key, data, db_path))
            elif isinstance(data, list):
                conversations.extend(self._extract_from_list(key, data, db_path))
        except (KeyError, AttributeError, TypeError, ValueError):
            # Silently ignore extraction errors
            pass

        return conversations

    def _extract_from_dict(
        self, key: str, data: Dict[str, Any], db_path: Path
    ) -> List[Dict[str, Any]]:
        """Extract conversations from dictionary data."""
        conversations = []

        # Check for entries pattern
        if "entries" in data and isinstance(data["entries"], dict) and data["entries"]:
            for entry_id, entry_data in data["entries"].items():
                if isinstance(
                    entry_data, dict
                ) and self.validator.is_valid_conversation(entry_data):
                    conversations.append(
                        self._create_conversation_entry(
                            entry_id,
                            entry_data,
                            "windsurf_db_entry",
                            db_path,
                            source_key=key,
                            raw_data=data,
                        )
                    )

        # Check direct conversation data
        elif self.validator.is_valid_conversation(data):
            conversations.append(
                self._create_conversation_entry(
                    f"{key}_{hash(str(data)) % 10000}",
                    data,
                    "windsurf_db_direct",
                    db_path,
                    source_key=key,
                    raw_data=data,
                )
            )

        # Check nested data
        else:
            for sub_key, sub_value in data.items():
                if isinstance(sub_value, list) and self.validator.is_valid_conversation(
                    sub_value
                ):
                    # Extract individual conversations from the list
                    conversations.extend(
                        self._extract_from_list(f"{key}_{sub_key}", sub_value, db_path)
                    )
                elif isinstance(
                    sub_value, dict
                ) and self.validator.is_valid_conversation(sub_value):
                    conversations.append(
                        self._create_conversation_entry(
                            f"{key}_{sub_key}",
                            sub_value,
                            "windsurf_db_nested",
                            db_path,
                            source_key=key,
                            raw_data=data,
                            sub_key=sub_key,
                        )
                    )

        return conversations

    def _extract_from_list(
        self, key: str, data: List[Any], db_path: Path
    ) -> List[Dict[str, Any]]:
        """Extract conversations from list data."""
        conversations = []

        for i, item in enumerate(data):
            if isinstance(item, dict) and self.validator.is_valid_conversation(item):
                # Use the item's ID if available, otherwise generate one
                conv_id = item.get("id", f"{key}_{i}")
                conversations.append(
                    self._create_conversation_entry(
                        conv_id,
                        item,
                        "windsurf_db_list",
                        db_path,
                        source_key=key,
                        raw_data=data,
                        list_index=i,
                    )
                )

        return conversations

    def _create_conversation_entry(
        self, conv_id: str, data: Any, source: str, db_path: Path, **kwargs
    ) -> Dict[str, Any]:
        """Create a standardized conversation entry."""
        entry = {
            "id": conv_id,
            "source": source,
            "data": data,
            "database_path": str(db_path),
            "workspace_id": db_path.parent.name,
        }

        # Add session_data for chat sessions
        if source == "windsurf_chat_session":
            entry["session_data"] = data

        # Add optional metadata
        entry.update(kwargs)

        return entry


class WindsurfQuery:
    """Main query interface for Windsurf conversation data."""

    def __init__(self, silent: bool = False):
        """Initialize with workspace storage and components."""
        self.silent = silent
        self.workspace_storage = WINDSURF_WORKSPACE_STORAGE
        self.global_storage = WINDSURF_GLOBAL_STORAGE
        self.db_reader = DatabaseReader(silent)
        self.validator = ConversationValidator()
        self.extractor = ConversationExtractor(self.db_reader, self.validator, self)

    def get_data_from_db(self, db_path: Path, key: str) -> Optional[Any]:
        """Extract data from database using a specific key."""
        try:
            return self.db_reader.get_data(db_path, key)
        except (sqlite3.Error, json.JSONDecodeError, OSError) as e:
            if not self.silent:
                log_error(e, f"querying database {db_path}")
            return None

    def find_workspace_databases(self) -> List[Path]:
        """Find all workspace and global database files."""
        return self._find_workspace_databases()

    def query_conversations_from_db(self, db_path: Path) -> Dict[str, Any]:
        """Query all conversation data from a single database."""
        # Try chat sessions first (most reliable)
        conversations = self.extractor.extract_from_chat_sessions(db_path)

        # Fall back to database key scanning if no chat sessions found
        if not conversations:
            conversations = self.extractor.extract_from_database_keys(db_path)

        return self._create_db_response(conversations, db_path)

    def query_all_conversations(self) -> Dict[str, Any]:
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
        self, query: str, project_root: Optional[Path] = None, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search conversations for specific content."""
        all_data = self.query_all_conversations()
        conversations = all_data.get("conversations", [])

        return self._search_in_conversations(conversations, query, limit)

    def _find_workspace_databases(self) -> List[Path]:
        """Find all workspace and global database files."""
        databases = []

        # Search workspace storage
        if self.workspace_storage.exists():
            try:
                for workspace_dir in self.workspace_storage.iterdir():
                    if workspace_dir.is_dir():
                        db_file = workspace_dir / "state.vscdb"
                        if db_file.exists():
                            databases.append(db_file)
            except (OSError, PermissionError) as e:
                if not self.silent:
                    log_error(
                        e,
                        f"scanning Windsurf workspace storage {self.workspace_storage}",
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
        self, conversations: List[Dict[str, Any]], db_path: Path
    ) -> Dict[str, Any]:
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
        self, conversations: List[Dict[str, Any]], query: str, limit: int
    ) -> List[Dict[str, Any]]:
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
        self, conv: Dict[str, Any], query_lower: str
    ) -> List[Dict[str, str]]:
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
    ) -> List[Dict[str, str]]:
        """Search for query in a specific field."""
        matches = []

        if isinstance(field_value, str) and query_lower in field_value.lower():
            matches.append(
                {
                    "type": field_name,
                    "content": self._truncate_content(field_value, 200),
                }
            )
        elif isinstance(field_value, (list, dict)):
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


def handle_query_windsurf_conversations(
    arguments: Dict[str, Any], project_root: Path, **kwargs
) -> Dict[str, Any]:
    """Query Windsurf conversations with comprehensive data retrieval."""
    try:
        # Extract and validate parameters
        format_type = arguments.get("format", "json")
        limit = arguments.get("limit", 50)

        if format_type not in ["json", "markdown", "windsurf"]:
            return AccessValidator.create_error_response(
                "format must be one of: json, markdown, windsurf"
            )

        # Query conversations
        query_tool = WindsurfQuery(silent=True)
        data = query_tool.query_all_conversations()

        # Apply limit
        conversations = data.get("conversations", [])
        if limit and len(conversations) > limit:
            conversations = conversations[:limit]
            data["conversations"] = conversations
            data["limited_results"] = True
            data["limit_applied"] = limit

        # Format response
        response_data = _format_response(data, format_type)
        return AccessValidator.create_success_response(response_data)

    except (ValueError, KeyError, TypeError) as e:
        log_error(e, "query_windsurf_conversations")
        return AccessValidator.create_error_response(
            f"Error querying Windsurf conversations: {str(e)}"
        )


def _format_response(data: Dict[str, Any], format_type: str) -> str:
    """Format response data according to specified format."""
    conversations = data.get("conversations", [])

    if format_type == "markdown":
        md_lines = [f"# Windsurf Conversations ({len(conversations)} total)"]
        for i, conv in enumerate(conversations, 1):
            md_lines.extend(
                [
                    f"\n## Conversation {i}",
                    f"- **ID**: {conv.get('id', 'Unknown')}",
                    f"- **Workspace**: {conv.get('workspace_id', 'Unknown')}",
                    f"- **Source**: {conv.get('source', 'Unknown')}",
                ]
            )
            if "session_data" in conv:
                session_preview = str(conv["session_data"])[:100] + "..."
                md_lines.append(f"- **Session Data**: {session_preview}")
        return "\n".join(md_lines)

    # Default to JSON for both "json" and "windsurf" formats
    return json.dumps(data, indent=2, default=str)


# Tool definitions
TOOL_QUERY_WINDSURF_CONVERSATIONS = {
    "name": "query_windsurf_conversations",
    "description": "Query conversations directly from Windsurf IDE databases for AI context analysis",
    "inputSchema": {
        "type": "object",
        "properties": {
            "format": {
                "type": "string",
                "enum": ["json", "markdown", "windsurf"],
                "default": "windsurf",
                "description": "Data format for AI analysis",
            },
            "summary": {
                "type": "boolean",
                "default": False,
                "description": "Return summary statistics instead of full conversation data",
            },
            "limit": {
                "type": "integer",
                "default": 50,
                "minimum": 1,
                "maximum": 200,
                "description": "Maximum number of conversations to return",
            },
        },
        "required": [],
    },
    "annotations": {
        "title": "Query Windsurf Conversations",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
}

# Tool handlers and definitions
WINDSURF_QUERY_TOOL_HANDLERS = {
    "query_windsurf_conversations": handle_query_windsurf_conversations,
}

WINDSURF_QUERY_TOOL_DEFINITIONS = [
    TOOL_QUERY_WINDSURF_CONVERSATIONS,
]

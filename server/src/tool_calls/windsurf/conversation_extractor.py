"""
Conversation extraction utilities for Windsurf IDE conversations.

This module extracts and structures conversation data from various sources
including chat sessions and database keys.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.utils.common import log_debug

if TYPE_CHECKING:
    from src.tool_calls.windsurf.database_reader import DatabaseReader
    from src.tool_calls.windsurf.query_validator import ConversationValidator
    from src.tool_calls.windsurf.windsurf_query import WindsurfQuery


class ConversationExtractor:
    """Extracts and structures conversation data from various sources."""

    def __init__(
        self,
        db_reader: "DatabaseReader",
        validator: "ConversationValidator",
        query_instance: "WindsurfQuery | None" = None,
    ) -> None:
        """Initialize conversation extractor with required components."""
        self.db_reader = db_reader
        self.validator = validator
        self.query_instance = query_instance

    def extract_from_chat_sessions(self, db_path: Path) -> list[dict[str, Any]]:
        """Extract conversations from Windsurf chat session store."""
        if self.query_instance:
            chat_sessions = self.query_instance.get_chat_session_data(db_path)
        else:
            # Fallback: try multiple keys when no query instance available
            from src.config.tool_config import WINDSURF_KEY_CHAT_SESSION_STORE

            chat_sessions = None
            for key in WINDSURF_KEY_CHAT_SESSION_STORE:
                data = self.db_reader.get_data(db_path, key)
                if data and isinstance(data, dict) and data.get("entries"):
                    chat_sessions = data
                    break

        if not chat_sessions or not isinstance(chat_sessions, dict):
            return []

        conversations = []
        entries = chat_sessions.get("entries", {})

        for session_id, session_data in entries.items():
            if isinstance(
                session_data, dict
            ) and self.validator.validate_conversation_data(session_data):
                conversations.append(
                    self._create_conversation_entry(
                        session_id,
                        session_data,
                        "windsurf_chat_session",
                        db_path,
                    )
                )

        return conversations

    def extract_from_database_keys(self, db_path: Path) -> list[dict[str, Any]]:
        """Extract conversations from database keys containing conversation data."""
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

    def extract_all_conversations(self, db_path: Path) -> list[dict[str, Any]]:
        """Extract all conversations using multiple strategies."""
        all_conversations = []

        # Try chat sessions first (most reliable)
        chat_conversations = self.extract_from_chat_sessions(db_path)
        all_conversations.extend(chat_conversations)

        # Fall back to database key scanning if no chat sessions found
        if not chat_conversations:
            key_conversations = self.extract_from_database_keys(db_path)
            all_conversations.extend(key_conversations)

        return all_conversations

    def _extract_from_data_structure(
        self, key: str, data: Any, db_path: Path
    ) -> list[dict[str, Any]]:
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
        self, key: str, data: dict[str, Any], db_path: Path
    ) -> list[dict[str, Any]]:
        """Extract conversations from dictionary data."""
        conversations = []

        # Check for entries pattern
        if "entries" in data and isinstance(data["entries"], dict) and data["entries"]:
            for entry_id, entry_data in data["entries"].items():
                if isinstance(
                    entry_data, dict
                ) and self.validator.validate_conversation_data(entry_data):
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
        elif self.validator.validate_conversation_data(data):
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
                if isinstance(
                    sub_value, list
                ) and self.validator.validate_conversation_data(sub_value):
                    # Extract individual conversations from the list
                    conversations.extend(
                        self._extract_from_list(f"{key}_{sub_key}", sub_value, db_path)
                    )
                elif isinstance(
                    sub_value, dict
                ) and self.validator.validate_conversation_data(sub_value):
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
        self, key: str, data: list[Any], db_path: Path
    ) -> list[dict[str, Any]]:
        """Extract conversations from list data."""
        conversations = []

        for i, item in enumerate(data):
            if isinstance(item, dict) and self.validator.validate_conversation_data(
                item
            ):
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
        self, conv_id: str, data: Any, source: str, db_path: Path, **kwargs: Any
    ) -> dict[str, Any]:
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

    def get_extraction_stats(self, db_path: Path) -> dict[str, Any]:
        """Get statistics about conversation extraction for a database."""
        stats = {
            "database_path": str(db_path),
            "chat_session_conversations": 0,
            "key_based_conversations": 0,
            "total_conversations": 0,
            "conversation_keys_found": 0,
            "has_chat_sessions": False,
        }

        try:
            # Check chat sessions
            chat_conversations = self.extract_from_chat_sessions(db_path)
            stats["chat_session_conversations"] = len(chat_conversations)
            stats["has_chat_sessions"] = len(chat_conversations) > 0

            # Check key-based extraction
            key_conversations = self.extract_from_database_keys(db_path)
            stats["key_based_conversations"] = len(key_conversations)
            stats["conversation_keys_found"] = len(
                self.db_reader.find_conversation_keys(db_path)
            )

            # Total (avoid double counting if using fallback strategy)
            if stats["has_chat_sessions"]:
                stats["total_conversations"] = stats["chat_session_conversations"]
            else:
                stats["total_conversations"] = stats["key_based_conversations"]

        except Exception as e:
            # Log extraction errors for debugging but don't fail stats collection
            log_debug(f"Error collecting extraction stats for {db_path}: {e}")

        return stats

    def validate_extraction_quality(
        self, conversations: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Validate the quality of extracted conversations."""
        quality_stats: dict[str, Any] = {
            "total_conversations": len(conversations),
            "valid_conversations": 0,
            "conversations_with_messages": 0,
            "conversations_with_metadata": 0,
            "average_data_size": 0,
            "sources": {},
        }

        total_data_size = 0

        for conv in conversations:
            # Check basic validity
            if "data" in conv and conv["data"]:
                quality_stats["valid_conversations"] += 1

                data_size = len(str(conv["data"]))
                total_data_size += data_size

                # Check for messages
                if "messages" in conv.get("data", {}) or "messages" in conv.get(
                    "session_data", {}
                ):
                    quality_stats["conversations_with_messages"] += 1

                # Check for metadata (id, title, timestamp, etc.)
                data_dict = (
                    conv.get("data", {}) if isinstance(conv.get("data"), dict) else {}
                )
                session_dict = (
                    conv.get("session_data", {})
                    if isinstance(conv.get("session_data"), dict)
                    else {}
                )
                combined_data = {**data_dict, **session_dict}

                metadata_fields = [
                    "id",
                    "title",
                    "name",
                    "timestamp",
                    "created_at",
                    "updated_at",
                ]
                if any(field in combined_data for field in metadata_fields):
                    quality_stats["conversations_with_metadata"] += 1

            # Track sources
            source = conv.get("source", "unknown")
            quality_stats["sources"][source] = (
                quality_stats["sources"].get(source, 0) + 1
            )

        # Calculate averages
        if quality_stats["total_conversations"] > 0:
            quality_stats["average_data_size"] = (
                total_data_size // quality_stats["total_conversations"]
            )

        return quality_stats

"""Conversation processing for all agentic tools."""

from dataclasses import dataclass
from typing import Any, Literal

from src.config.conversation_config import TOKEN_OPTIMIZATION_MAX_CONTEXT_KEYWORDS
from src.utils.common import log_error


@dataclass(frozen=True)
class ConversationStandardizer:
    """Conversation processing for all agentic tools."""

    tool_name: Literal["cursor", "claude-code", "windsurf"]

    def standardize_conversation(
        self,
        conversation: dict[str, Any],
        context_keywords: list[str],
        lightweight: bool = False,
    ) -> dict[str, Any]:
        """Standardize conversation format across all tools."""
        try:
            if lightweight:
                return self._create_lightweight_conversation(conversation)

            return self._create_full_conversation(conversation, context_keywords)

        except (ValueError, TypeError, KeyError, AttributeError, OSError) as e:
            log_error(e, f"standardizing {self.tool_name} conversation")
            return {}

    def _create_lightweight_conversation(
        self, conversation: dict[str, Any]
    ) -> dict[str, Any]:
        """Create lightweight conversation format for token optimization."""
        # Get ID with tool-specific fallbacks
        conv_id = self._extract_conversation_id(conversation)

        # Get title with tool-specific defaults
        title = self._extract_conversation_title(conversation)

        return {
            "id": conv_id,
            "title": title,
            "source_tool": self.tool_name,
            "timestamp": conversation.get(
                "timestamp", conversation.get("created_at", "")
            ),
            "relevance_score": conversation.get("relevance_score", 0.0),
            "message_count": self._extract_message_count(conversation),
        }

    def _create_full_conversation(
        self, conversation: dict[str, Any], context_keywords: list[str]
    ) -> dict[str, Any]:
        """Create full conversation format with all standardized fields."""

        # Helper for text truncation
        def _truncate_string_field(text: str, limit: int = 500) -> str:
            """Truncate string field with ellipsis if needed."""
            if not text or len(text) <= limit:
                return text
            return text[:limit] + "..."

        # Extract core fields using tool-specific logic
        conv_id = self._extract_conversation_id(conversation)
        title = self._extract_conversation_title(conversation)
        created_at = self._extract_created_at(conversation)
        updated_at = self._extract_updated_at(conversation)
        message_count = self._extract_message_count(conversation)

        # Build standardized base structure
        standardized = {
            "id": str(conv_id),
            "title": _truncate_string_field(str(title)),
            "source_tool": self.tool_name,
            "created_at": str(created_at),
            "updated_at": str(updated_at),
            "message_count": message_count,
            "relevance_score": round(conversation.get("relevance_score", 0.0), 2),
            "snippet": _truncate_string_field(conversation.get("snippet", "")),
        }

        # Add tool-specific fields
        tool_specific_fields = self._get_tool_specific_fields(conversation)
        standardized.update(tool_specific_fields)

        # Add truncated context keywords
        standardized["context_keywords"] = context_keywords[
            :TOKEN_OPTIMIZATION_MAX_CONTEXT_KEYWORDS
        ]
        standardized["keyword_matches"] = conversation.get("keyword_matches", [])

        return standardized

    def _extract_conversation_id(self, conversation: dict[str, Any]) -> str:
        """Extract conversation ID with tool-specific fallbacks."""
        if self.tool_name == "cursor":
            return str(
                conversation.get("id")
                or conversation.get("conversation_id")
                or conversation.get("uuid")
                or ""
            )
        elif self.tool_name == "claude-code":
            return str(conversation.get("id") or conversation.get("session_id") or "")
        else:  # windsurf
            return str(
                conversation.get("id") or conversation.get("chat_session_id") or ""
            )

    def _extract_conversation_title(self, conversation: dict[str, Any]) -> str:
        """Extract conversation title with tool-specific defaults."""
        if self.tool_name == "cursor":
            return str(
                conversation.get("title")
                or conversation.get("name")
                or conversation.get("subject")
                or "Untitled Conversation"
            )
        elif self.tool_name == "claude-code":
            return str(
                conversation.get("title")
                or conversation.get("summary")
                or "Claude Code Session"
            )
        else:  # windsurf
            conv_id = conversation.get("id", "Unknown")
            title = conversation.get("title")
            if title:
                return str(title)
            return f"Windsurf Chat {str(conv_id)[:8]}"

    def _extract_created_at(self, conversation: dict[str, Any]) -> str:
        """Extract created timestamp with tool-specific field names."""
        return str(
            conversation.get("created_at")
            or conversation.get("timestamp")
            or conversation.get("date_created")
            or conversation.get("start_time")
            or ""
        )

    def _extract_updated_at(self, conversation: dict[str, Any]) -> str:
        """Extract updated timestamp with tool-specific field names."""
        return str(
            conversation.get("updated_at")
            or conversation.get("last_updated")
            or conversation.get("modified_at")
            or conversation.get("last_modified")
            or ""
        )

    def _extract_message_count(self, conversation: dict[str, Any]) -> int:
        """Extract message count with tool-specific logic."""
        # Use explicit message_count if available
        if "message_count" in conversation:
            return int(conversation["message_count"])

        # Calculate from messages array if available
        messages = conversation.get("messages", [])
        if isinstance(messages, list):
            return len(messages)

        # Default to 1 for windsurf, 0 for others
        return 1 if self.tool_name == "windsurf" else 0

    def _get_tool_specific_fields(self, conversation: dict[str, Any]) -> dict[str, Any]:
        """Get tool-specific fields that should be preserved."""
        if self.tool_name == "cursor":
            return {
                "workspace_id": str(
                    conversation.get("workspace_id")
                    or conversation.get("workspace_hash")
                    or conversation.get("project_id")
                    or ""
                ),
                "messages": conversation.get("messages", []),
                "conversation_type": conversation.get("conversation_type", ""),
                "ai_model": conversation.get("ai_model", ""),
                "user_query": conversation.get("user_query", ""),
                "ai_response": conversation.get("ai_response", ""),
                "file_references": conversation.get("file_references", []),
                "code_blocks": conversation.get("code_blocks", []),
                "metadata": conversation.get("metadata", {}),
            }
        elif self.tool_name == "claude-code":
            return {
                "session_id": conversation.get("session_id", ""),
                "project_context": conversation.get("project_context", {}),
                "conversation_context": conversation.get("context", {}),
                "messages": conversation.get("messages", []),
                "session_metadata": conversation.get("metadata", {}),
                "analysis_results": conversation.get("analysis", {}),
                "tool_usage": conversation.get("tool_usage", []),
                "project_files": conversation.get("project_files", []),
                "working_directory": conversation.get("working_directory", ""),
                "file_references": conversation.get("file_references", []),
                "conversation_type": conversation.get("conversation_type", ""),
            }
        else:  # windsurf
            return {
                "workspace_id": conversation.get("workspace_id", ""),
                "database_path": conversation.get("database_path", ""),
                "session_data": conversation.get("session_data", {}),
                "windsurf_source": conversation.get(
                    "windsurf_source", conversation.get("source", "")
                ),
                "chat_session_id": conversation.get(
                    "chat_session_id", conversation.get("id", "")
                ),
                "windsurf_metadata": conversation.get(
                    "windsurf_metadata", conversation.get("metadata", {})
                ),
            }

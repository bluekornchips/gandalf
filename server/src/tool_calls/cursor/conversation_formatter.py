"""
Conversation formatting utilities for Cursor IDE conversations.

This module handles the formatting and presentation of conversation data
for output to MCP clients.
"""

from typing import Any

from src.config.constants.conversation import (
    CONVERSATION_ID_DISPLAY_LIMIT,
    CONVERSATION_SNIPPET_DISPLAY_LIMIT,
    CONVERSATION_TITLE_DISPLAY_LIMIT,
)


def create_lightweight_conversation(
    conversation: dict[str, Any],
) -> dict[str, Any]:
    """Create lightweight conversation format for Cursor."""
    conv_id = conversation.get("id", conversation.get("conversation_id", ""))
    title = conversation.get("title", conversation.get("name", ""))
    created_at = conversation.get("created_at", "")
    snippet = conversation.get("snippet", "")

    return {
        "id": conv_id[:CONVERSATION_ID_DISPLAY_LIMIT],
        "title": (
            title[:CONVERSATION_TITLE_DISPLAY_LIMIT] + "..."
            if len(title) > CONVERSATION_TITLE_DISPLAY_LIMIT
            else title
        ),
        "source_tool": "cursor",
        "message_count": conversation.get("message_count", 0),
        "relevance_score": round(conversation.get("relevance_score", 0.0), 2),
        "created_at": created_at,
        "snippet": (
            snippet[:CONVERSATION_SNIPPET_DISPLAY_LIMIT] + "..."
            if len(snippet) > CONVERSATION_SNIPPET_DISPLAY_LIMIT
            else snippet
        ),
    }


def standardize_conversation(
    conversation: dict[str, Any],
    context_keywords: list[str],
    lightweight: bool = False,
) -> dict[str, Any]:
    """Standardize conversation format across different tools."""
    try:
        if lightweight:
            return create_lightweight_conversation(conversation)

        # Handle different ID field names
        conv_id = (
            conversation.get("id")
            or conversation.get("conversation_id")
            or conversation.get("uuid")
            or ""
        )

        # Handle different title field names
        title = (
            conversation.get("title")
            or conversation.get("name")
            or conversation.get("subject")
            or "Untitled Conversation"
        )

        # Handle different timestamp formats
        created_at = (
            conversation.get("created_at")
            or conversation.get("timestamp")
            or conversation.get("date_created")
            or ""
        )

        # use existing field or calculate from messages
        messages = conversation.get("messages", [])
        message_count = (
            conversation.get("message_count", 0)
            if "message_count" in conversation
            else len(messages)
            if isinstance(messages, list)
            else 0
        )

        # Get relevance score if available, set default above minimum threshold
        relevance_score = conversation.get("relevance_score", 1.25)

        # Get snippet if available
        snippet = conversation.get("snippet", "")

        from src.config.constants.context import TOKEN_OPTIMIZATION_MAX_CONTEXT_KEYWORDS

        # Handle updated_at field
        updated_at = (
            conversation.get("updated_at")
            or conversation.get("last_updated")
            or conversation.get("modified_at")
            or ""
        )

        workspace_id = (
            conversation.get("workspace_id")
            or conversation.get("workspace_hash")
            or conversation.get("project_id")
            or ""
        )

        standardized = {
            "id": str(conv_id),
            "title": str(title),
            "source_tool": "cursor",
            "message_count": message_count,
            "relevance_score": round(float(relevance_score), 2),
            "created_at": str(created_at),
            "updated_at": str(updated_at),
            "workspace_id": str(workspace_id),
            "snippet": str(snippet),
            "messages": messages,  # Keep original messages for full access
            # Cursor-specific fields
            "conversation_type": conversation.get("conversation_type", ""),
            "ai_model": conversation.get("ai_model", ""),
            "user_query": conversation.get("user_query", ""),
            "ai_response": conversation.get("ai_response", ""),
            "file_references": conversation.get("file_references", []),
            "code_blocks": conversation.get("code_blocks", []),
            "metadata": conversation.get("metadata", {}),
            "keyword_matches": conversation.get("keyword_matches", []),
        }

        # Add truncated context keywords
        standardized["context_keywords"] = context_keywords[
            :TOKEN_OPTIMIZATION_MAX_CONTEXT_KEYWORDS
        ]

        return standardized

    except Exception as e:
        from src.utils.common import log_error

        log_error(e, "standardizing cursor conversation")
        return {}


def format_conversation_summary(
    conversations: list[dict[str, Any]],
    total_found: int,
    processing_stats: dict[str, Any],
) -> dict[str, Any]:
    """Format conversation summary for output."""
    return {
        "summary": {
            "total_conversations_found": total_found,
            "conversations_returned": len(conversations),
            "success_rate_percent": round(
                len(conversations) / total_found * 100 if total_found > 0 else 0,
                1,
            ),
            **processing_stats,
        },
        "conversations": conversations,
    }


def format_lightweight_conversations(
    analyzed_conversations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Format conversations into lightweight format."""
    lightweight_conversations = []

    for analyzed in analyzed_conversations:
        conversation = analyzed.get("conversation", analyzed)

        # Create lightweight format
        lightweight = create_lightweight_conversation(conversation)

        # Add analysis scores if available
        if "relevance_score" in analyzed:
            lightweight["relevance_score"] = round(analyzed["relevance_score"], 2)
        if "message_count" in analyzed:
            lightweight["message_count"] = analyzed["message_count"]

        lightweight_conversations.append(lightweight)

    return lightweight_conversations


def truncate_text_fields(
    conversation: dict[str, Any],
    max_title_length: int = CONVERSATION_TITLE_DISPLAY_LIMIT,
    max_snippet_length: int = CONVERSATION_SNIPPET_DISPLAY_LIMIT,
) -> dict[str, Any]:
    """Truncate text fields to specified lengths."""
    result = conversation.copy()

    # Truncate title
    if "title" in result and len(result["title"]) > max_title_length:
        result["title"] = result["title"][:max_title_length] + "..."

    # Truncate snippet
    if "snippet" in result and len(result["snippet"]) > max_snippet_length:
        result["snippet"] = result["snippet"][:max_snippet_length] + "..."

    return result

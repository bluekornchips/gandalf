"""
Enhanced conversation recall and analysis for Gandalf MCP server.

This module provides intelligent conversation recall capabilities for Cursor
IDE, using modular components for better maintainability.
"""

from pathlib import Path
from typing import Any

from src.config.config_data import CONVERSATION_TYPES
from src.config.constants.conversation import (
    CONVERSATION_DEFAULT_LIMIT,
    CONVERSATION_DEFAULT_LOOKBACK_DAYS,
    CONVERSATION_DEFAULT_MIN_SCORE,
    CONVERSATION_MAX_LIMIT,
    CONVERSATION_MAX_LOOKBACK_DAYS,
)
from src.tool_calls.cursor.conversation_parser import (
    handle_enhanced_mode,
    handle_fast_mode,
    query_and_analyze_conversations,
)
from src.utils.access_control import AccessValidator
from src.utils.common import log_error


def handle_recall_cursor_conversations(
    arguments: dict[str, Any], project_root: Path, **kwargs: Any
) -> dict[str, Any]:
    """Recall and analyze relevant conversations with intelligent caching."""
    try:
        # Get argument values
        limit = arguments.get("limit", CONVERSATION_DEFAULT_LIMIT)
        min_relevance_score = arguments.get(
            "min_relevance_score", CONVERSATION_DEFAULT_MIN_SCORE
        )
        days_lookback = arguments.get(
            "days_lookback", CONVERSATION_DEFAULT_LOOKBACK_DAYS
        )
        conversation_types = arguments.get("conversation_types", [])
        include_analysis = arguments.get("include_analysis", False)
        fast_mode = arguments.get("fast_mode", True)

        # Validate and clamp parameters to valid ranges
        limit = max(1, min(int(limit), CONVERSATION_MAX_LIMIT))
        min_relevance_score = max(0.0, float(min_relevance_score))
        days_lookback = max(1, min(int(days_lookback), CONVERSATION_MAX_LOOKBACK_DAYS))

        if not isinstance(conversation_types, list):
            conversation_types = []

        # Fast mode: Skip expensive operations for speed
        if fast_mode:
            return handle_fast_mode(limit, days_lookback, conversation_types)

        # Enhanced mode: Use caching and context analysis
        return handle_enhanced_mode(
            project_root,
            limit,
            min_relevance_score,
            days_lookback,
            conversation_types,
            include_analysis,
            query_and_analyze_conversations,
        )

    except (ValueError, TypeError, KeyError, AttributeError, OSError) as e:
        log_error(e, "recall_cursor_conversations")
        return AccessValidator.create_error_response(
            f"Error recalling conversations: {str(e)}"
        )


# Tool definitions
TOOL_RECALL_CURSOR_CONVERSATIONS = {
    "name": "recall_cursor_conversations",
    "description": "Recall and analyze relevant conversations from Cursor IDE "
    "history with intelligent caching. Defaults to recent 7 days for "
    "focused relevance.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": CONVERSATION_MAX_LIMIT,
                "default": CONVERSATION_DEFAULT_LIMIT,
                "description": "Maximum number of conversations to return",
            },
            "min_relevance_score": {
                "type": "number",
                "minimum": 0,
                "default": CONVERSATION_DEFAULT_MIN_SCORE,
                "description": "Minimum relevance score threshold (only used when fast_mode=false)",
            },
            "days_lookback": {
                "type": "integer",
                "minimum": 1,
                "maximum": CONVERSATION_MAX_LOOKBACK_DAYS,
                "default": CONVERSATION_DEFAULT_LOOKBACK_DAYS,
                "description": "Number of days to look back for conversations (default: 7 days for recent focus)",
            },
            "conversation_types": {
                "type": "array",
                "items": {"type": "string", "enum": CONVERSATION_TYPES},
                "description": "Filter by conversation types (only used when fast_mode=false)",
            },
            "include_analysis": {
                "type": "boolean",
                "default": False,
                "description": "Include detailed relevance analysis (only used when fast_mode=false)",
            },
            "fast_mode": {
                "type": "boolean",
                "default": True,
                "description": "Use fast extraction (seconds) vs full analysis (minutes). Recommended: true",
            },
        },
        "required": [],
    },
    "annotations": {
        "title": "Recall Relevant Conversations with Smart Caching",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
}

CONVERSATION_RECALL_TOOL_HANDLERS = {
    "recall_cursor_conversations": handle_recall_cursor_conversations,
}

CONVERSATION_RECALL_TOOL_DEFINITIONS = [
    TOOL_RECALL_CURSOR_CONVERSATIONS,
]

"""
Enhanced conversation recall and analysis for Gandalf MCP server.

This module provides intelligent conversation recall capabilities for Cursor
IDE, using modular components for better maintainability.
"""

from pathlib import Path
from typing import Any

from src.config.config_data import CONVERSATION_TYPES
from src.config.conversation_config import (
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
from src.utils.error_handling import handle_tool_errors
from src.utils.parameter_validator import ParameterValidator


@handle_tool_errors("cursor_conversation_recall")
def handle_recall_cursor_conversations(
    arguments: dict[str, Any], project_root: Path, **kwargs: Any
) -> dict[str, Any]:
    """Recall and analyze relevant conversations with intelligent caching."""
    # Validate and normalize parameters using shared utility
    params = ParameterValidator.validate_conversation_params(arguments)

    if params.fast_mode:
        return handle_fast_mode(
            params.limit, params.days_lookback, params.conversation_types or []
        )

    return handle_enhanced_mode(
        project_root,
        params.limit,
        params.min_relevance_score,
        params.days_lookback,
        params.conversation_types or [],
        params.include_analysis,
        query_and_analyze_conversations,
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

"""
Claude Code conversation recall functionality for Gandalf MCP Server.

This module provides conversation recall capabilities for Claude Code,
allowing retrieval and analysis of conversation data from Claude Code sessions.
"""

import json
from pathlib import Path
from typing import Any

from src.config.config_data import (
    CONVERSATION_TYPES,
)
from src.config.constants.context import (
    TOKEN_OPTIMIZATION_MAX_CONTEXT_KEYWORDS,
)
from src.config.constants.conversation import (
    CONVERSATION_DEFAULT_LIMIT,
    CONVERSATION_DEFAULT_LOOKBACK_DAYS,
    CONVERSATION_DEFAULT_MIN_SCORE,
    CONVERSATION_ID_DISPLAY_LIMIT,
    CONVERSATION_MAX_LIMIT,
    CONVERSATION_MAX_LOOKBACK_DAYS,
    CONVERSATION_SNIPPET_DISPLAY_LIMIT,
    CONVERSATION_TITLE_DISPLAY_LIMIT,
)
from src.core.conversation_analysis import (
    analyze_session_relevance,
    extract_conversation_content,
    filter_conversations_by_date,
    generate_shared_context_keywords,
    sort_conversations_by_relevance,
)
from src.tool_calls.claude_code.query import ClaudeCodeQuery
from src.utils.access_control import AccessValidator
from src.utils.common import log_error, log_info
from src.utils.performance import get_duration, start_timer


def create_lightweight_conversation(
    conversation: dict[str, Any],
) -> dict[str, Any]:
    """Create lightweight conversation format for Claude Code."""
    conv_id = conversation.get("id", conversation.get("session_id", ""))
    title = conversation.get(
        "title", conversation.get("summary", "Claude Code Session")
    )
    created_at = conversation.get("created_at", conversation.get("start_time", ""))
    snippet = conversation.get("snippet", conversation.get("summary", ""))

    return {
        "id": conv_id[:CONVERSATION_ID_DISPLAY_LIMIT],
        "title": (
            title[:CONVERSATION_TITLE_DISPLAY_LIMIT] + "..."
            if len(title) > CONVERSATION_TITLE_DISPLAY_LIMIT
            else title
        ),
        "source_tool": "claude-code",
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
    """Standardize Claude Code conversation format."""
    try:
        # token optimized response
        if lightweight:
            return create_lightweight_conversation(conversation)

        def _truncate_string_field(text: str, limit: int = 500) -> str:
            """Truncate string field with ellipsis if needed."""
            if not text or len(text) <= limit:
                return text
            return text[:limit] + "..."

        standardized = {
            "id": conversation.get("id", conversation.get("session_id", "")),
            "title": _truncate_string_field(
                conversation.get(
                    "title", conversation.get("summary", "Claude Code Session")
                )
            ),
            "source_tool": "claude-code",
            "created_at": conversation.get(
                "created_at", conversation.get("start_time", "")
            ),
            "updated_at": conversation.get(
                "updated_at", conversation.get("last_modified", "")
            ),
            "message_count": conversation.get("message_count", 0),
            "relevance_score": round(conversation.get("relevance_score", 0.0), 2),
            "snippet": _truncate_string_field(
                conversation.get("snippet", conversation.get("summary", ""))
            ),
            "session_id": conversation.get("session_id", ""),
            "project_context": conversation.get("project_context", {}),
            "conversation_context": conversation.get("context", {}),
            "messages": conversation.get("messages", []),
            "session_metadata": conversation.get("metadata", {}),
            "analysis_results": conversation.get("analysis", {}),
            "tool_usage": conversation.get("tool_usage", []),
            "project_files": conversation.get("project_files", []),
            "working_directory": conversation.get("working_directory", ""),
            "keyword_matches": conversation.get("keyword_matches", []),
            "file_references": conversation.get("file_references", []),
            "conversation_type": conversation.get("conversation_type", ""),
        }

        standardized["context_keywords"] = context_keywords[
            :TOKEN_OPTIMIZATION_MAX_CONTEXT_KEYWORDS
        ]
        standardized["keyword_matches"] = conversation.get("keyword_matches", [])

        return standardized

    except (ValueError, TypeError, KeyError, AttributeError, OSError) as e:
        log_error(e, "standardizing claude-code conversation")
        return {}


def handle_recall_claude_conversations(
    arguments: dict[str, Any], project_root: Path, **kwargs
) -> dict[str, Any]:
    """Recall and analyze Claude Code conversations for context."""
    try:
        # Get parameters
        fast_mode = arguments.get("fast_mode", True)
        days_lookback = arguments.get(
            "days_lookback", CONVERSATION_DEFAULT_LOOKBACK_DAYS
        )
        limit = min(
            arguments.get("limit", CONVERSATION_DEFAULT_LIMIT),
            CONVERSATION_MAX_LIMIT,
        )
        conversation_types = arguments.get("conversation_types", [])
        min_score = arguments.get("min_score", CONVERSATION_DEFAULT_MIN_SCORE)

        # Validate parameters
        days_lookback = min(days_lookback, CONVERSATION_MAX_LOOKBACK_DAYS)

        timer = start_timer()

        # Generate context keywords using shared functionality
        context_keywords = generate_shared_context_keywords(project_root)
        log_info(f"Generated {len(context_keywords)} context keywords")

        # Initialize query tool
        query_tool = ClaudeCodeQuery(silent=True)

        # Get conversations.
        # Claude Code needs to use project root
        log_info("Querying Claude Code conversations...")
        data = query_tool.query_conversations(
            project_root, limit=limit * 2
        )  # Get more for filtering

        if not data.get("conversations"):
            return AccessValidator.create_success_response(
                json.dumps(
                    {
                        "conversations": [],
                        "total_conversations": 0,
                        "total_analyzed": 0,
                        "context_keywords": context_keywords,
                        "processing_time": get_duration(timer),
                        "fast_mode": fast_mode,
                    },
                    indent=2,
                )
            )

        # Filter by date using shared functionality
        filtered_conversations = filter_conversations_by_date(
            data["conversations"], days_lookback
        )

        # Analyze and score conversations
        analyzed_conversations = []
        for conv in filtered_conversations:
            # Extract content using shared functionality
            content = extract_conversation_content(conv)

            # Analyze relevance using shared functionality
            score, analysis = analyze_session_relevance(
                content,
                context_keywords,
                conv.get("session_metadata", {}),
                include_detailed_analysis=not fast_mode,
            )

            if score >= min_score:
                # Filter by conversation type if specified
                if (
                    not conversation_types
                    or analysis["conversation_type"] in conversation_types
                ):
                    analyzed_conversations.append(
                        {
                            "session_data": conv,
                            "relevance_score": score,
                            "analysis": analysis,
                        }
                    )

        # Sort by relevance score using shared functionality
        analyzed_conversations = sort_conversations_by_relevance(
            analyzed_conversations, "relevance_score"
        )
        analyzed_conversations = analyzed_conversations[:limit]

        # Format response
        response_conversations = []
        for item in analyzed_conversations:
            conv = item["session_data"]
            analysis = item["analysis"]
            session_meta = conv.get("session_metadata", {})

            # Create conversation summary
            messages = conv.get("messages", [])
            first_message = messages[0] if messages else {}
            first_content = first_message.get("content", "")

            if isinstance(first_content, list):
                first_text = ""
                for content_item in first_content:
                    if (
                        isinstance(content_item, dict)
                        and content_item.get("type") == "text"
                    ):
                        first_text = content_item.get("text", "")
                        break
                first_content = first_text

            summary = (
                str(first_content)[:200] + "..."
                if len(str(first_content)) > 200
                else str(first_content)
            )

            response_conversations.append(
                {
                    # Standardized fields for aggregator
                    "id": session_meta.get("session_id", "Unknown"),
                    "title": summary,
                    "created_at": session_meta.get("start_time", "Unknown"),
                    "updated_at": conv.get("last_modified", "Unknown"),
                    "snippet": summary,
                    "message_count": len(messages),
                    "relevance_score": round(item["relevance_score"], 2),
                    # Tool-specific fields
                    "session_id": session_meta.get("session_id", "Unknown"),
                    "start_time": session_meta.get("start_time", "Unknown"),
                    "working_directory": session_meta.get("cwd", "Unknown"),
                    "conversation_type": analysis["conversation_type"],
                    "summary": summary,
                    "keyword_matches": analysis["keyword_matches"],
                    "file_references": analysis["file_references"],
                    "last_modified": conv.get("last_modified", "Unknown"),
                }
            )

        processing_time = get_duration(timer)

        result = {
            "conversations": response_conversations,
            "total_conversations": len(response_conversations),
            "total_analyzed": len(filtered_conversations),
            "total_returned": len(response_conversations),
            "context_keywords": context_keywords,
            "processing_time": processing_time,
            "fast_mode": fast_mode,
            "days_lookback": days_lookback,
            "min_score": min_score,
            "claude_home": data.get("claude_home"),
        }

        log_info(
            f"Recalled {len(response_conversations)} relevant conversations "
            f"in {processing_time:.2f}s"
        )
        return AccessValidator.create_success_response(json.dumps(result, indent=2))

    except (ValueError, TypeError, KeyError, AttributeError, OSError) as e:
        log_error(e, "recall_claude_conversations")
        return AccessValidator.create_error_response(
            f"Error recalling Claude Code conversations: {str(e)}"
        )


# Tool definitions
TOOL_RECALL_CLAUDE_CONVERSATIONS = {
    "name": "recall_claude_conversations",
    "description": (
        "Recall and analyze Claude Code conversations for relevant context"
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "fast_mode": {
                "type": "boolean",
                "default": True,
                "description": "Use fast mode for quicker context gathering",
            },
            "days_lookback": {
                "type": "integer",
                "default": CONVERSATION_DEFAULT_LOOKBACK_DAYS,
                "minimum": 1,
                "maximum": CONVERSATION_MAX_LOOKBACK_DAYS,
                "description": "Number of days to look back for conversations",
            },
            "limit": {
                "type": "integer",
                "default": CONVERSATION_DEFAULT_LIMIT,
                "minimum": 1,
                "maximum": CONVERSATION_MAX_LIMIT,
                "description": "Maximum number of conversations to return",
            },
            "conversation_types": {
                "type": "array",
                "items": {"type": "string", "enum": CONVERSATION_TYPES},
                "description": "Filter by conversation types",
            },
            "min_score": {
                "type": "number",
                "default": CONVERSATION_DEFAULT_MIN_SCORE,
                "minimum": 0.0,
                "maximum": 5.0,
                "description": "Minimum relevance score threshold",
            },
        },
        "required": [],
    },
    "annotations": {
        "title": "Recall Claude Code Conversations",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
}

# Tool handlers and definitions
CLAUDE_CODE_RECALL_TOOL_HANDLERS = {
    "recall_claude_conversations": handle_recall_claude_conversations,
}

CLAUDE_CODE_RECALL_TOOL_DEFINITIONS = [
    TOOL_RECALL_CLAUDE_CONVERSATIONS,
]

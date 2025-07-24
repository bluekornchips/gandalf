"""
Windsurf conversation recall and analysis.

This module provides intelligent conversation recall capabilities for Windsurf IDE,
using the shared conversation analysis functionality for consistency with Cursor IDE
and Claude Code patterns.
"""

from datetime import datetime
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
    CONVERSATION_SNIPPET_MAX_LENGTH,
    CONVERSATION_TEXT_EXTRACTION_LIMIT,
    CONVERSATION_TITLE_DISPLAY_LIMIT,
)
from src.core.conversation_analysis import (
    analyze_session_relevance,
    extract_conversation_content,
    filter_conversations_by_date,
    generate_shared_context_keywords,
    sort_conversations_by_relevance,
)
from src.tool_calls.windsurf.windsurf_query import WindsurfQuery
from src.utils.access_control import AccessValidator, create_mcp_tool_result
from src.utils.common import format_json_response, log_error, log_info
from src.utils.performance import get_duration, start_timer


def create_lightweight_conversation(
    conversation: dict[str, Any],
) -> dict[str, Any]:
    """Create lightweight conversation format for Windsurf."""
    conv_id = conversation.get("id", conversation.get("chat_session_id", ""))
    title = conversation.get(
        "title", f"Windsurf Chat {conversation.get('id', 'Unknown')[:8]}"
    )
    created_at = conversation.get("created_at", "")
    snippet = conversation.get("snippet", "")

    return {
        "id": conv_id[:CONVERSATION_ID_DISPLAY_LIMIT],
        "title": (
            title[:CONVERSATION_TITLE_DISPLAY_LIMIT] + "..."
            if len(title) > CONVERSATION_TITLE_DISPLAY_LIMIT
            else title
        ),
        "source_tool": "windsurf",
        "message_count": conversation.get("message_count", 1),
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
    """Standardize Windsurf conversation format."""
    try:
        if lightweight:
            return create_lightweight_conversation(conversation)

        def _truncate_string_field(text: str, limit: int = 500) -> str:
            """Truncate string field with ellipsis if needed."""
            if not text or len(text) <= limit:
                return text
            return text[:limit] + "..."

        standardized = {
            "id": conversation.get("id", conversation.get("chat_session_id", "")),
            "title": _truncate_string_field(
                conversation.get(
                    "title",
                    f"Windsurf Chat {conversation.get('id', 'Unknown')[:8]}",
                )
            ),
            "source_tool": "windsurf",
            "created_at": conversation.get("created_at", ""),
            "updated_at": conversation.get("updated_at", ""),
            "message_count": conversation.get("message_count", 1),
            "relevance_score": round(conversation.get("relevance_score", 0.0), 2),
            "snippet": _truncate_string_field(conversation.get("snippet", "")),
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

        standardized["context_keywords"] = context_keywords[
            :TOKEN_OPTIMIZATION_MAX_CONTEXT_KEYWORDS
        ]
        standardized["keyword_matches"] = conversation.get("keyword_matches", [])

        return standardized

    except (ValueError, TypeError, KeyError, AttributeError, OSError) as e:
        log_error(e, "standardizing windsurf conversation")
        return {}


def handle_recall_windsurf_conversations(
    arguments: dict[str, Any], project_root: Path, **kwargs: Any
) -> dict[str, Any]:
    """
    Intelligent conversation recall for Windsurf IDE with relevance analysis.

    This function provides context-aware conversation retrieval that helps maintain
    continuity across development sessions by surfacing the most relevant past discussions.
    """
    start_time = start_timer()

    try:
        # Extract and validate parameters
        fast_mode = arguments.get("fast_mode", True)
        days_lookback = min(
            max(
                arguments.get("days_lookback", CONVERSATION_DEFAULT_LOOKBACK_DAYS),
                1,
            ),
            CONVERSATION_MAX_LOOKBACK_DAYS,
        )
        limit = min(
            max(arguments.get("limit", CONVERSATION_DEFAULT_LIMIT), 1),
            CONVERSATION_MAX_LIMIT,
        )
        min_score = max(arguments.get("min_score", CONVERSATION_DEFAULT_MIN_SCORE), 0.0)
        conversation_types = arguments.get("conversation_types", CONVERSATION_TYPES)

        if not isinstance(conversation_types, list):
            conversation_types = CONVERSATION_TYPES

        log_info(
            f"Windsurf conversation recall: {days_lookback} days, "
            f"limit={limit}, min_score={min_score}, fast_mode={fast_mode}"
        )

        # Initialize query tool and get conversation data
        query_tool = WindsurfQuery(silent=True)
        raw_data = query_tool.query_all_conversations()

        conversations = raw_data.get("conversations", [])
        total_found = len(conversations)

        if not conversations:
            log_info("No Windsurf conversations found")
            response_data = {
                "conversations": [],
                "total_conversations": 0,
                "total_analyzed": 0,
                "parameters": {
                    "days_lookback": days_lookback,
                    "limit": limit,
                    "min_score": min_score,
                    "fast_mode": fast_mode,
                    "conversation_types": conversation_types,
                },
                "processing_time": get_duration(start_time),
                "query_timestamp": datetime.now().isoformat(),
                "fast_mode": fast_mode,
            }

            structured_data = {
                "summary": {
                    "total_conversations": 0,
                    "total_analyzed": 0,
                    "processing_time": get_duration(start_time),
                },
                "conversations": [],
                "context": {
                    "keywords": generate_shared_context_keywords(project_root),
                    "fast_mode": fast_mode,
                    "days_lookback": days_lookback,
                    "min_score": min_score,
                },
                "status": "windsurf_recall_complete",
            }

            content_text = format_json_response(response_data)
            return create_mcp_tool_result(content_text, structured_data)

        # Generate context keywords for relevance analysis
        context_keywords = generate_shared_context_keywords(project_root)

        # Transform conversations to standardized format for analysis
        standardized_conversations = []
        for conv in conversations:
            # Create a standardized conversation format
            standardized_conv = {
                "id": conv.get("id", "unknown"),
                "title": f"Windsurf Chat {conv.get('id', 'Unknown')[:8]}",
                "content": extract_conversation_content(
                    conv, CONVERSATION_TEXT_EXTRACTION_LIMIT
                ),
                "workspace_id": conv.get("workspace_id", "unknown"),
                "source": conv.get("source", "windsurf"),
                "source_tool": "windsurf",  # Set source_tool for aggregation
                "database_path": conv.get("database_path", ""),
                "session_data": conv.get("session_data", {}),
                "created_at": datetime.now().isoformat(),  # Default since Windsurf doesn't expose timestamps yet
                "updated_at": datetime.now().isoformat(),
                "message_count": 1,  # Default since we don't have message counts yet
                "relevance_score": 0.0,  # Will be calculated
                "snippet": "",  # Will be generated
            }

            # Add any additional fields from the original conversation
            for key, value in conv.items():
                if key not in standardized_conv:
                    standardized_conv[key] = value

            standardized_conversations.append(standardized_conv)

        # Filter by date if specified
        if days_lookback > 0:
            filtered_conversations = filter_conversations_by_date(
                standardized_conversations, days_lookback
            )
        else:
            filtered_conversations = standardized_conversations

        # Analyze relevance for each conversation
        analyzed_conversations = []
        for conv in filtered_conversations:
            try:
                # Extract content and use session relevance analysis adapted for Windsurf
                content = extract_conversation_content(
                    conv, CONVERSATION_TEXT_EXTRACTION_LIMIT
                )

                # Create session metadata including conversation ID for analysis
                session_metadata = conv.get("session_data", {}).copy()
                session_metadata["id"] = conv.get("id", "")

                score, analysis = analyze_session_relevance(
                    content,
                    context_keywords,
                    session_metadata,
                    include_detailed_analysis=not fast_mode,
                )

                # Update conversation with relevance data
                conv["relevance_score"] = score
                conv["snippet"] = (
                    content[:CONVERSATION_SNIPPET_MAX_LENGTH] if content else ""
                )
                conv["keyword_matches"] = analysis.get("keyword_matches", [])
                conv["context_analysis"] = analysis

                # Only include conversations that meet minimum score
                if conv["relevance_score"] >= min_score or conv["relevance_score"] == 0:
                    analyzed_conversations.append(conv)

            except (
                ValueError,
                TypeError,
                KeyError,
                AttributeError,
                OSError,
            ) as e:
                log_error(
                    e,
                    f"analyzing Windsurf conversation {conv.get('id', 'unknown')}",
                )
                # Include conversation with default score if analysis fails
                conv["relevance_score"] = 1.0
                conv["snippet"] = conv.get("content", "")[
                    :CONVERSATION_SNIPPET_MAX_LENGTH
                ]
                analyzed_conversations.append(conv)

        # Sort by relevance and apply limit
        sorted_conversations = sort_conversations_by_relevance(analyzed_conversations)
        final_conversations = sorted_conversations[:limit]

        # Prepare response data
        response_data = {
            "conversations": final_conversations,
            "total_conversations": len(final_conversations),
            "total_analyzed": total_found,
            "total_filtered": len(filtered_conversations),
            "total_after_relevance": len(analyzed_conversations),
            "context_keywords": context_keywords,
            "parameters": {
                "days_lookback": days_lookback,
                "limit": limit,
                "min_score": min_score,
                "fast_mode": fast_mode,
                "conversation_types": conversation_types,
            },
            "processing_time": get_duration(start_time),
            "query_timestamp": datetime.now().isoformat(),
        }

        log_info(
            f"Windsurf recall completed: {len(final_conversations)} conversations "
            f"(analyzed {total_found}, filtered {len(filtered_conversations)}) "
            f"in {get_duration(start_time):.3f}s"
        )

        final_structured_data: dict[str, Any] = {
            "summary": {
                "total_conversations": len(final_conversations),
                "total_analyzed": total_found,
                "processing_time": get_duration(start_time),
            },
            "conversations": final_conversations,
            "context": {
                "keywords": context_keywords,
                "fast_mode": fast_mode,
                "days_lookback": days_lookback,
                "min_score": min_score,
            },
            "status": "windsurf_recall_complete",
        }

        content_text = format_json_response(response_data)
        return create_mcp_tool_result(content_text, final_structured_data)

    except (ValueError, TypeError, KeyError, AttributeError, OSError) as e:
        log_error(e, "handle_recall_windsurf_conversations")
        return AccessValidator.create_error_response(
            f"Error recalling Windsurf conversations: {str(e)}"
        )


# Tool definition
TOOL_RECALL_WINDSURF_CONVERSATIONS = {
    "name": "recall_windsurf_conversations",
    "description": "Intelligent conversation recall for Windsurf IDE with "
    "relevance analysis and context awareness",
    "inputSchema": {
        "type": "object",
        "properties": {
            "fast_mode": {
                "type": "boolean",
                "default": True,
                "description": "Use fast extraction vs comprehensive analysis",
            },
            "days_lookback": {
                "type": "integer",
                "minimum": 1,
                "maximum": 60,
                "default": 7,
                "description": "Number of days to look back for conversations",
            },
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 100,
                "default": 20,
                "description": "Maximum number of conversations to return",
            },
            "min_score": {
                "type": "number",
                "minimum": 0,
                "default": 2.0,
                "description": "Minimum relevance score threshold",
            },
            "conversation_types": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [
                        "architecture",
                        "debugging",
                        "problem_solving",
                        "technical",
                        "code_discussion",
                        "general",
                    ],
                },
                "description": "Filter by conversation types",
            },
        },
        "required": [],
    },
    "annotations": {
        "title": "Recall Windsurf Conversations",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
}

# Tool handlers and definitions
WINDSURF_RECALL_TOOL_HANDLERS = {
    "recall_windsurf_conversations": handle_recall_windsurf_conversations,
}

WINDSURF_RECALL_TOOL_DEFINITIONS = [
    TOOL_RECALL_WINDSURF_CONVERSATIONS,
]

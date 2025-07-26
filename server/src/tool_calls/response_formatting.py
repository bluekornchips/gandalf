"""
Response formatting utilities for conversation aggregation.

This module handles the formatting and presentation of aggregated
conversation data for MCP clients.
"""

import json
from pathlib import Path
from typing import Any

from src.config.conversation_config import (
    CONVERSATION_ID_DISPLAY_LIMIT,
    CONVERSATION_SNIPPET_DISPLAY_LIMIT,
    CONVERSATION_TITLE_DISPLAY_LIMIT,
    TOKEN_OPTIMIZATION_CONTENT_TRUNCATION_LIMIT,
    TOKEN_OPTIMIZATION_MAX_RESPONSE_SIZE,
    TOKEN_OPTIMIZATION_MAX_TOOL_RESULT_FIELDS,
    TOKEN_OPTIMIZATION_SUMMARY_MODE_THRESHOLD,
)
from src.utils.common import log_debug, log_info


def _convert_paths_for_json(obj: Any) -> Any:
    """Convert Path objects to strings for JSON serialization."""
    if isinstance(obj, Path):
        return str(obj)
    elif isinstance(obj, dict):
        return {key: _convert_paths_for_json(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [_convert_paths_for_json(item) for item in obj]
    else:
        return obj


def _truncate_string_field(
    text: str, max_length: int, field_name: str = "field"
) -> str:
    """Truncate string field to specified length with ellipsis."""
    if len(text) <= max_length:
        return text
    # Reserve 3 characters for "..." to stay within max_length
    truncated = text[: max_length - 3] + "..."
    log_debug(f"Truncated {field_name} from {len(text)} to {len(truncated)} chars")
    return truncated


def _create_lightweight_conversation(
    conversation: dict[str, Any],
) -> dict[str, Any]:
    """Create lightweight conversation format optimized for aggregated results."""
    # Extract core fields with fallbacks
    conv_id = (
        conversation.get("id")
        or conversation.get("conversation_id")
        or conversation.get("uuid")
        or ""
    )

    title = (
        conversation.get("title")
        or conversation.get("name")
        or conversation.get("subject")
        or "Untitled"
    )

    # Create lightweight format
    lightweight = {
        "id": _truncate_string_field(
            str(conv_id), CONVERSATION_ID_DISPLAY_LIMIT, "conversation_id"
        ),
        "title": _truncate_string_field(
            str(title), CONVERSATION_TITLE_DISPLAY_LIMIT, "title"
        ),
        "source_tool": conversation.get("source_tool", "unknown"),
        "message_count": conversation.get("message_count", 0),
        "relevance_score": round(conversation.get("relevance_score", 0.0), 2),
        "created_at": conversation.get("created_at", ""),
    }

    # Add snippet if available
    snippet = conversation.get("snippet", "")
    if snippet:
        lightweight["snippet"] = _truncate_string_field(
            str(snippet), CONVERSATION_SNIPPET_DISPLAY_LIMIT, "snippet"
        )

    return lightweight


def _standardize_conversation_format(
    conversation: dict[str, Any],
    source_tool: str,
    context_keywords: list[str],
    lightweight: bool = False,
) -> dict[str, Any]:
    """Standardize conversation format across different tools."""
    if lightweight:
        # Set source_tool in conversation for lightweight processing
        conversation_with_source = {**conversation, "source_tool": source_tool}
        return _create_lightweight_conversation(conversation_with_source)
    # Create standardized base format
    standardized = {
        "id": str(conversation.get("id", conversation.get("conversation_id", ""))),
        "title": str(conversation.get("title", conversation.get("name", "Untitled"))),
        "source_tool": source_tool,
        "message_count": conversation.get("message_count", 0),
        "relevance_score": float(conversation.get("relevance_score", 0.0)),
        "created_at": str(conversation.get("created_at", "")),
    }

    # Add optional fields if present
    from src.config.conversation_config import CONVERSATION_OPTIONAL_FIELDS

    for field in CONVERSATION_OPTIONAL_FIELDS:
        if field in conversation:
            standardized[field] = conversation[field]

    from src.config.conversation_config import AGENTIC_TOOL_WINDSURF

    if source_tool == AGENTIC_TOOL_WINDSURF:
        if "source" in conversation:
            standardized["windsurf_source"] = conversation["source"]

    # Add truncated context keywords
    from src.config.conversation_config import TOKEN_OPTIMIZATION_MAX_CONTEXT_KEYWORDS

    standardized["context_keywords"] = context_keywords[
        :TOKEN_OPTIMIZATION_MAX_CONTEXT_KEYWORDS
    ]

    return standardized


def _check_response_size_and_optimize(
    conversations: list[dict[str, Any]],
    summary: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any], bool]:
    """Check response size and optimize if necessary."""
    # Convert to JSON to measure size
    test_response = {
        "summary": summary,
        "conversations": conversations,
    }

    # Measure response size
    response_json = json.dumps(test_response, default=_convert_paths_for_json)
    response_size = len(response_json.encode("utf-8"))

    log_debug(f"Response size: {response_size:,} bytes")

    # Check if optimization is needed
    if response_size > TOKEN_OPTIMIZATION_MAX_RESPONSE_SIZE:
        log_info(f"Large response ({response_size:,} bytes), applying optimizations")

        # Apply optimizations
        optimized_conversations = []
        for conv in conversations:
            optimized_conv = _create_lightweight_conversation(conv)

            # Further truncate if still too large
            if response_size > TOKEN_OPTIMIZATION_SUMMARY_MODE_THRESHOLD:
                # Remove optional fields for extreme size reduction
                fields_to_remove = ["snippet", "analysis", "tags"]
                for field in fields_to_remove:
                    optimized_conv.pop(field, None)

            optimized_conversations.append(optimized_conv)

        # Update summary with optimization notice
        optimized_summary = summary.copy()
        optimized_summary["optimization_applied"] = True
        optimized_summary["original_size_bytes"] = response_size

        return optimized_conversations, optimized_summary, True

    return conversations, summary, False


def _create_summary_response(
    conversations: list[dict[str, Any]],
    processing_stats: dict[str, Any],
    context_keywords: list[str],
    parameters: dict[str, Any],
) -> dict[str, Any]:
    """Create comprehensive summary for aggregated results."""
    total_found = processing_stats.get("total_conversations_found", len(conversations))

    summary = {
        "total_conversations_found": total_found,
        "conversations_returned": len(conversations),
        "success_rate_percent": round(
            len(conversations) / total_found * 100 if total_found > 0 else 0,
            1,
        ),
        "processing_time_seconds": round(
            processing_stats.get("total_processing_time", 0),
            2,
        ),
        "tools_processed": processing_stats.get("tools_processed", 0),
        "tools_with_data": processing_stats.get("tools_with_data", []),
        "context_keywords": context_keywords[:15],  # Limit for readability
    }

    # Add tool-specific stats if available
    if processing_stats.get("tools_with_errors"):
        summary["tools_with_errors"] = processing_stats["tools_with_errors"]

    # Add parameter information
    summary["parameters"] = {
        "limit": parameters.get("limit", 60),
        "min_relevance_score": parameters.get("min_relevance_score", 0.0),
        "days_lookback": parameters.get("days_lookback", 30),
        "fast_mode": parameters.get("fast_mode", True),
    }

    return summary


def format_aggregated_response(
    conversations: list[dict[str, Any]],
    processing_stats: dict[str, Any],
    context_keywords: list[str],
    parameters: dict[str, Any],
) -> dict[str, Any]:
    """Format the final aggregated response."""
    # Create summary
    summary = _create_summary_response(
        conversations, processing_stats, context_keywords, parameters
    )

    # Check size and optimize if needed
    final_conversations, final_summary, was_optimized = (
        _check_response_size_and_optimize(conversations, summary)
    )

    if was_optimized:
        log_info(
            f"Response optimized: {len(conversations)} -> {len(final_conversations)} conversations"
        )

    # Create final response
    response = {
        "summary": final_summary,
        "conversations": final_conversations,
        "status": "aggregation_complete",
    }

    # Add optimization info if applied
    if was_optimized:
        response["optimization_note"] = (
            "Response was optimized for size. Some conversation details were truncated."
        )

    return response


def create_lightweight_conversation_list(
    conversations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Create lightweight format for a list of conversations."""
    return [_create_lightweight_conversation(conv) for conv in conversations]


def truncate_conversation_content(
    conversation: dict[str, Any],
    max_content_length: int = TOKEN_OPTIMIZATION_CONTENT_TRUNCATION_LIMIT,
) -> dict[str, Any]:
    """Truncate conversation content to specified length."""
    truncated = conversation.copy()

    # Truncate main text fields
    text_fields = ["title", "snippet", "content"]
    for field in text_fields:
        if field in truncated:
            truncated[field] = _truncate_string_field(
                str(truncated[field]), max_content_length, field
            )

    # Truncate messages if present
    if "messages" in truncated and isinstance(truncated["messages"], list):
        truncated_messages = []
        for msg in truncated["messages"][:TOKEN_OPTIMIZATION_MAX_TOOL_RESULT_FIELDS]:
            if isinstance(msg, dict):
                truncated_msg = msg.copy()
                for msg_field in ["content", "text"]:
                    if msg_field in truncated_msg:
                        truncated_msg[msg_field] = _truncate_string_field(
                            str(truncated_msg[msg_field]), max_content_length, msg_field
                        )
                truncated_messages.append(truncated_msg)
        truncated["messages"] = truncated_messages

    return truncated

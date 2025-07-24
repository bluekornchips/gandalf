"""
Conversation parsing utilities for Cursor IDE conversations.

This module handles the extraction and initial processing of conversation data
from Cursor's storage formats.
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from src.config.config_data import TECHNOLOGY_KEYWORD_MAPPING
from src.config.constants.database import DATABASE_STRUCTURE_LIMITATION_NOTE
from src.core.conversation_analysis import generate_shared_context_keywords
from src.core.conversation_filtering import apply_conversation_filtering
from src.tool_calls.cursor.conversation_analyzer import (
    analyze_conversation_relevance,
    analyze_conversation_relevance_optimized,
)
from src.tool_calls.cursor.conversation_cache import (
    is_cache_valid,
    load_from_cache_filtered,
    save_conversations_to_cache,
)
from src.tool_calls.cursor.conversation_formatter import (
    format_conversation_summary,
    format_lightweight_conversations,
)
from src.tool_calls.cursor.conversation_utils import (
    handle_fast_conversation_extraction,
    log_processing_progress,
    quick_conversation_filter,
    validate_conversation_data,
)
from src.utils.access_control import AccessValidator
from src.utils.common import format_json_response, log_debug, log_info
from src.utils.cursor_chat_query import CursorQuery
from src.utils.performance import get_duration, log_operation_time, start_timer


def _get_tech_category_from_extension(extension: str) -> str | None:
    """Get technology category from file extension."""
    extension_lower = extension.lower().lstrip(".")

    for category, data in TECHNOLOGY_KEYWORD_MAPPING.items():
        for ext in data:
            if (
                isinstance(ext, str)
                and "." in ext
                and ext.lstrip(".") == extension_lower
            ):
                return category

    return None


def extract_conversation_text(
    conversation: dict[str, Any],
) -> tuple[str, int]:
    """Extract all text content from a conversation."""
    text_parts = []

    # Extract title
    title = conversation.get("title", conversation.get("name", ""))
    if title:
        text_parts.append(title)

    # Extract messages
    messages = conversation.get("messages", [])
    message_count = 0

    if isinstance(messages, list):
        message_count = len(messages)
        for msg in messages:
            content: str = ""
            if isinstance(msg, dict):
                content = str(msg.get("content", msg.get("text", "")))
            elif isinstance(msg, str):
                content = msg

            if content:
                text_parts.append(str(content))

    return " ".join(text_parts), message_count


def extract_snippet(text: str, query: str) -> str:
    """Extract relevant snippet from text based on query."""
    if not query or not text:
        return text[:200] + "..." if len(text) > 200 else text

    query_words = query.lower().split()
    text_lower = text.lower()

    # Find the first occurrence of any query word
    best_pos = -1
    for word in query_words:
        pos = text_lower.find(word)
        if pos != -1 and (best_pos == -1 or pos < best_pos):
            best_pos = pos

    if best_pos == -1:
        # No query words found, return beginning
        return text[:200] + "..." if len(text) > 200 else text

    # Extract context around the found word
    start = max(0, best_pos - 100)
    end = min(len(text), best_pos + 300)
    snippet = text[start:end]

    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."

    return snippet


def handle_fast_mode(
    limit: int,
    days_lookback: int,
    conversation_types: list[str],
) -> dict[str, Any]:
    """Handle fast mode conversation extraction."""
    # Initialize query tool for fresh data
    query_tool = CursorQuery(silent=True)

    # Query conversations
    log_info("Fast mode: Querying conversations from Cursor databases...")
    start_time = start_timer()
    data = query_tool.query_all_conversations()
    query_time = get_duration(start_time)
    log_operation_time("cursor_conversation_query", start_time, "debug")

    # Process data for fast extraction
    # Extract conversations from all workspaces
    conversations = []
    for workspace in data.get("workspaces", []):
        workspace_conversations = workspace.get("conversations", [])
        conversations.extend(workspace_conversations)

    processed_count = len(conversations)
    skipped_count = 0

    # Quick filter by date and type
    if days_lookback:
        cutoff_date = datetime.now() - timedelta(days=days_lookback)
        filtered_conversations = []

        for conv in conversations:
            # Basic date filtering
            created_at = conv.get("created_at")
            if created_at:
                try:
                    if isinstance(created_at, str):
                        conv_time = datetime.fromisoformat(
                            created_at.replace("Z", "+00:00")
                        )
                        if conv_time < cutoff_date:
                            skipped_count += 1
                            continue
                except (ValueError, TypeError):
                    pass

            filtered_conversations.append(conv)

        conversations = filtered_conversations[:limit]

    return handle_fast_conversation_extraction(
        conversations, limit, query_time, processed_count, skipped_count
    )


def generate_context_keywords(project_root: Path) -> list[str]:
    """Generate context keywords for the current project."""
    return generate_shared_context_keywords(project_root)


def handle_enhanced_mode(
    project_root: Path,
    limit: int,
    min_relevance_score: float,
    days_lookback: int,
    conversation_types: list[str],
    include_analysis: bool,
    query_and_analyze_func: Any,  # Function to call for querying
) -> dict[str, Any]:
    """Handle enhanced mode with caching and analysis."""
    # Generate context keywords for cache validation
    log_info("Generating intelligent context keywords...")
    context_keywords = generate_context_keywords(project_root)
    log_debug(f"Generated context keywords: {context_keywords[:15]}...")

    # Check cache first
    if is_cache_valid(project_root, context_keywords):
        cached_result = load_from_cache_filtered(
            project_root,
            limit,
            min_relevance_score,
            days_lookback,
            conversation_types,
            context_keywords,
        )
        if cached_result:
            return cached_result

    # Cache miss or invalid - query fresh data
    result = query_and_analyze_func(
        project_root,
        context_keywords,
        limit,
        min_relevance_score,
        days_lookback,
        conversation_types,
        include_analysis,
    )
    # Cast the result to the expected type
    return (
        result
        if isinstance(result, dict)
        else {"error": "Invalid response from query function"}
    )


def query_and_analyze_conversations(
    project_root: Path,
    context_keywords: list[str],
    limit: int,
    min_relevance_score: float,
    days_lookback: int,
    conversation_types: list[str],
    include_analysis: bool,
) -> dict[str, Any]:
    """Query and analyze conversations from database."""
    log_info("Cache miss - analyzing conversations from database...")

    # Initialize query tool
    query_tool = CursorQuery(silent=True)

    # Query conversations
    start_time = start_timer()
    data = query_tool.query_all_conversations()
    query_time = get_duration(start_time)

    conversations = data.get("conversations", [])
    if not conversations:
        return AccessValidator.create_error_response("No conversations found")

    log_info(f"Found {len(conversations)} conversations, analyzing relevance...")

    # Quick filter for performance
    filtered_conversations = quick_conversation_filter(
        conversations, context_keywords, days_lookback
    )

    # Analyze relevance
    analyzed_conversations = []
    processing_start = start_timer()

    for i, conversation in enumerate(filtered_conversations):
        if not validate_conversation_data(conversation):
            continue

        # Choose analysis method based on performance needs
        if include_analysis:
            analyzed = analyze_conversation_relevance(
                conversation, context_keywords, project_root, include_analysis
            )
        else:
            analyzed = analyze_conversation_relevance_optimized(
                conversation, context_keywords, project_root
            )

        analyzed_conversations.append(analyzed)

        # Log progress
        if i > 0:
            log_processing_progress(
                i + 1, len(filtered_conversations), processing_start
            )

    processing_time = get_duration(processing_start)

    # Apply filtering and sorting
    result_conversations, filtering_metadata = apply_conversation_filtering(
        analyzed_conversations,
        project_root,
        requested_limit=limit,
    )

    # Format results
    lightweight_conversations = format_lightweight_conversations(
        [
            {"conversation": conv, "relevance_score": conv.get("relevance_score", 0)}
            for conv in result_conversations
        ]
    )

    # Cache results for future use
    save_conversations_to_cache(
        project_root,
        [
            {"conversation": conv, "relevance_score": conv.get("relevance_score", 0)}
            for conv in result_conversations
        ],
        context_keywords,
        processing_time,
        len(analyzed_conversations),
    )

    # Create final result
    result = format_conversation_summary(
        lightweight_conversations,
        len(analyzed_conversations),
        {
            "extraction_time": round(query_time, 2),
            "analysis_time": round(processing_time, 2),
            "total_time": round(query_time + processing_time, 2),
            "context_keywords": context_keywords[:15],
        },
    )

    result["database_note"] = DATABASE_STRUCTURE_LIMITATION_NOTE

    log_info(
        f"Analyzed {len(analyzed_conversations)} conversations, "
        f"returned {len(lightweight_conversations)} results in {query_time + processing_time:.2f}s"
    )

    return AccessValidator.create_success_response(format_json_response(result))

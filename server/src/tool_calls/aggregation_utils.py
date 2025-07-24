"""
Utility functions for conversation aggregation.

This module contains shared utility functions and helper methods
used across the aggregation processing modules.
"""

import json
from pathlib import Path
from typing import Any

from src.config.constants.conversation import (
    CONVERSATION_DEFAULT_FAST_MODE,
    CONVERSATION_DEFAULT_LIMIT,
    CONVERSATION_DEFAULT_LOOKBACK_DAYS,
    CONVERSATION_DEFAULT_MIN_SCORE,
    CONVERSATION_MAX_LIMIT,
    CONVERSATION_MAX_LOOKBACK_DAYS,
)
from src.utils.access_control import AccessValidator
from src.utils.common import log_debug, log_info
from src.utils.performance import get_duration


def validate_aggregation_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize aggregation arguments."""
    # Extract and validate limit
    limit = arguments.get("limit", CONVERSATION_DEFAULT_LIMIT)
    if not isinstance(limit, int) or limit < 1:
        limit = CONVERSATION_DEFAULT_LIMIT
    else:
        limit = min(limit, CONVERSATION_MAX_LIMIT)

    # Extract and validate min_relevance_score
    min_score = arguments.get("min_relevance_score", CONVERSATION_DEFAULT_MIN_SCORE)
    if not isinstance(min_score, int | float):
        min_score = CONVERSATION_DEFAULT_MIN_SCORE
    else:
        min_score = max(0.0, float(min_score))

    # Extract and validate days_lookback
    days_lookback = arguments.get("days_lookback", CONVERSATION_DEFAULT_LOOKBACK_DAYS)
    if not isinstance(days_lookback, int) or days_lookback < 1:
        days_lookback = CONVERSATION_DEFAULT_LOOKBACK_DAYS
    else:
        days_lookback = min(days_lookback, CONVERSATION_MAX_LOOKBACK_DAYS)

    # Extract and validate other parameters
    conversation_types = arguments.get("conversation_types", [])
    if not isinstance(conversation_types, list):
        conversation_types = []

    include_analysis = arguments.get("include_analysis", False)
    if not isinstance(include_analysis, bool):
        include_analysis = False

    fast_mode = arguments.get("fast_mode", CONVERSATION_DEFAULT_FAST_MODE)
    if not isinstance(fast_mode, bool):
        fast_mode = CONVERSATION_DEFAULT_FAST_MODE

    # Additional parameters
    tags = arguments.get("tags", [])
    if not isinstance(tags, list):
        tags = []

    search_query = arguments.get("search_query", "")
    if not isinstance(search_query, str):
        search_query = ""

    user_prompt = arguments.get("user_prompt", "")
    if not isinstance(user_prompt, str):
        user_prompt = ""

    tools = arguments.get("tools", [])
    if not isinstance(tools, list):
        tools = []

    return {
        "limit": limit,
        "min_relevance_score": min_score,
        "days_lookback": days_lookback,
        "conversation_types": conversation_types,
        "include_analysis": include_analysis,
        "fast_mode": fast_mode,
        "tags": tags,
        "search_query": search_query,
        "user_prompt": user_prompt,
        "tools": tools,
    }


def generate_context_keywords_for_project(
    project_root: Path,
    user_prompt: str = "",
    search_query: str = "",
) -> list[str]:
    """Generate context keywords for the project with optional user input."""
    # Skip project-specific keywords to return ALL conversations from ALL directories
    # TODO: Make this configurable via environment variable if needed
    context_keywords = []

    # Add keywords from user prompt
    if user_prompt:
        prompt_keywords = extract_keywords_from_text(user_prompt)
        context_keywords.extend(prompt_keywords)

    # Add keywords from search query
    if search_query:
        query_keywords = extract_keywords_from_text(search_query)
        context_keywords.extend(query_keywords)

    # Remove duplicates while preserving order
    unique_keywords = []
    seen = set()
    for keyword in context_keywords:
        keyword_lower = keyword.lower()
        if keyword_lower not in seen:
            unique_keywords.append(keyword)
            seen.add(keyword_lower)

    log_debug(
        f"Generated {len(unique_keywords)} unique context keywords (project filtering disabled)"
    )
    return unique_keywords


def extract_keywords_from_text(text: str) -> list[str]:
    """Extract keywords from user-provided text."""
    if not text or not isinstance(text, str):
        return []

    import re

    # Simple keyword extraction
    # Remove punctuation and split into words
    cleaned_text = re.sub(r"[^\w\s]", " ", text.lower())
    words = cleaned_text.split()

    # Filter out common stop words and very short words
    stop_words = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "can",
        "may",
        "might",
        "this",
        "that",
        "these",
        "those",
        "i",
        "you",
        "he",
        "she",
        "it",
        "we",
        "they",
        "me",
        "him",
        "her",
        "us",
        "them",
    }

    keywords = []
    for word in words:
        if len(word) > 2 and word not in stop_words:
            keywords.append(word)

    return keywords[:20]  # Limit to top 20 keywords


def merge_conversation_results(
    results: list[dict[str, Any]],
    limit: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Merge conversation results from multiple tools."""
    all_conversations: list[dict[str, Any]] = []
    merged_stats: dict[str, Any] = {
        "total_processing_time": 0.0,
        "tools_processed": 0,
        "tools_successful": [],
        "tools_failed": [],
        "total_found": 0,
    }

    for result in results:
        merged_stats["tools_processed"] += 1

        try:
            # Parse result based on format
            conversations = []
            processing_time = 0.0

            if isinstance(result, dict):
                if "content" in result:
                    # MCP-style response
                    for content_item in result.get("content", []):
                        if content_item.get("type") == "text":
                            data = json.loads(content_item["text"])
                            conversations = data.get("conversations", [])
                            processing_time = data.get("processing_time", 0)
                            break
                else:
                    # Direct response
                    conversations = result.get("conversations", [])
                    processing_time = result.get("processing_time", 0)

            if conversations:
                all_conversations.extend(conversations)
                merged_stats["tools_successful"].append(
                    result.get("tool_name", "unknown")
                )
                merged_stats["total_found"] += len(conversations)

                if isinstance(processing_time, int | float):
                    merged_stats["total_processing_time"] += processing_time
            else:
                merged_stats["tools_failed"].append(result.get("tool_name", "unknown"))

        except (json.JSONDecodeError, KeyError, TypeError, AttributeError) as e:
            log_debug(f"Failed to parse result: {e}")
            merged_stats["tools_failed"].append(result.get("tool_name", "unknown"))

    # Sort by relevance score (descending)
    all_conversations.sort(key=lambda x: x.get("relevance_score", 0.0), reverse=True)

    # Limit results
    limited_conversations = all_conversations[:limit]

    log_info(
        f"Merged results: {len(all_conversations)} total conversations, "
        f"returning top {len(limited_conversations)}"
    )

    return limited_conversations, merged_stats


def create_error_response_for_aggregation(
    error_message: str,
    tools_attempted: list[str] | None = None,
    processing_time: float = 0.0,
) -> dict[str, Any]:
    """Create standardized error response for aggregation failures."""
    error_data = {
        "error": error_message,
        "success": False,
        "summary": {
            "total_conversations_found": 0,
            "conversations_returned": 0,
            "success_rate_percent": 0.0,
            "processing_time_seconds": round(processing_time, 2),
            "tools_attempted": tools_attempted or [],
        },
        "conversations": [],
        "status": "aggregation_failed",
    }

    return AccessValidator.create_error_response(json.dumps(error_data, indent=2))


def calculate_success_rate(
    successful_tools: int,
    total_tools: int,
    conversations_returned: int,
    conversations_found: int,
) -> float:
    """Calculate overall success rate for aggregation."""
    if total_tools == 0:
        return 0.0

    # Weight by both tool success and conversation retrieval
    tool_success_rate = successful_tools / total_tools

    if conversations_found > 0:
        conversation_success_rate = conversations_returned / conversations_found
        # Average the two rates
        return round((tool_success_rate + conversation_success_rate) / 2 * 100, 1)
    else:
        return round(tool_success_rate * 100, 1)


def log_aggregation_performance(
    operation_name: str,
    start_time: float,
    tools_processed: int,
    conversations_returned: int,
) -> None:
    """Log performance metrics for aggregation operations."""
    duration = get_duration(start_time)
    rate = conversations_returned / duration if duration > 0 else 0

    log_info(
        f"{operation_name} completed: {tools_processed} tools, "
        f"{conversations_returned} conversations in {duration:.2f}s "
        f"({rate:.1f} conv/sec)"
    )

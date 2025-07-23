"""
Utility functions for Cursor IDE conversation processing.

This module contains shared utility functions and helper methods
used across the conversation processing modules.
"""

import json
import re
from datetime import datetime, timedelta
from typing import Any

from src.config.config_data import TECHNOLOGY_KEYWORD_MAPPING
from src.config.constants.conversation import (
    CONVERSATION_KEYWORD_CHECK_LIMIT,
    CONVERSATION_PROGRESS_LOG_INTERVAL,
    CONVERSATION_TEXT_EXTRACTION_LIMIT,
)
from src.config.constants.database import (
    DATABASE_STRUCTURE_LIMITATION_NOTE,
)
from src.utils.access_control import AccessValidator
from src.utils.common import log_debug, log_info
from src.utils.performance import get_duration


def handle_fast_conversation_extraction(
    conversations: list[dict[str, Any]],
    limit: int,
    extraction_time: float,
    processed_count: int,
    skipped_count: int,
) -> dict[str, Any]:
    """Handle fast conversation extraction results."""
    # Quick processing - just format and return
    processing_time = 0.1  # Minimal processing time

    # Limit results
    limited_conversations = conversations[:limit]

    result = {
        "summary": {
            "total_conversations_found": len(conversations),
            "conversations_returned": len(limited_conversations),
            "success_rate_percent": (
                round(
                    (processed_count - skipped_count) / processed_count * 100,
                    1,
                )
                if processed_count > 0
                else 0
            ),
            "extraction_time_seconds": round(extraction_time, 2),
            "filtering_time_seconds": round(processing_time, 2),
            "total_time_seconds": round(extraction_time + processing_time, 2),
        },
        "conversations": limited_conversations,
        "database_note": DATABASE_STRUCTURE_LIMITATION_NOTE,
        "processing_time": round(
            extraction_time + processing_time, 2
        ),  # Add top-level field for aggregator
    }

    log_info(
        f"Ultra-fast extracted {len(limited_conversations)} conversations in {extraction_time + processing_time:.2f}s "
        f"(processed {processed_count}, skipped {skipped_count})"
    )
    return AccessValidator.create_success_response(json.dumps(result, indent=2))


def log_processing_progress(
    current: int,
    total: int,
    start_time: float,
    operation: str = "Processing",
) -> None:
    """Log processing progress at regular intervals."""
    if current % CONVERSATION_PROGRESS_LOG_INTERVAL == 0 or current == total:
        elapsed = get_duration(start_time)
        percentage = (current / total * 100) if total > 0 else 0
        rate = current / elapsed if elapsed > 0 else 0

        log_info(
            f"{operation}: {current}/{total} ({percentage:.1f}%) "
            f"- {rate:.1f} items/sec - {elapsed:.1f}s elapsed"
        )


def validate_conversation_data(conversation: Any) -> bool:
    """Validate that conversation data has required fields."""
    if not isinstance(conversation, dict):
        return False

    # Check for essential fields
    # Check for ID field, and alternatives
    if not any(field in conversation for field in ["id", "conversation_id", "uuid"]):
        return False

    if "messages" not in conversation:
        return False

    # Validate messages field
    messages = conversation.get("messages", [])
    if not isinstance(messages, list):
        return False

    return True


def extract_conversation_metadata(conversation: dict[str, Any]) -> dict[str, Any]:
    """Extract metadata from conversation."""
    metadata: dict[str, Any] = {}

    # Extract basic info
    metadata["has_title"] = bool(conversation.get("title") or conversation.get("name"))
    metadata["message_count"] = len(conversation.get("messages", []))
    metadata["has_timestamp"] = bool(
        conversation.get("created_at") or conversation.get("timestamp")
    )

    # Extract message types if available
    messages = conversation.get("messages", [])
    if isinstance(messages, list):
        message_types = set()
        for msg in messages:
            if isinstance(msg, dict):
                msg_type = msg.get("type") or msg.get("role", "unknown")
                message_types.add(msg_type)
        metadata["message_types"] = list(message_types)

    return metadata


def sanitize_conversation_for_output(conversation: dict[str, Any]) -> dict[str, Any]:
    """Sanitize conversation data for safe output."""
    sanitized = {}

    # Copy safe fields
    safe_fields = [
        "id",
        "conversation_id",
        "uuid",
        "title",
        "name",
        "subject",
        "created_at",
        "timestamp",
        "date_created",
        "message_count",
        "relevance_score",
        "snippet",
        "source_tool",
        "conversation_type",
    ]

    for field in safe_fields:
        if field in conversation:
            sanitized[field] = conversation[field]

    # Handle messages carefully
    messages = conversation.get("messages", [])
    if isinstance(messages, list):
        sanitized_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                sanitized_msg = {}
                msg_safe_fields = ["content", "text", "type", "role", "timestamp"]
                for msg_field in msg_safe_fields:
                    if msg_field in msg:
                        sanitized_msg[msg_field] = str(msg[msg_field])[
                            :1000
                        ]  # Limit length
                sanitized_messages.append(sanitized_msg)
        sanitized["messages"] = sanitized_messages

    return sanitized


def create_error_response(
    error_message: str, details: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Create standardized error response."""
    response = {
        "error": error_message,
        "success": False,
    }

    if details:
        response["details"] = details

    return AccessValidator.create_error_response(json.dumps(response, indent=2))


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


def extract_keywords_from_content(file_name: str, content: str) -> list[str]:
    """Extract relevant keywords from conversation content."""
    keywords = []

    # Extract file extensions and map to tech categories
    extensions = re.findall(r"\.[a-zA-Z0-9]{1,6}", content)
    for ext in set(extensions):
        tech_category = _get_tech_category_from_extension(ext)
        if tech_category:
            keywords.append(tech_category)

    # Extract common programming patterns
    patterns = {
        "function": r"\bfunction\s+\w+",
        "class": r"\bclass\s+\w+",
        "import": r"\bimport\s+",
        "error": r"\berror\b|\bexception\b",
        "test": r"\btest\b|\btesting\b",
        "database": r"\bdatabase\b|\bdb\b|\bsql\b",
        "api": r"\bapi\b|\brest\b|\bhttp\b",
    }

    for keyword, pattern in patterns.items():
        if re.search(pattern, content, re.IGNORECASE):
            keywords.append(keyword)

    return list(set(keywords))


def extract_conversation_text_lazy(
    conversation: dict[str, Any],
) -> tuple[str, int]:
    """Extract text from conversation with lazy loading approach."""
    text_parts = []
    total_chars = 0

    # Extract title
    title = conversation.get("title", conversation.get("name", ""))
    if title:
        text_parts.append(title)
        total_chars += len(title)

    # Extract messages with early termination for large conversations
    messages = conversation.get("messages", [])
    if isinstance(messages, list):
        for msg in messages:
            if total_chars > CONVERSATION_TEXT_EXTRACTION_LIMIT:
                break

            content: str = ""
            if isinstance(msg, dict):
                content = str(msg.get("content", msg.get("text", "")))
            elif isinstance(msg, str):
                content = msg

            if content:
                text_parts.append(str(content))
                total_chars += len(content)

    combined_text = " ".join(text_parts)

    # Truncate if still too long
    if len(combined_text) > CONVERSATION_TEXT_EXTRACTION_LIMIT:
        combined_text = combined_text[:CONVERSATION_TEXT_EXTRACTION_LIMIT]
        log_debug(
            f"Truncated conversation text to {CONVERSATION_TEXT_EXTRACTION_LIMIT} chars"
        )

    return combined_text, len(messages)


def quick_conversation_filter(
    conversations: list[dict[str, Any]],
    context_keywords: list[str],
    days_lookback: int,
) -> list[dict[str, Any]]:
    """Quick filter conversations by basic criteria."""
    if not conversations:
        return []

    # Calculate date threshold
    cutoff_date = datetime.now() - timedelta(days=days_lookback)
    cutoff_timestamp = cutoff_date.timestamp()

    filtered = []

    for conv in conversations[:CONVERSATION_KEYWORD_CHECK_LIMIT]:
        # Check date
        created_at = conv.get("created_at")
        if created_at:
            try:
                if isinstance(created_at, str):
                    conv_time = datetime.fromisoformat(
                        created_at.replace("Z", "+00:00")
                    )
                    if conv_time.timestamp() < cutoff_timestamp:
                        continue
                elif isinstance(created_at, int | float):
                    if created_at < cutoff_timestamp:
                        continue
            except (ValueError, TypeError):
                log_debug(f"Failed to parse date: {created_at}")

        # Quick keyword check if available
        if context_keywords:
            text, _ = extract_conversation_text_lazy(conv)
            if text and any(kw.lower() in text.lower() for kw in context_keywords[:5]):
                filtered.append(conv)
            elif not text:  # Include conversations we couldn't analyze
                filtered.append(conv)
        else:
            filtered.append(conv)

    return filtered

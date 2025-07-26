"""
Content extraction utilities for conversation analysis.

This module provides utilities for extracting and processing text content
from various conversation data formats across different IDEs.
"""

from datetime import datetime, timedelta
from typing import Any

from src.config.conversation_config import CONVERSATION_TEXT_EXTRACTION_LIMIT
from src.utils.common import log_debug


def extract_conversation_content(  # noqa: C901
    conversation_data: Any, max_chars: int = CONVERSATION_TEXT_EXTRACTION_LIMIT
) -> str:
    """Extract text content from conversation data (IDE-agnostic)."""
    text_parts = []
    total_chars = 0

    try:
        # Handle different conversation data formats
        if isinstance(conversation_data, dict):
            # Extract title/name first
            title = conversation_data.get("name") or conversation_data.get("title", "")
            if title and title != "Untitled":
                text_parts.append(title)
                total_chars += len(title)

            # Claude Code format - messages array
            if "messages" in conversation_data:
                messages = conversation_data["messages"]
                total_chars = _extract_from_messages(
                    messages, text_parts, total_chars, max_chars
                )

            # Cursor format - different structure
            elif "composerSteps" in conversation_data:
                steps = conversation_data["composerSteps"]
                for step in steps[:10]:  # Limit steps processed
                    if total_chars >= max_chars:
                        break

                    content = step.get("content", "") or step.get("text", "")
                    if content:
                        remaining = max_chars - total_chars
                        if len(content) > remaining:
                            content = content[:remaining]
                        text_parts.append(str(content))
                        total_chars += len(str(content))

            # Generic content field
            elif "content" in conversation_data:
                content = conversation_data["content"]
                if isinstance(content, str):
                    remaining = max_chars - total_chars
                    if len(content) > remaining:
                        content = content[:remaining]
                    text_parts.append(content)
                    total_chars += len(content)

        elif isinstance(conversation_data, list):
            # Handle message arrays directly
            total_chars = _extract_from_messages(
                conversation_data, text_parts, total_chars, max_chars
            )

        elif isinstance(conversation_data, str):
            # Handle direct string content
            content = conversation_data[:max_chars]
            text_parts.append(content)

    except (KeyError, TypeError, ValueError, AttributeError) as e:
        log_debug(f"Error extracting conversation content: {e}")

    return " ".join(text_parts)


def _extract_from_messages(
    messages: list[Any], text_parts: list[str], total_chars: int, max_chars: int
) -> int:
    """Extract text from message arrays with character limit."""
    for message in messages[:10]:  # Limit messages processed
        if total_chars >= max_chars:
            break

        if isinstance(message, dict):
            content = message.get("content", "") or message.get("text", "")

            if isinstance(content, str):
                remaining = max_chars - total_chars
                if len(content) > remaining:
                    content = content[:remaining]
                text_parts.append(content)
                total_chars += len(content)

            elif isinstance(content, list):
                # Handle structured content (Claude API format)
                for item in content:
                    if total_chars >= max_chars:
                        break
                    if isinstance(item, dict) and item.get("type") == "text":
                        text = item.get("text", "")
                        remaining = max_chars - total_chars
                        if len(text) > remaining:
                            text = text[:remaining]
                        text_parts.append(text)
                        total_chars += len(text)

        elif isinstance(message, str):
            # Handle string messages directly
            remaining = max_chars - total_chars
            if len(message) > remaining:
                message = message[:remaining]
            text_parts.append(message)
            total_chars += len(message)

    return total_chars


def extract_conversation_metadata(conversation_data: Any) -> dict[str, Any]:
    """Extract metadata from conversation data."""
    metadata = {}

    try:
        if isinstance(conversation_data, dict):
            # Common metadata fields
            metadata_fields = [
                "id",
                "name",
                "title",
                "created_at",
                "updated_at",
                "lastUpdatedAt",
                "timestamp",
                "start_time",
                "end_time",
                "user_id",
                "session_id",
            ]

            for field in metadata_fields:
                if field in conversation_data:
                    metadata[field] = conversation_data[field]

            # Extract message count
            if "messages" in conversation_data:
                messages = conversation_data["messages"]
                metadata["message_count"] = (
                    len(messages) if isinstance(messages, list) else 0
                )
            elif "composerSteps" in conversation_data:
                steps = conversation_data["composerSteps"]
                metadata["step_count"] = len(steps) if isinstance(steps, list) else 0

            # Extract session metadata if nested
            if "session_metadata" in conversation_data:
                session_meta = conversation_data["session_metadata"]
                if isinstance(session_meta, dict):
                    metadata.update(session_meta)

    except (KeyError, TypeError, AttributeError) as e:
        log_debug(f"Error extracting conversation metadata: {e}")

    return metadata


def normalize_conversation_format(conversation_data: Any) -> dict[str, Any]:
    """Normalize conversation data to a standard format."""
    normalized = {
        "id": "",
        "title": "",
        "content": "",
        "messages": [],
        "metadata": {},
        "source": "unknown",
    }

    try:
        if isinstance(conversation_data, dict):
            # Extract ID
            normalized["id"] = (
                conversation_data.get("id")
                or conversation_data.get("conversation_id")
                or conversation_data.get("session_id")
                or ""
            )

            # Extract title
            normalized["title"] = (
                conversation_data.get("title")
                or conversation_data.get("name")
                or "Untitled Conversation"
            )

            # Extract content
            normalized["content"] = extract_conversation_content(conversation_data)

            # Extract messages
            if "messages" in conversation_data:
                normalized["messages"] = conversation_data["messages"]
                normalized["source"] = "claude_code"
            elif "composerSteps" in conversation_data:
                normalized["messages"] = conversation_data["composerSteps"]
                normalized["source"] = "cursor"

            # Extract metadata
            normalized["metadata"] = extract_conversation_metadata(conversation_data)

        elif isinstance(conversation_data, list):
            # Handle list of messages
            normalized["messages"] = conversation_data
            normalized["content"] = extract_conversation_content(conversation_data)

        elif isinstance(conversation_data, str):
            # Handle string content
            normalized["content"] = conversation_data

    except (KeyError, TypeError, AttributeError) as e:
        log_debug(f"Error normalizing conversation format: {e}")

    return normalized


def filter_conversations_by_date(
    conversations: list[dict[str, Any]],
    days_lookback: int,
    date_field_mappings: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Filter conversations by date with IDE-agnostic date field handling."""
    if not conversations or days_lookback <= 0:
        return conversations

    cutoff_date = datetime.now() - timedelta(days=days_lookback)
    filtered = []

    # Default date field mappings
    if date_field_mappings is None:
        date_field_mappings = {
            "cursor": "lastUpdatedAt",
            "claude_code": "start_time",
        }

    for conv in conversations:
        try:
            # Try different date field formats
            timestamp = None

            # Cursor format (milliseconds timestamp)
            if "lastUpdatedAt" in conv:
                timestamp = datetime.fromtimestamp(conv["lastUpdatedAt"] / 1000)

            # Claude Code format (ISO string)
            elif "session_metadata" in conv:
                session_meta = conv["session_metadata"]
                if "start_time" in session_meta:
                    start_time_str = session_meta["start_time"]
                    if start_time_str:
                        timestamp = datetime.fromisoformat(
                            start_time_str.replace("Z", "+00:00")
                        )

            # Direct timestamp field
            elif "timestamp" in conv:
                ts = conv["timestamp"]
                if isinstance(ts, int | float):
                    # Handle both seconds and milliseconds timestamps
                    if ts > 1e10:  # Likely milliseconds
                        timestamp = datetime.fromtimestamp(ts / 1000)
                    else:  # Likely seconds
                        timestamp = datetime.fromtimestamp(ts)
                elif isinstance(ts, str):
                    timestamp = datetime.fromisoformat(ts.replace("Z", "+00:00"))

            # Created/updated date fields
            elif "created_at" in conv:
                created_at = conv["created_at"]
                if isinstance(created_at, str):
                    timestamp = datetime.fromisoformat(
                        created_at.replace("Z", "+00:00")
                    )
                elif isinstance(created_at, int | float):
                    timestamp = datetime.fromtimestamp(created_at)

            # Include if timestamp is recent enough or if no timestamp available
            if timestamp is None or timestamp >= cutoff_date:
                filtered.append(conv)

        except (ValueError, TypeError, KeyError):
            # Include conversations with invalid/missing timestamps
            filtered.append(conv)

    return filtered


def sort_conversations_by_relevance(
    conversations: list[dict[str, Any]], relevance_key: str = "relevance_score"
) -> list[dict[str, Any]]:
    """Sort conversations by relevance score in descending order."""
    try:
        return sorted(
            conversations,
            key=lambda x: x.get(relevance_key, 0.0),
            reverse=True,
        )
    except (TypeError, KeyError):
        return conversations


def extract_conversation_summary(conversation_data: Any, max_length: int = 200) -> str:
    """Extract a brief summary from conversation content."""
    content = extract_conversation_content(conversation_data)

    if not content:
        return "No content available"

    # Remove extra whitespace
    content = " ".join(content.split())

    if len(content) <= max_length:
        return content

    # Try to cut at sentence boundary
    sentences = content.split(". ")
    summary = ""

    for sentence in sentences:
        if len(summary + sentence + ". ") <= max_length:
            summary += sentence + ". "
        else:
            break

    if summary:
        return summary.strip()

    # Fallback to word boundary
    words = content.split()
    summary = ""

    for word in words:
        if len(summary + word + " ") <= max_length:
            summary += word + " "
        else:
            break

    return (summary.strip() + "...") if summary else content[:max_length] + "..."


def get_conversation_statistics(conversations: list[dict[str, Any]]) -> dict[str, Any]:
    """Get statistics about a collection of conversations."""
    if not conversations:
        return {
            "total_conversations": 0,
            "total_messages": 0,
            "average_length": 0,
            "date_range": None,
        }

    total_messages = 0
    total_length = 0
    dates = []

    for conv in conversations:
        # Count messages
        if "messages" in conv:
            messages = conv["messages"]
            if isinstance(messages, list):
                total_messages += len(messages)

        # Calculate content length
        content = extract_conversation_content(conv)
        total_length += len(content)

        # Extract dates
        metadata = extract_conversation_metadata(conv)
        for date_field in ["created_at", "timestamp", "lastUpdatedAt", "start_time"]:
            if date_field in metadata:
                try:
                    if isinstance(metadata[date_field], str):
                        date = datetime.fromisoformat(
                            metadata[date_field].replace("Z", "+00:00")
                        )
                        dates.append(date)
                    elif isinstance(metadata[date_field], int | float):
                        timestamp = metadata[date_field]
                        if timestamp > 1e10:  # Milliseconds
                            timestamp = timestamp / 1000
                        date = datetime.fromtimestamp(timestamp)
                        dates.append(date)
                    break
                except (ValueError, TypeError):
                    continue

    date_range = None
    if dates:
        dates.sort()
        date_range = {
            "earliest": dates[0].isoformat(),
            "latest": dates[-1].isoformat(),
            "span_days": (dates[-1] - dates[0]).days,
        }

    return {
        "total_conversations": len(conversations),
        "total_messages": total_messages,
        "average_length": total_length // len(conversations) if conversations else 0,
        "average_messages": total_messages // len(conversations)
        if conversations
        else 0,
        "date_range": date_range,
    }

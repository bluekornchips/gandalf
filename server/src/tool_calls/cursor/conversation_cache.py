"""
Conversation caching utilities for Cursor IDE conversations.

This module handles caching of conversation data to improve performance
and reduce database queries.
"""

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from src.config.constants.cache import (
    CONVERSATION_CACHE_MIN_SIZE,
    CONVERSATION_CACHE_TTL_HOURS,
)
from src.tool_calls.cursor.conversation_formatter import (
    format_conversation_summary,
    format_lightweight_conversations,
)
from src.utils.access_control import AccessValidator
from src.utils.common import format_json_response, log_debug, log_error, log_info


def get_project_cache_hash(project_root: Path, context_keywords: list[str]) -> str:
    """Generate cache hash for project and context."""
    # Create cache key from project path and sorted keywords
    cache_elements = [
        str(project_root.resolve()),
        "|".join(sorted(context_keywords)),
    ]

    cache_string = "|".join(cache_elements)
    cache_hash = hashlib.sha256(cache_string.encode()).hexdigest()[:16]

    log_debug(f"Generated cache hash: {cache_hash} for project: {project_root}")
    return cache_hash


def is_cache_valid(project_root: Path, context_keywords: list[str]) -> bool:
    """Check if cached conversations are still valid."""
    try:
        # Use project-specific cache files
        cache_file = project_root / "conversations.json"
        metadata_file = project_root / "metadata.json"

        if not cache_file.exists() or not metadata_file.exists():
            return False

        # Check metadata
        with open(metadata_file) as f:
            metadata = json.load(f)

        # Check age
        cache_age_hours = (time.time() - metadata.get("timestamp", 0)) / 3600
        if cache_age_hours > CONVERSATION_CACHE_TTL_HOURS:
            log_debug(
                f"Cache expired: {cache_age_hours:.1f}h > {CONVERSATION_CACHE_TTL_HOURS}h"
            )
            return False

        # Check context hash
        expected_hash = get_project_cache_hash(project_root, context_keywords)
        if metadata.get("context_hash") != expected_hash:
            log_debug("Cache context hash mismatch")
            return False

        # Check minimum size
        cache_size = cache_file.stat().st_size
        if cache_size < CONVERSATION_CACHE_MIN_SIZE:
            log_debug(f"Cache too small: {cache_size} < {CONVERSATION_CACHE_MIN_SIZE}")
            return False

        log_debug(f"Cache valid: age={cache_age_hours:.1f}h, size={cache_size}")
        return True

    except (OSError, json.JSONDecodeError, KeyError) as e:
        log_debug(f"Cache validation failed: {e}")
        return False


def load_cached_conversations(project_root: Path) -> dict[str, Any] | None:
    """Load conversations from cache if available."""
    try:
        # Use project-specific cache file, not global cache
        cache_file = project_root / "conversations.json"

        if not cache_file.exists():
            return None

        with open(cache_file) as f:
            cached_data = json.load(f)

        # Validate that we got a dict
        if not isinstance(cached_data, dict):
            log_error(
                ValueError("Cache file contains invalid data"),
                f"Expected dict, got {type(cached_data)}",
            )
            return None

        log_info(
            f"Loaded {len(cached_data.get('conversations', []))} conversations from cache"
        )
        return cached_data

    except (OSError, json.JSONDecodeError) as e:
        log_error(e, "Failed to load cached conversations")
        return None


def save_conversations_to_cache(
    project_root: Path,
    conversations: list[dict[str, Any]],
    context_keywords: list[str],
    processing_time: float,
    total_found: int,
) -> None:
    """Save conversations to cache for faster future access."""
    try:
        # Use project-specific cache files
        cache_file = project_root / "conversations.json"
        metadata_file = project_root / "metadata.json"

        # Prepare cache data
        cache_data = {
            "conversations": conversations,
            "total_found": total_found,
            "processing_time": processing_time,
            "cached_at": time.time(),
        }

        # Prepare metadata
        metadata = {
            "timestamp": time.time(),
            "context_hash": get_project_cache_hash(project_root, context_keywords),
            "conversation_count": len(conversations),
            "total_found": total_found,
            "processing_time": processing_time,
        }

        # Create cache directory if it doesn't exist
        cache_file.parent.mkdir(parents=True, exist_ok=True)

        # Write cache file
        with open(cache_file, "w") as f:
            json.dump(cache_data, f, indent=2, default=str)

        # Write metadata file
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

        cache_size = cache_file.stat().st_size
        log_info(
            f"Cached {len(conversations)} conversations "
            f"({cache_size} bytes) for project: {project_root.name}"
        )

    except (OSError, TypeError) as e:
        log_error(e, "Failed to save conversations to cache")


def clear_cache(project_root: Path) -> bool:
    """Clear cached conversations for a project."""
    try:
        cache_file = project_root / "conversations.json"
        metadata_file = project_root / "metadata.json"

        removed_files = 0

        if cache_file.exists():
            cache_file.unlink()
            removed_files += 1

        if metadata_file.exists():
            metadata_file.unlink()
            removed_files += 1

        if removed_files > 0:
            log_info(
                f"Cleared {removed_files} cache files for project: {project_root.name}"
            )

        return removed_files > 0

    except OSError as e:
        log_error(e, "Failed to clear cache")
        return False


def get_cache_info(project_root: Path) -> dict[str, Any]:
    """Get information about current cache status."""
    cache_file = project_root / "conversations.json"
    metadata_file = project_root / "metadata.json"

    info = {
        "cache_exists": cache_file.exists(),
        "metadata_exists": metadata_file.exists(),
        "cache_size": 0,
        "cache_age_hours": 0,
        "conversation_count": 0,
    }

    try:
        if cache_file.exists():
            info["cache_size"] = cache_file.stat().st_size

        if metadata_file.exists():
            with open(metadata_file) as f:
                metadata = json.load(f)

            info["cache_age_hours"] = (
                time.time() - metadata.get("timestamp", 0)
            ) / 3600
            info["conversation_count"] = metadata.get("conversation_count", 0)
            info["context_hash"] = metadata.get("context_hash", "")

    except (OSError, json.JSONDecodeError):
        pass

    return info


def load_from_cache_filtered(
    project_root: Path,
    limit: int,
    min_relevance_score: float,
    days_lookback: int,
    conversation_types: list[str],
    context_keywords: list[str],
) -> dict[str, Any] | None:
    """Load and filter conversations from cache."""
    log_info("Loading conversations from cache...")
    cached_data = load_cached_conversations(project_root)
    if not cached_data:
        return None

    cached_conversations = cached_data.get("conversations", [])

    # Apply current filters to cached data
    filtered_cached = []
    for conv in cached_conversations:
        # Apply relevance score filter
        if (
            conv.get("relevance_score", 0) >= min_relevance_score
            or conv.get("relevance_score", 0) == 0
        ):
            # Apply conversation type filter
            if (
                not conversation_types
                or conv.get("conversation_type") in conversation_types
            ):
                filtered_cached.append(conv)

    # Return cached results if sufficient
    if len(filtered_cached) >= limit:
        result_conversations = filtered_cached[:limit]

        # Format as lightweight conversations
        lightweight_conversations = format_lightweight_conversations(
            result_conversations
        )

        result = format_conversation_summary(
            lightweight_conversations,
            len(filtered_cached),
            {
                "cache_hit": True,
                "processing_time": cached_data.get("processing_time", 0),
                "context_keywords": context_keywords[:15],
            },
        )

        log_info(f"Returned {len(result_conversations)} cached conversations")
        return AccessValidator.create_success_response(format_json_response(result))

    return None

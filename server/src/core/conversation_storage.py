"""
Core conversation storage and caching functionality for Gandalf MCP server.
Handles conversation data persistence, validation, and context keyword
generation.
"""

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.cache import (
    CONVERSATION_CACHE_DIR,
    CONVERSATION_CACHE_FILE,
    CONVERSATION_CACHE_MAX_SIZE_MB,
    CONVERSATION_CACHE_METADATA_FILE,
    CONVERSATION_CACHE_MIN_SIZE,
    CONVERSATION_CACHE_TTL_HOURS,
)
from core.conversation_analysis import generate_shared_context_keywords
from utils.common import log_debug, log_error, log_info


def get_storage_directory() -> Path:
    """
    Get or create the storage directory for conversations in GANDALF_HOME.
    """
    storage_dir = CONVERSATION_CACHE_DIR
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir


def get_storage_file_path() -> Path:
    """Get the full path to the conversation storage file in GANDALF_HOME."""
    return CONVERSATION_CACHE_FILE


def get_storage_metadata_path(project_root: Path) -> Path:
    """Get the full path to the storage metadata file in GANDALF_HOME."""
    return CONVERSATION_CACHE_METADATA_FILE


def get_project_storage_hash(project_root: Path, context_keywords: List[str]) -> str:
    """Generate a storage hash based on project state and keywords."""
    try:
        # Include project path, git state, and keywords in hash
        hash_input = str(project_root)

        # Add git HEAD if available
        git_head = project_root / ".git" / "HEAD"
        if git_head.exists():
            hash_input += git_head.read_text().strip()

        # Add context keywords
        hash_input += "".join(sorted(context_keywords))

        return hashlib.md5(hash_input.encode()).hexdigest()[:16]
    except (OSError, ValueError, UnicodeDecodeError):
        try:
            fallback_input = f"{project_root}{time.time()}"
        except (OSError, ValueError, TypeError):
            # if everything fails, we at least have each other as fallback
            fallback_input = f"fallback{time.time()}"
        return hashlib.md5(fallback_input.encode()).hexdigest()[:16]


def is_storage_valid(project_root: Path, context_keywords: List[str]) -> bool:
    """Check if the conversation storage is valid and up to date."""
    try:
        metadata_path = get_storage_metadata_path(project_root)
        storage_file_path = get_storage_file_path()

        if not metadata_path.exists() or not storage_file_path.exists():
            return False

        # Check storage file size
        storage_size_mb = storage_file_path.stat().st_size / (1024 * 1024)
        if storage_size_mb > CONVERSATION_CACHE_MAX_SIZE_MB:
            log_debug(f"Storage file too large: {storage_size_mb:.1f}MB")
            return False

        # Load and validate metadata
        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        # Check TTL
        storage_age_hours = (time.time() - metadata.get("timestamp", 0)) / 3600
        if storage_age_hours > CONVERSATION_CACHE_TTL_HOURS:
            log_debug(f"Storage expired: {storage_age_hours:.1f} hours old")
            return False

        # Check project hash
        current_hash = get_project_storage_hash(project_root, context_keywords)
        if metadata.get("project_hash") != current_hash:
            log_debug("Project state changed, storage invalid")
            return False

        return True

    except (OSError, json.JSONDecodeError, ValueError, KeyError) as e:
        log_debug(f"Storage validation error: {e}")
        return False


def load_stored_conversations(project_root: Path) -> Optional[Dict[str, Any]]:
    """Load conversations from storage if valid."""
    try:
        storage_file_path = get_storage_file_path()

        if not storage_file_path.exists():
            return None

        with open(storage_file_path, "r") as f:
            stored_data = json.load(f)

        conversation_count = len(stored_data.get("conversations", []))
        log_info(f"Loaded {conversation_count} conversations from storage")
        return stored_data

    except (OSError, json.JSONDecodeError, ValueError) as e:
        log_error(e, "loading stored conversations")
        return None


def save_conversations_to_storage(
    project_root: Path,
    conversations: List[Dict[str, Any]],
    context_keywords: List[str],
    metadata: Dict[str, Any],
) -> bool:
    """Save conversations to local storage with metadata."""
    try:
        if len(conversations) < CONVERSATION_CACHE_MIN_SIZE:
            log_debug(f"Not storing - too few conversations: {len(conversations)}")
            return False

        storage_file_path = get_storage_file_path()
        metadata_path = get_storage_metadata_path(project_root)

        # Prepare storage data
        storage_data = {
            "conversations": conversations,
            "metadata": metadata,
            "stored_at": time.time(),
        }

        # Save conversations
        with open(storage_file_path, "w") as f:
            json.dump(storage_data, f, indent=2)

        # Save metadata
        storage_metadata = {
            "timestamp": time.time(),
            "project_hash": get_project_storage_hash(project_root, context_keywords),
            "conversation_count": len(conversations),
            "context_keywords": context_keywords,
            "search_metadata": metadata,
        }

        with open(metadata_path, "w") as f:
            json.dump(storage_metadata, f, indent=2)

        # Verify file size
        storage_size_mb = storage_file_path.stat().st_size / (1024 * 1024)
        log_info(
            f"Stored {len(conversations)} conversations " f"({storage_size_mb:.1f}MB)"
        )

        return True

    except (OSError, json.JSONDecodeError, ValueError, TypeError) as e:
        log_error(e, "saving conversations to storage")
        return False


# Use shared implementation from conversation_analysis module
generate_context_keywords = generate_shared_context_keywords


def clear_conversation_storage():
    """Clear all conversation storage and reset caches."""
    log_debug("Cleared conversation storage caches")


def get_conversation_storage_info() -> Dict[str, Any]:
    """Get information about conversation storage state."""
    storage_file = get_storage_file_path()
    metadata_file = get_storage_metadata_path(Path.cwd())  # Default path

    info = {
        "storage_file_exists": storage_file.exists(),
        "metadata_file_exists": metadata_file.exists(),
        "cache_entries": 0,
        "keyword_cache_entries": 0,
    }

    if storage_file.exists():
        info["storage_file_size_mb"] = storage_file.stat().st_size / (1024 * 1024)

    return info

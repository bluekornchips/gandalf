"""
Core conversation storage and caching functionality for Gandalf MCP server.
Handles conversation data persistence, validation, and context keyword generation.
"""

import hashlib
import json
import time
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.constants.conversations import (
    CONTEXT_KEYWORD_MAX_COUNT,
    CONTEXT_TECH_WEIGHT_MULTIPLIER,
    CONTEXT_PROJECT_WEIGHT_MULTIPLIER,
)
from config.cache import (
    CONVERSATION_CACHE_DIR,
    CONVERSATION_CACHE_FILE,
    CONVERSATION_CACHE_METADATA_FILE,
    CONVERSATION_CACHE_TTL_HOURS,
    CONVERSATION_CACHE_MIN_SIZE,
    CONVERSATION_CACHE_MAX_SIZE_MB,
)
from config.constants.technology import (
    TECHNOLOGY_EXTENSION_MAPPING,
    TECHNOLOGY_KEYWORD_MAPPING,
)
from src.utils.common import log_debug, log_info, log_error
from src.core.file_scoring import get_files_list


# Global storage for context keywords and conversation data
_context_keywords_storage = {}
_context_keywords_timestamp = {}
_conversation_storage = {}
_conversation_storage_timestamp = {}
CONTEXT_STORAGE_TTL = 300  # 5 minutes


def get_storage_directory() -> Path:
    """Get or create the storage directory for conversations in GANDALF_HOME."""
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
        return hashlib.md5(f"{project_root}{time.time()}".encode()).hexdigest()[:16]


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

        log_info(
            f"Loaded {len(stored_data.get('conversations', []))} conversations from storage"
        )
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

        storage_dir = get_storage_directory()
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
        log_info(f"Stored {len(conversations)} conversations ({storage_size_mb:.1f}MB)")

        return True

    except (OSError, json.JSONEncodeError, ValueError, TypeError) as e:
        log_error(e, "saving conversations to storage")
        return False


def get_project_hash(project_root: Path) -> str:
    """Generate a hash for the project to use in storage."""
    try:
        # Use project path and modification time of key files
        hash_input = str(project_root)

        # Add git head if available
        git_head = project_root / ".git" / "HEAD"
        if git_head.exists():
            hash_input += git_head.read_text().strip()

        return hashlib.md5(hash_input.encode()).hexdigest()[:12]
    except (OSError, UnicodeDecodeError):
        return hashlib.md5(str(project_root).encode()).hexdigest()[:12]


@lru_cache(maxsize=32)
def get_enhanced_context_keywords(
    project_root_str: str, project_hash: str
) -> List[str]:
    """Enhanced context keyword generation with intelligent filtering."""
    project_root = Path(project_root_str)
    keyword_weights = {}  # Track keyword importance

    # 1. Project name (highest weight)
    project_name = project_root.name
    keyword_weights[project_name] = CONTEXT_PROJECT_WEIGHT_MULTIPLIER * 10

    try:
        # 2. Get top files with relevance scoring
        files = get_files_list(project_root)[:40]  # More files for better context

        for i, file_path in enumerate(files):
            file_path_obj = Path(file_path)

            # Weight files by their position in relevance (earlier = more important)
            position_weight = max(1.0, (40 - i) / 40)

            # Add filename without extension
            file_name = file_path_obj.stem
            if len(file_name) > 2 and not file_name.startswith("."):
                keyword_weights[file_name] = (
                    keyword_weights.get(file_name, 0) + position_weight * 2
                )

            # Add directory names
            for dir_part in file_path_obj.parts[:-1]:
                if (
                    len(dir_part) > 2
                    and not dir_part.startswith(".")
                    and dir_part not in ["src", "lib", "app", "components"]
                ):
                    keyword_weights[dir_part] = (
                        keyword_weights.get(dir_part, 0) + position_weight * 1.5
                    )

        # 3. Technology-based keywords from file extensions
        extensions = set()
        for file_path in files[:50]:  # Limit for performance
            ext = Path(file_path).suffix.lower()
            if ext and len(ext) > 1:
                clean_ext = ext[1:]  # Remove dot
                extensions.add(clean_ext)

        # Convert common extensions to technology names
        for ext in extensions:
            tech_name = TECHNOLOGY_EXTENSION_MAPPING.get(ext, ext)
            keyword_weights[tech_name] = (
                keyword_weights.get(tech_name, 0) + CONTEXT_TECH_WEIGHT_MULTIPLIER * 3
            )

            # Also add specific technology keywords if available
            if ext in TECHNOLOGY_KEYWORD_MAPPING:
                for tech_keyword in TECHNOLOGY_KEYWORD_MAPPING[ext]:
                    keyword_weights[tech_keyword] = (
                        keyword_weights.get(tech_keyword, 0)
                        + CONTEXT_TECH_WEIGHT_MULTIPLIER
                    )

    except (OSError, ValueError, AttributeError) as e:
        log_debug(f"Error generating enhanced context keywords: {e}")

    # Sort by weight and return top keywords
    sorted_keywords = sorted(keyword_weights.items(), key=lambda x: x[1], reverse=True)[
        :CONTEXT_KEYWORD_MAX_COUNT
    ]

    keywords = [kw for kw, weight in sorted_keywords]
    log_debug(f"Generated {len(keywords)} context keywords for {project_root}")

    return keywords


def generate_context_keywords(project_root: Path) -> List[str]:
    """Generate context keywords with storage."""
    storage_key = str(project_root)
    current_time = time.time()

    # Check if stored and still valid
    if (
        storage_key in _context_keywords_storage
        and storage_key in _context_keywords_timestamp
        and current_time - _context_keywords_timestamp[storage_key]
        < CONTEXT_STORAGE_TTL
    ):
        return _context_keywords_storage[storage_key]

    # Generate new keywords
    project_hash = get_project_hash(project_root)
    keywords = get_enhanced_context_keywords(str(project_root), project_hash)

    # Store the result
    _context_keywords_storage[storage_key] = keywords
    _context_keywords_timestamp[storage_key] = current_time

    # Clean up old storage entries
    for key in list(_context_keywords_timestamp.keys()):
        if current_time - _context_keywords_timestamp[key] > CONTEXT_STORAGE_TTL:
            _context_keywords_storage.pop(key, None)
            _context_keywords_timestamp.pop(key, None)

    return keywords


def clear_conversation_storage():
    """Clear all conversation storage."""
    global _context_keywords_storage, _context_keywords_timestamp
    global _conversation_storage, _conversation_storage_timestamp

    _context_keywords_storage.clear()
    _context_keywords_timestamp.clear()
    _conversation_storage.clear()
    _conversation_storage_timestamp.clear()

    log_debug("Cleared all conversation storage")


def get_conversation_storage_info() -> Dict[str, Any]:
    """Get conversation storage information for debugging."""
    current_time = time.time()

    return {
        "context_keywords_storage_size": len(_context_keywords_storage),
        "conversation_storage_size": len(_conversation_storage),
        "oldest_context_storage_age": (
            min(current_time - t for t in _context_keywords_timestamp.values())
            if _context_keywords_timestamp
            else 0
        ),
        "newest_context_storage_age": (
            max(current_time - t for t in _context_keywords_timestamp.values())
            if _context_keywords_timestamp
            else 0
        ),
        "context_storage_ttl": CONTEXT_STORAGE_TTL,
    }

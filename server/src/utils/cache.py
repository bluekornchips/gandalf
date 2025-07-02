"""
Cache utilities for the Gandalf MCP server.
"""

from pathlib import Path

from config.cache import (
    CACHE_ROOT_DIR,
    CONVERSATION_CACHE_DIR,
    FILE_CACHE_DIR,
    GIT_CACHE_DIR,
)


def get_cache_directory() -> Path:
    """Ensure cache directory exists and return the path."""
    CACHE_ROOT_DIR.mkdir(parents=True, exist_ok=True)
    CONVERSATION_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    FILE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    GIT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_ROOT_DIR

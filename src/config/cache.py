"""
Cache configuration constants for Gandalf MCP server.
"""

from src.config.constants.core import GANDALF_HOME

# Cache Directory Structure

# Main cache directories
CACHE_ROOT_DIR = GANDALF_HOME / "cache"
CONVERSATION_CACHE_DIR = CACHE_ROOT_DIR / "conversations"
FILE_CACHE_DIR = CACHE_ROOT_DIR / "files"
GIT_CACHE_DIR = CACHE_ROOT_DIR / "git"

# Cache File Paths

# Conversation cache files
CONVERSATION_CACHE_FILE = CONVERSATION_CACHE_DIR / "conversations.json"
CONVERSATION_CACHE_METADATA_FILE = CONVERSATION_CACHE_DIR / "metadata.json"

# Cache TTL Settings

# Cache time-to-live settings in seconds
CONVERSATION_CACHE_TTL_HOURS = 4  # Cache valid for 4 hours
CONVERSATION_CACHE_TTL_SECONDS = CONVERSATION_CACHE_TTL_HOURS * 3600

# Context keyword cache TTL
CONTEXT_CACHE_TTL_SECONDS = 300  # 5 minutes

# Git activity cache TTL
CONTEXT_GIT_CACHE_TTL = 3600  # 1 hour

# General MCP cache TTL
MCP_CACHE_TTL = 3600  # 1 hour

# Cache Size Limits

# Conversation cache limits
CONVERSATION_CACHE_MIN_SIZE = 5  # Minimum conversations to cache
CONVERSATION_CACHE_MAX_SIZE_MB = 10  # Maximum cache file size in MB

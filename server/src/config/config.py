"""
Simplified configuration module for Gandalf MCP server.
Provides easy access to all configuration constants and settings.
"""

from typing import Any, Dict

from config import weights
from config.constants import (
    # Core configuration
    MCP_SERVER_NAME,
    GANDALF_HOME,
    MCP_PROTOCOL_VERSION,
    GANDALF_SERVER_VERSION,
    SERVER_INFO,
    SERVER_CAPABILITIES,
    WORKSPACE_FOLDER_PATHS,
    # System limits
    MAX_PROJECT_FILES,
    MAX_FILE_SIZE_BYTES,
    MAX_STRING_LENGTH,
    MAX_ARRAY_LENGTH,
    MAX_QUERY_LENGTH,
    MAX_PATH_DEPTH,
    RECENT_FILE_COUNT_LIMIT,
    # Cache configuration
    CACHE_ROOT_DIR,
    CONVERSATION_CACHE_DIR,
    FILE_CACHE_DIR,
    GIT_CACHE_DIR,
    CONVERSATION_CACHE_FILE,
    CONVERSATION_CACHE_METADATA_FILE,
    CONVERSATION_CACHE_TTL_SECONDS,
    CONTEXT_CACHE_TTL_SECONDS,
    CONTEXT_GIT_CACHE_TTL,
    MCP_CACHE_TTL,
    # Conversation processing
    DEFAULT_FAST_MODE,
    CONVERSATION_DEFAULT_RECENT_DAYS,
    CONVERSATION_DEFAULT_LIMIT,
    CONVERSATION_DEFAULT_MIN_SCORE,
    CONVERSATION_MAX_LIMIT,
    CONVERSATION_MAX_LOOKBACK_DAYS,
    CONVERSATION_BATCH_SIZE,
    # File filtering
    EXCLUDE_DIRECTORIES,
    EXCLUDE_FILE_PATTERNS,
    BLOCKED_EXTENSIONS,
    BLOCKED_PATHS,
    # Agentic tools
    SUPPORTED_AGENTIC_TOOLS,
    CURSOR_LOCATIONS,
    CLAUDE_CODE_LOCATIONS,
    CURSOR_DB_PATTERNS,
    CLAUDE_CONVERSATION_PATTERNS,
    # Technology mapping
    TECHNOLOGY_EXTENSION_MAPPING,
    TECHNOLOGY_KEYWORD_MAPPING,
)


class Config:
    """
    Simplified configuration accessor.

    Provides easy access to all configuration values without the complexity
    of the previous multi-file structure.
    """

    def __init__(self):
        """Initialize the configuration."""
        self._weights_loader = weights._weights_loader

    @property
    def core(self) -> Dict[str, Any]:
        """Get core server configuration."""
        return {
            "server_name": MCP_SERVER_NAME,
            "gandalf_home": GANDALF_HOME,
            "protocol_version": MCP_PROTOCOL_VERSION,
            "server_version": GANDALF_SERVER_VERSION,
            "server_info": SERVER_INFO,
            "server_capabilities": SERVER_CAPABILITIES,
            "workspace_folder_paths": WORKSPACE_FOLDER_PATHS,
        }

    @property
    def limits(self) -> Dict[str, Any]:
        """Get system limits and thresholds."""
        return {
            "max_project_files": MAX_PROJECT_FILES,
            "max_file_size_bytes": MAX_FILE_SIZE_BYTES,
            "max_string_length": MAX_STRING_LENGTH,
            "max_array_length": MAX_ARRAY_LENGTH,
            "max_query_length": MAX_QUERY_LENGTH,
            "max_path_depth": MAX_PATH_DEPTH,
            "recent_file_count_limit": RECENT_FILE_COUNT_LIMIT,
        }

    @property
    def cache(self) -> Dict[str, Any]:
        """Get cache configuration."""
        return {
            "directories": {
                "cache_root": CACHE_ROOT_DIR,
                "conversation_cache": CONVERSATION_CACHE_DIR,
                "file_cache": FILE_CACHE_DIR,
                "git_cache": GIT_CACHE_DIR,
            },
            "files": {
                "conversation_cache": CONVERSATION_CACHE_FILE,
                "conversation_metadata": CONVERSATION_CACHE_METADATA_FILE,
            },
            "ttl": {
                "conversation_cache_seconds": CONVERSATION_CACHE_TTL_SECONDS,
                "context_cache_seconds": CONTEXT_CACHE_TTL_SECONDS,
                "git_cache_seconds": CONTEXT_GIT_CACHE_TTL,
                "mcp_cache_seconds": MCP_CACHE_TTL,
            },
        }

    @property
    def conversation(self) -> Dict[str, Any]:
        """Get conversation processing configuration."""
        return {
            "default_fast_mode": DEFAULT_FAST_MODE,
            "default_recent_days": CONVERSATION_DEFAULT_RECENT_DAYS,
            "default_limit": CONVERSATION_DEFAULT_LIMIT,
            "default_min_score": CONVERSATION_DEFAULT_MIN_SCORE,
            "max_limit": CONVERSATION_MAX_LIMIT,
            "max_lookback_days": CONVERSATION_MAX_LOOKBACK_DAYS,
            "batch_size": CONVERSATION_BATCH_SIZE,
        }

    @property
    def filtering(self) -> Dict[str, Any]:
        """Get file filtering configuration."""
        return {
            "exclude_directories": EXCLUDE_DIRECTORIES,
            "exclude_file_patterns": EXCLUDE_FILE_PATTERNS,
            "blocked_extensions": BLOCKED_EXTENSIONS,
            "blocked_paths": BLOCKED_PATHS,
        }

    @property
    def agentic_tools(self) -> Dict[str, Any]:
        """Get agentic tool configuration."""
        return {
            "supported_tools": SUPPORTED_AGENTIC_TOOLS,
            "cursor_locations": CURSOR_LOCATIONS,
            "claude_code_locations": CLAUDE_CODE_LOCATIONS,
            "cursor_db_patterns": CURSOR_DB_PATTERNS,
            "claude_conversation_patterns": CLAUDE_CONVERSATION_PATTERNS,
        }

    @property
    def technology(self) -> Dict[str, Any]:
        """Get technology mapping configuration."""
        return {
            "extension_mapping": TECHNOLOGY_EXTENSION_MAPPING,
            "keyword_mapping": TECHNOLOGY_KEYWORD_MAPPING,
        }

    @property
    def weights(self) -> Dict[str, Any]:
        """Get scoring weights configuration."""
        return {
            "context_weights": weights.CONTEXT_WEIGHTS,
            "conversation_weights": weights.CONVERSATION_WEIGHTS,
            "file_extension_weights": weights.get_file_extension_weights(),
            "directory_priority_weights": weights.get_directory_priority_weights(),
        }

    def get_all(self) -> Dict[str, Any]:
        """Get all configuration as a single dictionary."""
        return {
            "core": self.core,
            "limits": self.limits,
            "cache": self.cache,
            "conversation": self.conversation,
            "filtering": self.filtering,
            "agentic_tools": self.agentic_tools,
            "technology": self.technology,
            "weights": self.weights,
        }


# Global configuration instance
config = Config()

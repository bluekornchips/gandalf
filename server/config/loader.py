"""
Configuration loader for Gandalf MCP server.
Provides an interface to access all configuration constants and settings.
"""

from typing import Dict, Any

# Import all constant modules
from config.constants import (
    core,
    security,
    system,
    technology,
    file_filters,
    conversations,
    conversation_patterns,
)

# Import setup modules
from config import weights, cache


class ConfigLoader:
    """
    Unified configuration loader that provides access to all configuration settings.

    This class acts as a single point of access for all configuration values,
    making it easier to manage and modify configuration loading behavior.
    """

    def __init__(self):
        """Initialize the configuration loader."""
        self._weights_loader = weights._weights_loader

    def get_core_config(self) -> Dict[str, Any]:
        """Get core server configuration."""
        return {
            "server_name": core.MCP_SERVER_NAME,
            "gandalf_home": core.GANDALF_HOME,
            "protocol_version": core.MCP_PROTOCOL_VERSION,
            "server_version": core.SERVER_VERSION,
            "server_info": core.SERVER_INFO,
            "server_capabilities": core.SERVER_CAPABILITIES,
            "workspace_folder_paths": core.WORKSPACE_FOLDER_PATHS,
        }

    def get_security_config(self) -> Dict[str, Any]:
        """Get security configuration."""
        return {
            "max_string_length": security.SECURITY_MAX_STRING_LENGTH,
            "max_array_length": security.SECURITY_MAX_ARRAY_LENGTH,
            "max_query_length": security.SECURITY_MAX_QUERY_LENGTH,
            "max_path_depth": security.SECURITY_MAX_PATH_DEPTH,
            "blocked_paths": security.SECURITY_BLOCKED_PATHS,
            "safe_extensions": security.SECURITY_SAFE_EXTENSIONS,
        }

    def get_system_config(self) -> Dict[str, Any]:
        """Get system constants configuration."""
        return {
            "display_limits": {
                "max_high_priority": system.MAX_HIGH_PRIORITY_DISPLAY,
                "max_medium_priority": system.MAX_MEDIUM_PRIORITY_DISPLAY,
                "max_top_files": system.MAX_TOP_FILES_DISPLAY,
            },
            "scoring_thresholds": {
                "context_high_priority": system.CONTEXT_HIGH_PRIORITY_THRESHOLD,
                "context_medium_priority": system.CONTEXT_MEDIUM_PRIORITY_THRESHOLD,
                "priority_high": system.PRIORITY_HIGH_THRESHOLD,
                "priority_medium": system.PRIORITY_MEDIUM_THRESHOLD,
                "priority_neutral": system.PRIORITY_NEUTRAL_SCORE,
            },
            "performance": {
                "context_min_score": system.CONTEXT_MIN_SCORE,
                "git_cache_ttl": system.CONTEXT_GIT_CACHE_TTL,
                "git_lookback_days": system.CONTEXT_GIT_LOOKBACK_DAYS,
                "git_timeout": system.CONTEXT_GIT_TIMEOUT,
            },
            "file_limits": {
                "max_project_files": system.MAX_PROJECT_FILES,
                "max_file_size_bytes": system.MAX_FILE_SIZE_BYTES,
                "recent_file_count_limit": system.RECENT_FILE_COUNT_LIMIT,
            },
            "conversation_limits": {
                "default_limit": system.CONVERSATION_DEFAULT_LIMIT,
                "max_limit": system.CONVERSATION_MAX_LIMIT,
                "default_lookback_days": system.CONVERSATION_DEFAULT_LOOKBACK_DAYS,
                "max_lookback_days": system.CONVERSATION_MAX_LOOKBACK_DAYS,
            },
        }

    def get_technology_config(self) -> Dict[str, Any]:
        """Get technology mapping configuration."""
        return {
            "extension_mapping": technology.TECHNOLOGY_EXTENSION_MAPPING,
            "keyword_mapping": technology.TECHNOLOGY_KEYWORD_MAPPING,
        }

    def get_file_filter_config(self) -> Dict[str, Any]:
        """Get file filtering configuration."""
        return {
            "exclude_dirs": file_filters.FIND_EXCLUDE_DIRS,
            "exclude_patterns": file_filters.FIND_EXCLUDE_PATTERNS,
        }

    def get_conversation_config(self) -> Dict[str, Any]:
        """Get conversation processing configuration."""
        return {
            "defaults": {
                "recent_days": conversations.CONVERSATION_DEFAULT_RECENT_DAYS,
                "fast_window_days": conversations.CONVERSATION_FAST_WINDOW_DAYS,
            },
            "processing": {
                "batch_size": conversations.CONVERSATION_BATCH_SIZE,
                "early_termination_multiplier": conversations.CONVERSATION_EARLY_TERMINATION_MULTIPLIER,
                "progress_log_interval": conversations.CONVERSATION_PROGRESS_LOG_INTERVAL,
            },
            "filtering": {
                "min_keyword_matches": conversations.FILTER_MIN_KEYWORD_MATCHES,
                "skip_untitled_after_hours": conversations.FILTER_SKIP_UNTITLED_AFTER_HOURS,
                "min_exchange_count": conversations.FILTER_MIN_EXCHANGE_COUNT,
            },
            "context": {
                "keyword_min_relevance": conversations.CONTEXT_KEYWORD_MIN_RELEVANCE,
                "keyword_max_count": conversations.CONTEXT_KEYWORD_MAX_COUNT,
                "tech_weight_multiplier": conversations.CONTEXT_TECH_WEIGHT_MULTIPLIER,
                "project_weight_multiplier": conversations.CONTEXT_PROJECT_WEIGHT_MULTIPLIER,
                "cache_ttl_seconds": conversations.CONTEXT_CACHE_TTL_SECONDS,
            },
        }

    def get_pattern_config(self) -> Dict[str, Any]:
        """Get conversation pattern matching configuration."""
        return {
            "pattern_groups": conversation_patterns.CONVERSATION_PATTERN_GROUPS,
            "architecture_keywords": conversation_patterns.ARCHITECTURE_KEYWORDS,
            "debug_keywords": conversation_patterns.DEBUG_KEYWORDS,
            "problem_solving_keywords": conversation_patterns.PROBLEM_SOLVING_KEYWORDS,
            "technical_keywords": conversation_patterns.TECHNICAL_KEYWORDS,
            "code_keywords": conversation_patterns.CODE_KEYWORDS,
        }

    def get_weights_config(self) -> Dict[str, Any]:
        """Get scoring weights configuration."""
        return {
            "context_weights": weights.CONTEXT_WEIGHTS,
            "conversation_weights": weights.CONVERSATION_WEIGHTS,
            "file_extension_weights": weights.get_file_extension_weights(),
            "directory_priority_weights": weights.get_directory_priority_weights(),
        }

    def get_cache_config(self) -> Dict[str, Any]:
        """Get cache configuration."""
        return {
            "directories": {
                "cache_root": cache.CACHE_ROOT_DIR,
                "conversation_cache": cache.CONVERSATION_CACHE_DIR,
                "file_cache": cache.FILE_CACHE_DIR,
                "git_cache": cache.GIT_CACHE_DIR,
            },
            "files": {
                "cached_filenames": cache.CACHED_FILENAMES_FILE,
                "conversation_cache": cache.CONVERSATION_CACHE_FILE,
                "conversation_metadata": cache.CONVERSATION_CACHE_METADATA_FILE,
            },
            "ttl": {
                "conversation_cache_hours": cache.CONVERSATION_CACHE_TTL_HOURS,
                "conversation_cache_seconds": cache.CONVERSATION_CACHE_TTL_SECONDS,
                "context_cache_seconds": cache.CONTEXT_CACHE_TTL_SECONDS,
                "git_cache_seconds": cache.CONTEXT_GIT_CACHE_TTL,
                "mcp_cache_seconds": cache.MCP_CACHE_TTL,
            },
            "limits": {
                "conversation_min_size": cache.CONVERSATION_CACHE_MIN_SIZE,
                "conversation_max_size_mb": cache.CONVERSATION_CACHE_MAX_SIZE_MB,
            },
        }

    def get_all_config(self) -> Dict[str, Any]:
        """Get all configuration as a single dictionary."""
        return {
            "core": self.get_core_config(),
            "security": self.get_security_config(),
            "system": self.get_system_config(),
            "technology": self.get_technology_config(),
            "file_filters": self.get_file_filter_config(),
            "conversations": self.get_conversation_config(),
            "patterns": self.get_pattern_config(),
            "weights": self.get_weights_config(),
            "cache": self.get_cache_config(),
        }

    def reload_weights(self):
        """Reload weights configuration from YAML file."""
        self._weights_loader._weights_loaded = False
        self._weights_loader._weights_config = None


# Global configuration loader instance
config = ConfigLoader()

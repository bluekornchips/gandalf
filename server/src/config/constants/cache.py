"""Cache configuration constants."""

from typing import Final

# Cache time-to-live configurations
CONVERSATION_CACHE_TTL_HOURS: Final[int] = 4
CONVERSATION_CACHE_TTL_SECONDS: Final[int] = CONVERSATION_CACHE_TTL_HOURS * 3600
CONTEXT_CACHE_TTL_SECONDS: Final[int] = 300
CONTEXT_GIT_CACHE_TTL: Final[int] = 3600
MCP_CACHE_TTL: Final[int] = 3600
DATABASE_SCANNER_CACHE_TTL: Final[int] = 300  # 5 minutes

# Cache size and storage limits
CONVERSATION_CACHE_MIN_SIZE: Final[int] = 5
CONVERSATION_CACHE_MAX_SIZE_MB: Final[int] = 10

# Context intelligence cache configuration
CONTEXT_IMPORT_CACHE_TTL: Final[int] = 3600  # 1 hour
CONTEXT_IMPORT_TIMEOUT: Final[int] = 10  # 10 seconds

# Git activity tracking cache configuration
GIT_ACTIVITY_CACHE_TTL: Final[int] = 3600  # 1 hour cache
GIT_ACTIVITY_RECENT_DAYS: Final[int] = 7  # Look back 7 days
GIT_ACTIVITY_MAX_FILES: Final[int] = 1000  # Max files to track
GIT_ACTIVITY_COMMIT_LIMIT: Final[int] = 10  # Timeout for git commands

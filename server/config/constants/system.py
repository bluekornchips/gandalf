"""
System constants configuration for Gandalf MCP server.
Contains fixed thresholds, limits, and system parameters that are not configurable weights.
"""

# Display and UI Limits

# Maximum number of files to display in different priority categories
# These control UI presentation, not AI scoring
MAX_HIGH_PRIORITY_DISPLAY = 5
MAX_MEDIUM_PRIORITY_DISPLAY = 10
MAX_TOP_FILES_DISPLAY = 10

# Scoring Thresholds

# Context intelligence thresholds, these define boundaries for categorization
CONTEXT_HIGH_PRIORITY_THRESHOLD = 5.0
CONTEXT_MEDIUM_PRIORITY_THRESHOLD = 2.0
CONTEXT_TOP_FILES_COUNT = 10

# File relevance scoring thresholds, these define priority boundaries
PRIORITY_HIGH_THRESHOLD = 0.8
PRIORITY_MEDIUM_THRESHOLD = 0.4
PRIORITY_NEUTRAL_SCORE = 0.5  # Default score when relevance scoring is disabled

# System Performance Parameters

# Core scoring parameters
CONTEXT_MIN_SCORE = 0.1  # Minimum score to prevent division by zero
CONTEXT_GIT_CACHE_TTL = 3600
CONTEXT_GIT_LOOKBACK_DAYS = 7
CONTEXT_GIT_TIMEOUT = 10

# File Size Thresholds

# File size scoring parameters
CONTEXT_FILE_SIZE_OPTIMAL_MIN = 1000
CONTEXT_FILE_SIZE_OPTIMAL_MAX = 50000
CONTEXT_FILE_SIZE_ACCEPTABLE_MAX = 200000

# File size multipliers for scoring
CONTEXT_FILE_SIZE_ACCEPTABLE_MULTIPLIER = (
    0.6  # Score multiplier for acceptable size files
)
CONTEXT_FILE_SIZE_LARGE_MULTIPLIER = 0.2  # Score multiplier for large files

# Time-Based Thresholds

# Recent modification time parameters
CONTEXT_RECENT_HOUR_THRESHOLD = 1  # "very recent"
CONTEXT_RECENT_DAY_THRESHOLD = 24  # "recent"
CONTEXT_RECENT_WEEK_THRESHOLD = 168  # "somewhat recent"

# Time decay multipliers
CONTEXT_RECENT_DAY_MULTIPLIER = 0.7  # day-old files
CONTEXT_RECENT_WEEK_MULTIPLIER = 0.4  # week-old files

# File Processing Limits

# System limits for file processing
RECENT_FILE_COUNT_LIMIT = 20  # Maximum recent files to track for scoring
MAX_PROJECT_FILES = 10000  # Maximum files to process in a project
MCP_CACHE_TTL = 3600  # MCP cache time-to-live in seconds
MAX_FILE_SIZE_BYTES = 1048576  # Maximum file size to process (1MB)

# Conversation Analysis Constants

# Conversation scoring factors; fixed scoring increments, not weights
CONVERSATION_KEYWORD_WEIGHT = 0.1
CONVERSATION_FILE_REF_SCORE = 0.2
CONVERSATION_TECHNICAL_SCORE = 0.1
CONVERSATION_PROBLEM_SCORE = 0.15
CONVERSATION_ARCH_SCORE = 0.2
CONVERSATION_DEBUG_SCORE = 0.25
CONVERSATION_TOOL_SCORE = 0.1

# Conversation recency thresholds - these define time decay boundaries
CONVERSATION_RECENCY_THRESHOLDS = {
    "days_1": 1.0,
    "days_7": 0.8,
    "days_30": 0.5,
    "days_90": 0.2,
    "default": 0.1,
}

# Conversation Processing Limits

# Conversation ingestion limits and defaults
CONVERSATION_DEFAULT_LIMIT = 20
CONVERSATION_DEFAULT_MIN_SCORE = 2.0
CONVERSATION_DEFAULT_LOOKBACK_DAYS = 30
CONVERSATION_MAX_LIMIT = 100
CONVERSATION_MAX_LOOKBACK_DAYS = 365
CONVERSATION_SNIPPET_CONTEXT_CHARS = 150
CONVERSATION_SNIPPET_MAX_LENGTH = 100

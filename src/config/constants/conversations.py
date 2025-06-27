"""
Conversation configuration constants for Gandalf MCP server.
Contains settings for conversation recall, processing, and caching.
"""

# Default Processing Constants
CONVERSATION_DEFAULT_RECENT_DAYS = 7
CONVERSATION_FAST_WINDOW_DAYS = 3
CONVERSATION_MAX_LOOKBACK_DAYS = 60

# Performance Optimization Constants
CONVERSATION_BATCH_SIZE = 50
CONVERSATION_EARLY_TERMINATION_MULTIPLIER = 3  # Stop when we have 3x limit
CONVERSATION_PROGRESS_LOG_INTERVAL = 25  # Log progress every N conversations

# Filtering Constants
FILTER_MIN_KEYWORD_MATCHES = 1  # Minimum keyword matches for relevance
FILTER_SKIP_UNTITLED_AFTER_HOURS = 48
FILTER_MIN_EXCHANGE_COUNT = 1  # Minimum exchanges for consideration

# Activity Scoring Constants
ACTIVITY_SCORE_MAX_DURATION = 5.0  # Maximum activity score based on duration
ACTIVITY_SCORE_RECENCY_BOOST = (
    2.0  # Boost for conversations updated within 24 hours
)

# Context Intelligence Constants
CONTEXT_KEYWORD_MIN_RELEVANCE = 0.3  # Minimum keyword relevance threshold
CONTEXT_KEYWORD_MAX_COUNT = 30  # Maximum keywords to generate
CONTEXT_TECH_WEIGHT_MULTIPLIER = 1.5  # Boost for technology keywords
CONTEXT_PROJECT_WEIGHT_MULTIPLIER = 2.0  # Boost for project-specific keywords
CONTEXT_CACHE_TTL_SECONDS = 300  # Context keyword cache TTL in seconds

# Analysis Constants
PROJECT_NAME_WEIGHT_MULTIPLIER = 10
CONTEXT_KEYWORDS_FILE_LIMIT = 60
TECH_WEIGHT_DIVISOR = 5.0
MAX_TECH_WEIGHT = 3.0
CONVERSATION_TEXT_EXTRACTION_LIMIT = 5000
KEYWORD_CHECK_LIMIT = 15
KEYWORD_MATCHES_LIMIT = 8
CONTEXT_KEYWORDS_QUICK_LIMIT = 10
MATCHES_OUTPUT_LIMIT = 8
FIRST_WORDS_ANALYSIS_LIMIT = 30
PATTERN_MATCHES_DEFAULT_LIMIT = 50
KEYWORD_MATCHES_TOP_LIMIT = 10
EARLY_TERMINATION_LIMIT_MULTIPLIER = 3
RECENT_ACTIVITY_HOURS = 24

# Database and Error Messages
DATABASE_STRUCTURE_LIMITATION_NOTE = (
    "Prompt/generation counts are estimated based on conversation activity "
    "due to Cursor database structure limitations"
)

# Pattern Matching
TOOL_USAGE_PATTERNS = [
    r"\b(?:tool|command|script|utility)\b",
    r"\b(?:run|execute|invoke|call)\b",
    r"\b(?:cli|terminal|shell|bash)\b",
]

FILE_REFERENCE_PATTERNS = [
    r"([a-zA-Z_][a-zA-Z0-9_]*\.py)",
    r"([a-zA-Z_][a-zA-Z0-9_]*\.js)",
    r"([a-zA-Z_][a-zA-Z0-9_]*\.ts)",
    r"([a-zA-Z_][a-zA-Z0-9_]*\.md)",
    r"([a-zA-Z_][a-zA-Z0-9_]*\.yaml)",
    r"([a-zA-Z_][a-zA-Z0-9_]*\.json)",
]

CONVERSATION_TYPES = [
    "architecture",
    "debugging",
    "problem_solving",
    "technical",
    "code_discussion",
    "general",
]

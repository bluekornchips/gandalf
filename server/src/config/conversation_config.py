"""Conversation processing and analysis configuration.

This module contains all conversation-related settings, patterns, analysis parameters,
context intelligence configuration, and agentic tool definitions.
"""

import os
from typing import Final

# ============================================================================
# AGENTIC TOOL CONFIGURATION
# ============================================================================

# Supported Tools
AGENTIC_TOOL_CURSOR = "cursor"
AGENTIC_TOOL_CLAUDE_CODE = "claude-code"
AGENTIC_TOOL_WINDSURF = "windsurf"
SUPPORTED_AGENTIC_TOOLS = [
    AGENTIC_TOOL_CURSOR,
    AGENTIC_TOOL_CLAUDE_CODE,
    AGENTIC_TOOL_WINDSURF,
]

# Registry
REGISTRY_FILENAME = "registry.json"

# ============================================================================
# CONVERSATION DEFAULT BEHAVIOR SETTINGS
# ============================================================================

# Default behavior settings
CONVERSATION_DEFAULT_FAST_MODE = True
CONVERSATION_DEFAULT_RECENT_DAYS = 7
CONVERSATION_DEFAULT_LIMIT = 60
CONVERSATION_DEFAULT_MIN_SCORE = 0.0
CONVERSATION_DEFAULT_LOOKBACK_DAYS = 30
CONVERSATION_MAX_LIMIT = 100
CONVERSATION_MAX_LOOKBACK_DAYS = 60

# Processing intervals
CONVERSATION_PROGRESS_LOG_INTERVAL = 25

# Feature toggles
CONVERSATION_FILTERING_ENABLED = (
    os.getenv("GANDALF_CONVERSATION_FILTERING_ENABLED", "false").lower() == "true"
)
CONVERSATION_KEYWORD_MATCH_ENABLED = (
    os.getenv("GANDALF_CONVERSATION_KEYWORD_MATCH_ENABLED", "false").lower() == "true"
)

# ============================================================================
# CONVERSATION PROCESSING LIMITS
# ============================================================================

# Keyword extraction limits
CONVERSATION_KEYWORD_EXTRACTION_LIMIT = 10

# Text processing limits
CONVERSATION_TEXT_EXTRACTION_LIMIT = 10000

# Content length limits
CONVERSATION_SNIPPET_CONTEXT_CHARS = 200
CONVERSATION_SNIPPET_MAX_LENGTH = 500
CONVERSATION_KEYWORD_CHECK_LIMIT = 100
CONVERSATION_KEYWORD_MATCHES_LIMIT = 50
CONVERSATION_KEYWORD_MATCHES_TOP_LIMIT = 20
CONVERSATION_ID_DISPLAY_LIMIT = 50
CONVERSATION_SNIPPET_DISPLAY_LIMIT = 150
CONVERSATION_TITLE_DISPLAY_LIMIT = 100
CONVERSATION_MATCHES_OUTPUT_LIMIT = 100
CONVERSATION_PATTERN_MATCHES_LIMIT = 50

# Domain word filtering
CONVERSATION_DOMAIN_WORD_LIMIT = 100
CONVERSATION_DOMAIN_WORD_MIN_LENGTH = 3

# ============================================================================
# CONVERSATION DETECTION PATTERNS
# ============================================================================

# Conversation detection patterns
CONVERSATION_PATTERNS = {
    "role",
    "content",
    "message",
    "user",
    "assistant",
    "system",
}
CONVERSATION_STRONG_INDICATORS = {"assistant", "user", "role", "content"}
CONVERSATION_FALSE_POSITIVE_INDICATORS = {
    "settings",
    "config",
    "preferences",
    "metadata",
}
CONVERSATION_CONTENT_KEYS = {"content", "text", "message", "data"}
CONVERSATION_MESSAGE_INDICATORS = {"messages", "chat", "conversation", "dialog"}

# Content analysis limits
CONVERSATION_MIN_CONTENT_LENGTH = 5
CONVERSATION_MAX_ANALYSIS_LENGTH = 1000
CONVERSATION_FALSE_POSITIVE_RATIO_THRESHOLD = 0.3
CONVERSATION_MAX_LIST_ITEMS_TO_CHECK = 100

# File patterns
CONVERSATION_FILE_PATTERNS = [
    r"\b(\w+\.\w+)\b",  # filename.extension
    r"\b(\w+/\w+)\b",  # directory/file
]

# Tech patterns for keyword extraction
CONVERSATION_TECH_PATTERNS = [
    r"\b(python|javascript|typescript|react|vue|angular|node|express|"
    r"django|flask|fastapi)\b",
    r"\b(docker|kubernetes|aws|azure|gcp|terraform|ansible)\b",
    r"\b(database|sql|postgresql|mysql|mongodb|redis|elasticsearch)\b",
    r"\b(api|rest|graphql|webhook|endpoint|service|microservice)\b",
    r"\b(test|testing|unit|integration|e2e|pytest|jest|mocha)\b",
    r"\b(debug|debugging|error|exception|bug|issue|problem)\b",
    r"\b(refactor|refactoring|architecture|design|pattern|structure)\b",
    r"\b(performance|optimization|scalability|security|authentication)\b",
]

# ============================================================================
# CONVERSATION STANDARDIZATION
# ============================================================================

# Optional fields for conversation standardization
CONVERSATION_OPTIONAL_FIELDS = [
    "snippet",
    "conversation_type",
    "tags",
    "analysis",
    "workspace_id",
    "database_path",
    "session_data",
    "session_id",
    "project_context",
    "context",
    "source",
    "windsurf_source",
    "chat_session_id",
    "windsurf_metadata",
    "ai_model",
    "user_query",
    "ai_response",
    "file_references",
    "code_blocks",
    "metadata",
    "keyword_matches",
    "updated_at",
]

# Domain word exclusions - stop words filtered during keyword extraction
CONVERSATION_DOMAIN_WORD_EXCLUSIONS = {
    "the",
    "and",
    "for",
    "are",
    "but",
    "not",
    "you",
    "all",
    "can",
    "had",
    "her",
    "was",
    "one",
    "our",
    "out",
    "day",
    "get",
    "has",
    "him",
    "his",
    "how",
    "its",
    "may",
    "new",
    "now",
    "old",
    "see",
    "two",
    "who",
    "boy",
    "did",
    "man",
    "men",
    "run",
    "she",
    "too",
    "any",
    "big",
    "got",
    "put",
    "say",
    "use",
    "way",
    "work",
    "well",
    "where",
    "when",
    "what",
    "with",
    "will",
    "were",
    "very",
    "that",
    "this",
    "they",
    "them",
    "then",
    "than",
    "take",
    "some",
    "said",
    "part",
    "over",
    "only",
    "onto",
    "once",
    "off",
    "nor",
    "lot",
    "let",
    "far",
    "end",
    "ago",
    "as",
    "at",
    "be",
    "by",
    "do",
    "go",
    "he",
    "if",
    "in",
    "is",
    "it",
    "me",
    "my",
    "no",
    "of",
    "on",
    "or",
    "so",
    "to",
    "up",
    "us",
    "we",
}

# ============================================================================
# CONTEXT ANALYSIS CONFIGURATION
# ============================================================================

# Context analysis scoring thresholds
CONTEXT_ANALYSIS_MIN_SCORE = 0.1
CONTEXT_ANALYSIS_HIGH_SCORE = 1.5
CONTEXT_ANALYSIS_MEDIUM_SCORE = 1.0

# File analysis integration settings
CONTEXT_ANALYSIS_FILE_ENABLED = True
CONTEXT_ANALYSIS_FILE_WEIGHT = 0.3

# Performance optimization settings
CONTEXT_ANALYSIS_CACHE_TTL = 300  # 5 minutes
CONTEXT_ANALYSIS_BATCH_SIZE = 20

# Export format choices
CONVERSATION_EXPORT_FORMATS = ["json", "markdown", "cursor"]
CONVERSATION_EXPORT_FORMAT_DEFAULT = "json"

# ============================================================================
# CONTEXT INTELLIGENCE CONFIGURATION
# ============================================================================

CONTEXT_KEYWORD_MAX_COUNT: Final[int] = 15
CONTEXT_MAX_FILES_TO_CHECK: Final[int] = 50
CONTEXT_MIN_EXTENSIONS_BEFORE_DEEP_SCAN: Final[int] = 3
CONTEXT_KEYWORDS_QUICK_LIMIT: Final[int] = 10

# File size constants for context analysis
CONTEXT_FILE_SIZE_ACCEPTABLE_MAX: Final[int] = 10_000_000  # 10MB
CONTEXT_FILE_SIZE_OPTIMAL_MAX: Final[int] = 1_000_000  # 1MB
CONTEXT_TOP_FILES_COUNT: Final[int] = 20

# Token optimization configuration
TOKEN_OPTIMIZATION_MAX_RESPONSE_SIZE: Final[int] = 16_000
TOKEN_OPTIMIZATION_CONTENT_TRUNCATION_LIMIT: Final[int] = 1_000
TOKEN_OPTIMIZATION_SUMMARY_MODE_THRESHOLD: Final[int] = 10
TOKEN_OPTIMIZATION_MAX_CONTEXT_KEYWORDS: Final[int] = 15
TOKEN_OPTIMIZATION_MAX_TOOL_RESULT_FIELDS: Final[int] = 8

# Activity-based weight constants
ACTIVITY_SCORE_MAX_DURATION: Final[int] = 30  # days
CONTEXT_FILE_SIZE_PENALTY_THRESHOLD: Final[int] = 100_000  # 100KB

# Base weights
ACTIVE_FILE_WEIGHT: Final[float] = 5.0
IMPORT_NEIGHBOR_WEIGHT: Final[float] = 3.0
RECENT_EDIT_WEIGHT: Final[float] = 4.0
CURSOR_ACTIVITY_WEIGHT: Final[float] = 2.0

# Scoring thresholds and multipliers
CURSOR_ACTIVITY_WEIGHT_MULTIPLIER: Final[float] = 1.5
CURSOR_ACTIVITY_SCORE_THRESHOLD: Final[float] = 0.1
CURSOR_ACTIVITY_POSITION_WEIGHT: Final[float] = 0.3
CURSOR_ACTIVITY_RECENT_WEIGHT: Final[float] = 0.7

RECENT_EDIT_HOURS_THRESHOLD: Final[int] = 24
RECENT_EDIT_WEIGHT_MULTIPLIER: Final[float] = 2.0
RECENT_EDIT_SCORE_THRESHOLD: Final[float] = 0.2
RECENT_EDIT_TIME_WEIGHT: Final[float] = 0.5

IMPORT_NEIGHBOR_SCORE_THRESHOLD: Final[float] = 0.15
IMPORT_NEIGHBOR_WEIGHT_MULTIPLIER: Final[float] = 1.8
IMPORT_NEIGHBOR_DEPTH_WEIGHT: Final[float] = 0.2

ACTIVE_FILE_SCORE_THRESHOLD: Final[float] = 0.3
ACTIVE_FILE_WEIGHT_MULTIPLIER: Final[float] = 3.0

# File tools configuration
HIGH_PRIORITY_DISPLAY_LIMIT: Final[int] = 50
MEDIUM_PRIORITY_DISPLAY_LIMIT: Final[int] = 15
LOW_PRIORITY_DISPLAY_LIMIT: Final[int] = 10
TOP_FILES_DISPLAY_LIMIT: Final[int] = 15
MAX_FILES_LIMIT: Final[int] = 10_000

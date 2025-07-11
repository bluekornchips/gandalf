"""Conversation processing configuration and patterns."""

DEFAULT_FAST_MODE = False
CONVERSATION_DEFAULT_RECENT_DAYS = 7
CONVERSATION_DEFAULT_LIMIT = 20
CONVERSATION_DEFAULT_MIN_SCORE = 2.0  # Change to 1.0
CONVERSATION_DEFAULT_LOOKBACK_DAYS = 30
CONVERSATION_MAX_LIMIT = 100
CONVERSATION_MAX_LOOKBACK_DAYS = 60

# Processing
CONVERSATION_BATCH_SIZE = 50
CONVERSATION_PROGRESS_LOG_INTERVAL = 25

# Enhanced Conversation Filtering Constants
CONVERSATION_FILTERING_ENABLED = True  # Should always be true, we can remove
# this constant and update our code.

# Simple keyword-based filtering
CONVERSATION_KEYWORD_MATCH_ENABLED = True  # Should always be true, we can
# remove this constant and update our code.
CONVERSATION_PROMPT_KEYWORD_EXTRACTION_LIMIT = 10

# Basic tech patterns for keyword extraction, AI generated not made by me.
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

CONVERSATION_FILE_PATTERNS = [
    r"\b(\w+\.\w+)\b",  # filename.extension
    r"\b(\w+/\w+)\b",  # directory/file
]

# Filtering exclusions
# These are the words that we don't want to include in the conversation
# because of how common they are.
CONVERSATION_DOMAIN_WORD_EXCLUSIONS = {
    "this",
    "that",
    "with",
    "from",
    "they",
    "were",
    "been",
    "have",
    "will",
    "would",
    "could",
    "should",
    "might",
}

CONVERSATION_DOMAIN_WORD_MIN_LENGTH = 3
CONVERSATION_DOMAIN_WORD_LIMIT = 5

# Keyword Processing
KEYWORD_CHECK_LIMIT = 10
KEYWORD_MATCHES_LIMIT = 50
KEYWORD_MATCHES_TOP_LIMIT = 10
MATCHES_OUTPUT_LIMIT = 100
PATTERN_MATCHES_DEFAULT_LIMIT = 20

# Conversation Snippet Processing
CONVERSATION_SNIPPET_CONTEXT_CHARS = 100

# Lightweight Conversation Field Limits
LIGHTWEIGHT_CONVERSATION_ID_LIMIT = 50
LIGHTWEIGHT_CONVERSATION_TITLE_LIMIT = 100
LIGHTWEIGHT_CONVERSATION_SNIPPET_LIMIT = 150

# Conversation Text Extraction Limit
CONVERSATION_TEXT_EXTRACTION_LIMIT = 10000
CONVERSATION_SNIPPET_MAX_LENGTH = 500

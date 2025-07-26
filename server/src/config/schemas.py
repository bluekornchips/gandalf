"""
Configuration schemas for Gandalf MCP server.
Contains validation schemas and structured configuration definitions.
"""

from src.config.core_constants import (
    VALIDATION_CONVERSATION_PARAM_MAX,
    VALIDATION_CONVERSATION_PARAM_MIN,
    VALIDATION_FILE_SIZE_LARGE_MAX,
    VALIDATION_FILE_SIZE_MIN,
    VALIDATION_FILE_SIZE_OPTIMAL_MAX,
    VALIDATION_MULTIPLIER_MAX,
    VALIDATION_MULTIPLIER_MIN,
    VALIDATION_TIME_THRESHOLD_MAX_DAYS,
    VALIDATION_TIME_THRESHOLD_MAX_HOURS,
    VALIDATION_TIME_THRESHOLD_MAX_WEEKS,
    VALIDATION_TIME_THRESHOLD_MIN,
    VALIDATION_WEIGHT_MAX,
    VALIDATION_WEIGHT_MIN,
)

# Required configuration sections
VALIDATION_REQUIRED_SECTIONS = {
    "enabled": bool,
    "weights": dict,
    "conversation": dict,
    "context": dict,
    "file_extensions": dict,
    "directories": dict,
}

# Required weights with their validation ranges
VALIDATION_REQUIRED_WEIGHTS = {
    "recent_modification": (
        float,
        VALIDATION_WEIGHT_MIN,
        VALIDATION_WEIGHT_MAX,
    ),
    "file_size_optimal": (float, VALIDATION_WEIGHT_MIN, VALIDATION_WEIGHT_MAX),
    "import_relationship": (
        float,
        VALIDATION_WEIGHT_MIN,
        VALIDATION_WEIGHT_MAX,
    ),
    "conversation_mention": (
        float,
        VALIDATION_WEIGHT_MIN,
        VALIDATION_WEIGHT_MAX,
    ),
    "git_activity": (float, VALIDATION_WEIGHT_MIN, VALIDATION_WEIGHT_MAX),
    "file_type_priority": (
        float,
        VALIDATION_WEIGHT_MIN,
        VALIDATION_WEIGHT_MAX,
    ),
    "directory_importance": (
        float,
        VALIDATION_WEIGHT_MIN,
        VALIDATION_WEIGHT_MAX,
    ),
}

# Required conversation parameters with their validation ranges
VALIDATION_REQUIRED_CONVERSATION = {
    "keyword_match": (float, VALIDATION_WEIGHT_MIN, VALIDATION_WEIGHT_MAX),
    "file_reference": (float, VALIDATION_WEIGHT_MIN, VALIDATION_WEIGHT_MAX),
    "recency": (float, VALIDATION_WEIGHT_MIN, VALIDATION_WEIGHT_MAX),
    "technical_content": (float, VALIDATION_WEIGHT_MIN, VALIDATION_WEIGHT_MAX),
    "problem_solving": (float, VALIDATION_WEIGHT_MIN, VALIDATION_WEIGHT_MAX),
    "architecture": (float, VALIDATION_WEIGHT_MIN, VALIDATION_WEIGHT_MAX),
    "debugging": (float, VALIDATION_WEIGHT_MIN, VALIDATION_WEIGHT_MAX),
    "keyword_weight": (
        float,
        VALIDATION_CONVERSATION_PARAM_MIN,
        VALIDATION_CONVERSATION_PARAM_MAX,
    ),
    "file_ref_score": (
        float,
        VALIDATION_CONVERSATION_PARAM_MIN,
        VALIDATION_CONVERSATION_PARAM_MAX,
    ),
}

# Required context structure with validation ranges
VALIDATION_REQUIRED_CONTEXT = {
    "file_size": {
        "optimal_min": (
            int,
            VALIDATION_FILE_SIZE_MIN,
            VALIDATION_FILE_SIZE_OPTIMAL_MAX,
        ),
        "optimal_max": (int, 1000, VALIDATION_FILE_SIZE_OPTIMAL_MAX),
        "acceptable_max": (int, 10000, VALIDATION_FILE_SIZE_LARGE_MAX),
        "acceptable_multiplier": (
            float,
            VALIDATION_MULTIPLIER_MIN,
            VALIDATION_MULTIPLIER_MAX,
        ),
        "large_multiplier": (
            float,
            VALIDATION_MULTIPLIER_MIN,
            VALIDATION_MULTIPLIER_MAX,
        ),
    },
    "recent_modifications": {
        "hour_threshold": (
            int,
            VALIDATION_TIME_THRESHOLD_MIN,
            VALIDATION_TIME_THRESHOLD_MAX_HOURS,
        ),
        "day_threshold": (
            int,
            VALIDATION_TIME_THRESHOLD_MIN,
            VALIDATION_TIME_THRESHOLD_MAX_DAYS,
        ),
        "week_threshold": (
            int,
            VALIDATION_TIME_THRESHOLD_MIN,
            VALIDATION_TIME_THRESHOLD_MAX_WEEKS,
        ),
        "day_multiplier": (
            float,
            VALIDATION_MULTIPLIER_MIN,
            VALIDATION_MULTIPLIER_MAX,
        ),
        "week_multiplier": (
            float,
            VALIDATION_MULTIPLIER_MIN,
            VALIDATION_MULTIPLIER_MAX,
        ),
    },
    "activity_score_recency_boost": (
        float,
        VALIDATION_MULTIPLIER_MIN,
        VALIDATION_MULTIPLIER_MAX,
    ),
}

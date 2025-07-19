"""Schema default values for configuration validation."""

from typing import Final

# Basic default values
DEFAULT_WEIGHT_VALUE: Final[float] = 1.0
DEFAULT_KEYWORD_WEIGHT: Final[float] = 0.1
DEFAULT_FILE_REF_SCORE: Final[float] = 0.2
DEFAULT_MULTIPLIER_HIGH: Final[float] = 0.8
DEFAULT_MULTIPLIER_MID: Final[float] = 0.5
DEFAULT_MULTIPLIER_LOW: Final[float] = 0.3
DEFAULT_ACTIVITY_BOOST: Final[float] = 1.5
DEFAULT_TERMINATION_MULTIPLIER: Final[float] = 0.8
DEFAULT_TERMINATION_LIMIT_MULTIPLIER: Final[float] = 1.5
DEFAULT_OPTIMAL_FILE_SIZE_MIN: Final[int] = 100

# Conversation type bonuses
DEFAULT_TYPE_BONUSES: Final[dict[str, float]] = {
    "debugging": 0.25,
    "architecture": 0.2,
    "testing": 0.15,
    "code_discussion": 0.1,
    "problem_solving": 0.1,
    "general": 0.0,
}

# Default recency thresholds
DEFAULT_RECENCY_THRESHOLDS: Final[dict[str, float]] = {
    "days_1": DEFAULT_WEIGHT_VALUE,
    "days_7": DEFAULT_MULTIPLIER_HIGH,
    "days_30": DEFAULT_MULTIPLIER_MID,
    "days_90": DEFAULT_FILE_REF_SCORE,
    "default": DEFAULT_KEYWORD_WEIGHT,
}

# Default file extension priorities
# Very basic, will be updated as we go.
DEFAULT_FILE_EXTENSIONS: Final[dict[str, float]] = {
    "py": DEFAULT_WEIGHT_VALUE,
    "js": 0.9,
    "ts": 0.9,
    "jsx": DEFAULT_MULTIPLIER_HIGH,
    "tsx": DEFAULT_MULTIPLIER_HIGH,
    "vue": DEFAULT_MULTIPLIER_HIGH,
    "md": 0.6,
    "txt": DEFAULT_MULTIPLIER_LOW,
    "json": DEFAULT_MULTIPLIER_MID,
    "yaml": DEFAULT_MULTIPLIER_MID,
    "yml": DEFAULT_MULTIPLIER_MID,
}

# Default directory priorities
DEFAULT_DIRECTORIES: Final[dict[str, float]] = {
    "src": DEFAULT_WEIGHT_VALUE,
    "lib": 0.9,
    "app": 0.9,
    "components": DEFAULT_MULTIPLIER_HIGH,
    "utils": 0.7,
    "tests": 0.6,
    "docs": 0.4,
    "examples": DEFAULT_MULTIPLIER_LOW,
}

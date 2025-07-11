"""Application limits and validation thresholds."""

from typing import Final

# File processing limits
MAX_PROJECT_FILES: Final[int] = 10_000
MAX_FILE_SIZE_BYTES: Final[int] = 1_048_576  # 1MB
MAX_FILE_EXTENSION_LENGTH: Final[int] = 10
MAX_FILE_TYPES: Final[int] = 20
RECENT_FILE_COUNT_LIMIT: Final[int] = 20

# Input validation limits
MAX_STRING_LENGTH: Final[int] = 50_000
MAX_ARRAY_LENGTH: Final[int] = 100
MAX_QUERY_LENGTH: Final[int] = 100
MAX_PATH_DEPTH: Final[int] = 20
PROJECT_NAME_MAX_LENGTH: Final[int] = 100

# Timeout configurations
FIND_COMMAND_TIMEOUT: Final[int] = 30
DATABASE_SCANNER_TIMEOUT: Final[int] = 30
DATABASE_OPERATION_TIMEOUT: Final[int] = 5
DATABASE_SCANNER_CACHE_TTL: Final[int] = 300  # 5 minutes

# Scoring thresholds and neutral values
PRIORITY_NEUTRAL_SCORE: Final[float] = 0.5
CONTEXT_MIN_SCORE: Final[float] = 0.0

# Weights validation (0.0 to 100.0)
VALIDATION_WEIGHT_MIN: Final[float] = 0.0
VALIDATION_WEIGHT_MAX: Final[float] = 100.0

# Conversation parameters (0.0 to 10.0)
VALIDATION_CONVERSATION_PARAM_MIN: Final[float] = 0.0
VALIDATION_CONVERSATION_PARAM_MAX: Final[float] = 10.0

# Context multipliers (0.0 to 10.0)
VALIDATION_MULTIPLIER_MIN: Final[float] = 0.0
VALIDATION_MULTIPLIER_MAX: Final[float] = 10.0

# File size validation ranges
VALIDATION_FILE_SIZE_MIN: Final[int] = 1
VALIDATION_FILE_SIZE_OPTIMAL_MAX: Final[int] = 1_000_000  # 1MB
VALIDATION_FILE_SIZE_ACCEPTABLE_MAX: Final[int] = 10_000_000  # 10MB
VALIDATION_FILE_SIZE_LARGE_MAX: Final[int] = 100_000_000  # 100MB

# Time threshold validation ranges (in hours)
VALIDATION_TIME_THRESHOLD_MIN: Final[int] = 1
VALIDATION_TIME_THRESHOLD_MAX_HOURS: Final[int] = 168  # 1 week
VALIDATION_TIME_THRESHOLD_MAX_DAYS: Final[int] = 720  # 30 days
VALIDATION_TIME_THRESHOLD_MAX_WEEKS: Final[int] = 8760  # 1 year

# File extension validation
VALIDATION_FILE_EXT_MIN_VALUE: Final[float] = 0.0
VALIDATION_FILE_EXT_MAX_VALUE: Final[float] = 100.0

# Directory priority validation
VALIDATION_DIRECTORY_MIN_VALUE: Final[float] = 0.0
VALIDATION_DIRECTORY_MAX_VALUE: Final[float] = 100.0

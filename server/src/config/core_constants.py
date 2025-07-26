"""Core constants and configuration values.

This module contains basic limits, timeouts, defaults, path configurations, and server settings.
"""

import os
from pathlib import Path
from typing import Final

from src.utils.version import get_version

# ============================================================================
# SERVER CONFIGURATION
# ============================================================================

# Server identity and protocol
MCP_SERVER_NAME = os.getenv("MCP_SERVER_NAME", "gandalf")
GANDALF_SERVER_VERSION = os.getenv("GANDALF_SERVER_VERSION", get_version())
MCP_PROTOCOL_VERSION = "2025-06-18"
JSONRPC_VERSION = "2.0"

# Server info and capabilities
SERVER_INFO = {"name": "gandalf-mcp", "version": GANDALF_SERVER_VERSION}
SERVER_CAPABILITIES = {"tools": {"listChanged": True}, "logging": {}}

# Environment
WORKSPACE_FOLDER_PATHS = os.getenv("WORKSPACE_FOLDER_PATHS")
DEBUG_LOGGING = bool(os.getenv("GANDALF_DEBUG_LOGGING"))

# ============================================================================
# FILE PROCESSING AND INPUT VALIDATION LIMITS
# ============================================================================

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

# ============================================================================
# TIMEOUT CONFIGURATIONS
# ============================================================================

# Operation timeouts
FIND_COMMAND_TIMEOUT: Final[int] = 30
DATABASE_SCANNER_TIMEOUT: Final[int] = 30
DATABASE_OPERATION_TIMEOUT: Final[int] = 5
SUBPROCESS_TIMEOUT: Final[int] = 5  # seconds

# ============================================================================
# CACHE CONFIGURATION
# ============================================================================

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

# ============================================================================
# PATH CONFIGURATION
# ============================================================================

# Project structure constants
GANDALF_HOME = Path(os.getenv("GANDALF_HOME", str(Path.home() / ".gandalf")))

# Gandalf installation detection - find spec directory relative to this file
# This file is at: gandalf/server/src/config/core_constants.py
# Spec directory is at: gandalf/spec/
_CURRENT_FILE = Path(__file__).resolve()
_GANDALF_ROOT = _CURRENT_FILE.parent.parent.parent.parent  # Go up 4 levels
GANDALF_SPEC_DIR = _GANDALF_ROOT / "spec"

# Gandalf configuration directories
GANDALF_CONFIG_DIR = GANDALF_HOME / "config"

# Weights Configuration - can be overridden for testing
DEFAULT_WEIGHTS_FILE = GANDALF_CONFIG_DIR / "gandalf-weights.yaml"
SPEC_WEIGHTS_FILE = GANDALF_SPEC_DIR / "gandalf-weights.yaml"

# Allow override for testing via environment variable
WEIGHTS_FILE_OVERRIDE = os.getenv("GANDALF_WEIGHTS_FILE")

# Cache Directories
CACHE_ROOT_DIR = GANDALF_HOME / "cache"
CONVERSATION_CACHE_DIR = CACHE_ROOT_DIR / "conversations"
FILE_CACHE_DIR = CACHE_ROOT_DIR / "files"
GIT_CACHE_DIR = CACHE_ROOT_DIR / "git"

# Cache Files
CONVERSATION_CACHE_FILE = CONVERSATION_CACHE_DIR / "conversations.json"
CONVERSATION_CACHE_METADATA_FILE = CONVERSATION_CACHE_DIR / "metadata.json"

# Application directories - Cursor
CURSOR_WORKSPACE_STORAGE_PATH = "Application Support/Cursor/User/workspaceStorage"
CURSOR_WORKSPACE_STORAGE = [
    Path.home()
    / "Library"
    / "Application Support"
    / "Cursor"
    / "User"
    / "workspaceStorage"
]

# Application directories - Windsurf
WINDSURF_WORKSPACE_STORAGE = [
    Path.home()
    / "Library"
    / "Application Support"
    / "Windsurf"
    / "User"
    / "workspaceStorage"
]

WINDSURF_GLOBAL_STORAGE = (
    Path.home()
    / "Library"
    / "Application Support"
    / "Windsurf"
    / "User"
    / "globalStorage"
)

CLAUDE_HOME = [Path.home() / ".claude"]

# ============================================================================
# SCORING THRESHOLDS AND VALIDATION
# ============================================================================

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

# ============================================================================
# SCHEMA DEFAULT VALUES
# ============================================================================

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

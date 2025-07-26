"""
Common imports used across multiple modules.

This module consolidates frequently imported utilities, constants, and functions
to reduce duplication and simplify import management across the codebase.
"""

# Standard library imports
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Optional

from src.config.conversation_config import (
    CONVERSATION_DEFAULT_LIMIT,
    CONVERSATION_DEFAULT_LOOKBACK_DAYS,
    CONVERSATION_MAX_LIMIT,
    CONVERSATION_MAX_LOOKBACK_DAYS,
    CONVERSATION_TEXT_EXTRACTION_LIMIT,
    TOKEN_OPTIMIZATION_MAX_CONTEXT_KEYWORDS,
)

# Core configuration imports
from src.config.core_constants import (
    DATABASE_OPERATION_TIMEOUT,
    DATABASE_SCANNER_TIMEOUT,
    GANDALF_HOME,
    MCP_CACHE_TTL,
    MCP_PROTOCOL_VERSION,
    PRIORITY_NEUTRAL_SCORE,
    SERVER_CAPABILITIES,
    SERVER_INFO,
)
from src.config.enums import ErrorCodes
from src.utils.access_control import (
    AccessValidator,
    create_mcp_tool_result,
)

# Utilities - most commonly imported
from src.utils.common import (
    format_json_response,
    initialize_session_logging,
    log_debug,
    log_error,
    log_info,
)
from src.utils.jsonrpc import (
    create_error_response,
    create_success_response,
)
from src.utils.performance import (
    get_duration,
    log_operation_time,
    start_timer,
)

# Export all common imports for easy access
__all__ = [
    # Standard library
    "json",
    "os",
    "sys",
    "time",
    "Path",
    "Any",
    "Optional",
    # Core constants
    "DATABASE_OPERATION_TIMEOUT",
    "DATABASE_SCANNER_TIMEOUT",
    "GANDALF_HOME",
    "MCP_CACHE_TTL",
    "MCP_PROTOCOL_VERSION",
    "PRIORITY_NEUTRAL_SCORE",
    "SERVER_CAPABILITIES",
    "SERVER_INFO",
    # Conversation config
    "CONVERSATION_DEFAULT_LIMIT",
    "CONVERSATION_DEFAULT_LOOKBACK_DAYS",
    "CONVERSATION_MAX_LIMIT",
    "CONVERSATION_MAX_LOOKBACK_DAYS",
    "CONVERSATION_TEXT_EXTRACTION_LIMIT",
    "TOKEN_OPTIMIZATION_MAX_CONTEXT_KEYWORDS",
    # Enums
    "ErrorCodes",
    # Common utilities
    "format_json_response",
    "initialize_session_logging",
    "log_debug",
    "log_error",
    "log_info",
    # Access control
    "AccessValidator",
    "create_mcp_tool_result",
    # Performance
    "get_duration",
    "log_operation_time",
    "start_timer",
    # JSON-RPC
    "create_error_response",
    "create_success_response",
]

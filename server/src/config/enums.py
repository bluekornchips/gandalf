"""
Enumeration definitions for Gandalf MCP server.
"""

from enum import Enum, IntEnum


class LogLevel(Enum):
    """Logging levels for the application."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCodes(IntEnum):
    """Standard error codes for the application."""

    SUCCESS = 0
    GENERAL_ERROR = 1
    INVALID_INPUT = 2
    FILE_NOT_FOUND = 3
    PERMISSION_DENIED = 4
    NETWORK_ERROR = 5
    TIMEOUT_ERROR = 6
    CONFIGURATION_ERROR = 7

    # JSON-RPC 2.0 Error Codes
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603


class Severity(Enum):
    """Validation severity levels."""

    ERROR = "error"
    WARNING = "warning"

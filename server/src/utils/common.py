"""Common utility functions for the MCP server, focusing on file-based logging only."""

import json
import sys
from datetime import datetime
from enum import IntEnum
from pathlib import Path
from typing import Any

from src.config.constants.paths import GANDALF_HOME
from src.config.constants.server import DEBUG_LOGGING, MCP_SERVER_NAME

_log_file_path: Path | None = None
_session_id: str | None = None
_min_log_level: str = "debug"
_server_instance: Any = None


class LogLevel(IntEnum):
    """RFC 5424 severity levels.
    Ref: https://modelcontextprotocol.io/specification/2025-06-18/server/utilities/logging
    """

    DEBUG = 0
    INFO = 1
    NOTICE = 2
    WARNING = 3
    ERROR = 4
    CRITICAL = 5
    ALERT = 6
    EMERGENCY = 7


LOG_LEVELS = {
    "debug": LogLevel.DEBUG,
    "info": LogLevel.INFO,
    "notice": LogLevel.NOTICE,
    "warning": LogLevel.WARNING,
    "error": LogLevel.ERROR,
    "critical": LogLevel.CRITICAL,
    "alert": LogLevel.ALERT,
    "emergency": LogLevel.EMERGENCY,
}


def initialize_session_logging(session_id: str, server_instance: Any = None) -> None:
    """Initialize session-specific logging to file and optionally MCP notifications."""
    global _log_file_path, _session_id, _server_instance
    _session_id = session_id
    _server_instance = server_instance

    logs_dir = GANDALF_HOME / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"{MCP_SERVER_NAME}_session_{session_id}_{timestamp}.log"
    _log_file_path = logs_dir / log_filename

    write_log("info", f"{MCP_SERVER_NAME.upper()} session started: {session_id}")


def set_min_log_level(level: str) -> bool:
    """Set the minimum log level for both file and MCP notifications."""
    global _min_log_level
    if level in LOG_LEVELS:
        _min_log_level = level
        write_log("notice", f"Log level set to: {level}", logger="logging")
        return True
    return False


def _should_log(level: str) -> bool:
    """Check if a log level should be processed based on minimum level."""
    current_level = LOG_LEVELS.get(level, LogLevel.DEBUG)
    min_level = LOG_LEVELS.get(_min_log_level, LogLevel.DEBUG)
    return current_level >= min_level


def _send_mcp_notification(
    level: str, message: str, logger: str | None = None, data: dict | None = None
) -> None:
    """Send MCP log notification if server instance is available."""
    if not _server_instance or not hasattr(_server_instance, "send_notification"):
        return

    try:
        notification_data = {
            "level": level,
            "data": {
                "message": message,
                "session_id": _session_id,
            },
        }

        if logger:
            notification_data["logger"] = logger

        if data:
            notification_data["data"].update(data)

        _server_instance.send_notification("notifications/message", notification_data)
    except AttributeError:
        pass


def write_log(
    level: str,
    message: str,
    logger: str | None = None,
    data: dict | None = None,
) -> None:
    """Write log entry to file and send MCP notification if applicable."""
    if not _should_log(level):
        return

    if not _log_file_path:
        if DEBUG_LOGGING:
            print(
                f"GANDALF_LOG_DEBUG: No log file path - {level}: {message}",
                file=sys.stderr,
            )
        return

    try:
        timestamp = datetime.now().isoformat()
        log_entry: dict[str, Any] = {
            "timestamp": timestamp,
            "level": level,
            "message": message,
            "session_id": _session_id,
        }

        if logger:
            log_entry["logger"] = logger
        if data:
            log_entry["data"] = data

        _log_file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(_log_file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
            f.flush()

        _send_mcp_notification(level, message, logger, data)

    except OSError as e:
        if DEBUG_LOGGING:
            print(f"GANDALF_LOG_ERROR: {e}", file=sys.stderr)
    except UnicodeEncodeError as e:
        if DEBUG_LOGGING:
            print(f"GANDALF_ENCODING_ERROR: {e}", file=sys.stderr)
    except TypeError as e:
        if DEBUG_LOGGING:
            print(f"GANDALF_TYPE_ERROR: {e}", file=sys.stderr)


def log_debug(
    message: str, logger: str | None = None, data: dict | None = None
) -> None:
    """Log a debug message with structured data."""
    write_log("debug", message, logger or "server", data)


def log_info(message: str, logger: str | None = None, data: dict | None = None) -> None:
    """Log an info message with structured data."""
    write_log("info", message, logger or "server", data)


def log_notice(
    message: str, logger: str | None = None, data: dict | None = None
) -> None:
    """Log a notice message for normal but significant events."""
    write_log("notice", message, logger or "server", data)


def log_warning(
    message: str, logger: str | None = None, data: dict | None = None
) -> None:
    """Log a warning message for warning conditions."""
    write_log("warning", message, logger or "server", data)


def log_error(
    error: Exception,
    context: str = "",
    logger: str | None = None,
    data: dict | None = None,
) -> None:
    """Log an error message with structured data."""
    error_msg = f"{context}: {error}" if context else str(error)
    error_data = {"error_type": type(error).__name__, "error_str": str(error)}
    if data:
        error_data.update(data)
    write_log("error", error_msg, logger or "server", error_data)


def log_critical(
    message: str, logger: str | None = None, data: dict | None = None
) -> None:
    """Log a critical message for critical conditions."""
    write_log("critical", message, logger or "server", data)


def log_alert(
    message: str, logger: str | None = None, data: dict | None = None
) -> None:
    """Log an alert message when action must be taken immediately."""
    write_log("alert", message, logger or "server", data)


def log_emergency(
    message: str, logger: str | None = None, data: dict | None = None
) -> None:
    """Log an emergency message when system is unusable."""
    write_log("emergency", message, logger or "server", data)

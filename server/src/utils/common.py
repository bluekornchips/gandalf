"""Common utility functions for the MCP server, focusing on file-based logging only."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from src.config.constants.paths import GANDALF_HOME
from src.config.constants.server import MCP_SERVER_NAME

_log_file_path: Optional[Path] = None
_session_id: Optional[str] = None


def initialize_session_logging(session_id: str) -> None:
    """Initialize session-specific logging to file only."""
    global _log_file_path, _session_id
    _session_id = session_id

    # Create logs directory, if it doesn't exist
    logs_dir = GANDALF_HOME / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Create session-specific log file, if it doesn't exist
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"{MCP_SERVER_NAME}_session_{session_id}_{timestamp}.log"
    _log_file_path = logs_dir / log_filename

    # Write session start marker
    write_log("info", f"{MCP_SERVER_NAME.upper()} session started: {session_id}")


def write_log(
    level: str,
    message: str,
    logger: Optional[str] = None,
    data: Optional[dict] = None,
) -> None:
    """Write log entry to session-specific log file only."""
    if not _log_file_path:
        return

    try:
        timestamp = datetime.now().isoformat()
        log_entry: Dict[str, Any] = {
            "timestamp": timestamp,
            "level": level,
            "message": message,
            "session_id": _session_id,
        }

        if logger:
            log_entry["logger"] = logger
        if data:
            log_entry["data"] = data

        with open(_log_file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")

    except (OSError, IOError, UnicodeEncodeError, TypeError):
        # Avoid recursion by not logging this error
        pass


def log_info(message: str) -> None:
    """Log an info message to file only."""
    write_log("info", message)


def log_error(error: Exception, context: str = "") -> None:
    """Log an error message to file only."""
    error_msg = f"{context}: {error}" if context else str(error)
    write_log("error", error_msg)


def log_debug(message: str) -> None:
    """Log a debug message to file only."""
    write_log("debug", message)


def log_critical(message: str) -> None:
    """Log a critical message to file only."""
    write_log("critical", message)

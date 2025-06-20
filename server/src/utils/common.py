"""Common utility functions for the MCP server, mainly logging,."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from config.constants.core import GANDALF_HOME, MCP_SERVER_NAME

_log_file_path: Optional[Path] = None
_session_id: Optional[str] = None


def initialize_session_logging(session_id: str) -> None:
    """Initialize session-specific logging."""
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
    level: str, message: str, logger: Optional[str] = None, data: Optional[dict] = None
) -> None:
    """Write log entry to session-specific log file."""
    if not _log_file_path:
        return

    try:
        timestamp = datetime.now().isoformat()
        log_entry = {
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

    except (OSError, IOError, UnicodeEncodeError, json.JSONEncodeError) as e:
        # Avoid recursion by not logging this error, avoid recursion, avoid recursion...
        pass


def send_rpc_message(
    level: str, message: str, logger: Optional[str] = None, data: Optional[dict] = None
) -> None:
    """Send a log notification via JSON-RPC."""
    params = {"level": level, "message": message}

    if logger:
        params["logger"] = logger

    if data:
        params["data"] = data

    rpc_message = {
        "jsonrpc": "2.0",
        "method": "notifications/message",
        "params": params,
    }
    print(json.dumps(rpc_message), flush=True)


def log_info(message: str) -> None:
    """Log an info message to both file and RPC."""
    write_log("info", message)
    send_rpc_message("info", message)


def log_error(error: Exception, context: str = "") -> None:
    """Log an error message to both file and RPC."""
    error_msg = f"{context}: {error}" if context else str(error)
    write_log("error", error_msg)
    send_rpc_message("error", error_msg)


def log_debug(message: str) -> None:
    """Log a debug message to both file and RPC."""
    write_log("debug", message)
    send_rpc_message("debug", message)

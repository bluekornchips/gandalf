"""File-based logging utility."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config.constants import GANDALF_HOME


def write_log(level: str, message: str, data: dict[str, Any] | None = None) -> None:
    """Write log entry to file in GANDALF_HOME/logs directory."""
    if not GANDALF_HOME:
        # No-op when log home is not configured. Avoid console output.
        return

    logs_dir = Path(GANDALF_HOME) / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).isoformat()
    log_entry: dict[str, Any] = {
        "timestamp": timestamp,
        "level": level,
        "message": message,
    }

    if data:
        log_entry["data"] = data

    log_file = logs_dir / f"{level}.log"

    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, default=str) + "\n")
            f.flush()
    except OSError:
        # On write failure, fail silently to avoid console output in production paths.
        # TODO: Why? Because I don't want to handle this yet.
        return


def log_debug(message: str, data: dict[str, Any] | None = None) -> None:
    """Log a debug message."""
    write_log("debug", message, data)


def log_info(message: str, data: dict[str, Any] | None = None) -> None:
    """Log an info message."""
    write_log("info", message, data)


def log_error(message: str, data: dict[str, Any] | None = None) -> None:
    """Log an error message."""
    write_log("error", message, data)

"""Performance monitoring utilities for the Gandalf MCP server."""

import time
from contextlib import contextmanager

from src.config.enums import LogLevel
from src.utils.common import log_debug, log_info


def start_timer() -> float:
    """Start a performance timer."""
    return time.perf_counter()


def get_duration(start_time: float) -> float:
    """Get duration since start time in seconds."""
    return time.perf_counter() - start_time


def log_operation_time(
    operation_name: str,
    start_time: float,
    log_level: str = LogLevel.INFO.value,
    extra_info: str = "",
) -> None:
    """Log the duration of an operation."""
    duration = time.perf_counter() - start_time
    message = f"Performance: {operation_name} completed in {duration:.3f}s"
    if extra_info:
        message += f" ({extra_info})"

    if log_level == LogLevel.DEBUG.value:
        log_debug(message)
    else:
        log_info(message)


@contextmanager
def timed_operation(operation_name: str, log_level: str = LogLevel.INFO.value):
    """Context manager for timing operations."""
    start_time = time.perf_counter()
    try:
        yield start_time
    finally:
        try:
            log_operation_time(operation_name, start_time, log_level)
        except (OSError, ValueError, TypeError, AttributeError):
            # Don't let logging errors break gandalf
            pass

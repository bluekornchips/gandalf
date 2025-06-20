"""Performance monitoring utilities for Gandalf MCP server."""

import time
from contextlib import contextmanager
from src.utils.common import log_debug, log_info


def start_timer() -> float:
    """Start a timer and return the start time.

    Returns:
        float: Start time from time.time()
    """
    return time.time()


def log_operation_time(
    operation_name: str, start_time: float, log_level: str = "debug"
):
    """Log operation timing information.

    Args:
        operation_name: Name of the operation being timed
        start_time: Start time from time.time()
        log_level: Logging level ('debug' or 'info')
    """
    duration = time.time() - start_time
    message = f"Performance: {operation_name} completed in {duration:.3f}s"

    if log_level == "info":
        log_info(message)
    else:
        log_debug(message)


@contextmanager
def time_operation(operation_name: str, log_level: str = "debug"):
    """Context manager for timing operations.

    Args:
        operation_name: Name of the operation being timed
        log_level: Logging level ('debug' or 'info')

    Example:
        with time_operation("file_listing"):
            # operation code here
            pass
    """
    start_time = time.time()
    try:
        yield start_time
    finally:
        log_operation_time(operation_name, start_time, log_level)


def get_duration(start_time: float) -> float:
    """Get duration since start time.

    Args:
        start_time: Start time from time.time()

    Returns:
        float: Duration in seconds
    """
    return time.time() - start_time

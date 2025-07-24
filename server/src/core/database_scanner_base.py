"""
Base utilities and data structures for database scanning.

This module provides the core data structures and utilities shared
across database scanning operations.
"""

import signal
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.config.constants.cache import DATABASE_SCANNER_CACHE_TTL
from src.config.constants.limits import DATABASE_SCANNER_TIMEOUT


@contextmanager
def timeout_context(seconds: int) -> Any:
    """Context manager to timeout operations that might hang."""

    def timeout_handler(_signum: int, _frame: Any) -> None:
        """Signal handler for timeout operations."""
        raise TimeoutError(f"Operation timed out after {seconds} seconds")

    # Set the signal handler and a alarm
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)

    try:
        yield
    finally:
        # Restore the old signal handler and cancel the alarm
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


@dataclass
class ConversationDatabase:
    """Represents a conversation database found during scanning."""

    path: str
    tool_type: str
    size_bytes: int
    last_modified: float
    conversation_count: int | None = None
    is_accessible: bool = True
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format for serialization."""
        return {
            "path": self.path,
            "tool_type": self.tool_type,
            "size_bytes": self.size_bytes,
            "last_modified": self.last_modified,
            "conversation_count": self.conversation_count,
            "is_accessible": self.is_accessible,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConversationDatabase":
        """Create instance from dictionary data."""
        return cls(
            path=data["path"],
            tool_type=data["tool_type"],
            size_bytes=data["size_bytes"],
            last_modified=data["last_modified"],
            conversation_count=data.get("conversation_count"),
            is_accessible=data.get("is_accessible", True),
            error_message=data.get("error_message"),
        )

    def get_size_mb(self) -> float:
        """Get file size in megabytes."""
        return self.size_bytes / (1024 * 1024)

    def get_age_hours(self) -> float:
        """Get age of the database in hours."""
        return (time.time() - self.last_modified) / 3600

    def is_recent(self, hours: int = 24) -> bool:
        """Check if database was modified within specified hours."""
        return self.get_age_hours() <= hours

    def is_large(self, mb_threshold: int = 10) -> bool:
        """Check if database exceeds size threshold in MB."""
        return self.get_size_mb() >= mb_threshold


class ScannerConfig:
    """Configuration for database scanner behavior."""

    def __init__(
        self,
        cache_ttl: float = DATABASE_SCANNER_CACHE_TTL,
        scan_timeout: int = DATABASE_SCANNER_TIMEOUT,
        project_root: Path | None = None,
    ) -> None:
        """Initialize scanner configuration."""
        self.cache_ttl = cache_ttl
        self.scan_timeout = scan_timeout
        self.project_root = project_root or Path.cwd()

    def should_rescan(self, last_scan_time: float) -> bool:
        """Determine if a rescan is needed based on cache age."""
        return time.time() - last_scan_time > self.cache_ttl

    def get_full_scan_timeout(self) -> int:
        """Get timeout for full scan operations (double the normal timeout)."""
        return self.scan_timeout * 2


class ScannerCache:
    """Cache management for scanner operations."""

    def __init__(self, config: ScannerConfig) -> None:
        """Initialize scanner cache with configuration."""
        self.config = config
        self._scan_cache: dict[str, list[ConversationDatabase]] = {}
        self._last_scan_time: float = 0.0

    def is_cache_valid(self) -> bool:
        """Check if current cache is still valid."""
        return not self.config.should_rescan(self._last_scan_time)

    def get_cached_databases(self) -> list[ConversationDatabase]:
        """Get cached databases if available and valid."""
        if self.is_cache_valid() and "all" in self._scan_cache:
            return self._scan_cache["all"]
        return []

    def cache_databases(self, databases: list[ConversationDatabase]) -> None:
        """Cache the provided databases."""
        self._scan_cache["all"] = databases
        self._last_scan_time = time.time()

    def cache_tool_databases(
        self, tool_type: str, databases: list[ConversationDatabase]
    ) -> None:
        """Cache databases for a specific tool type."""
        self._scan_cache[tool_type] = databases

    def get_cached_tool_databases(self, tool_type: str) -> list[ConversationDatabase]:
        """Get cached databases for a specific tool type."""
        return self._scan_cache.get(tool_type, [])

    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._scan_cache.clear()
        self._last_scan_time = 0.0

    def get_cache_stats(self) -> dict[str, Any]:
        """Get statistics about the current cache."""
        return {
            "cache_entries": len(self._scan_cache),
            "last_scan_time": self._last_scan_time,
            "cache_age_seconds": time.time() - self._last_scan_time,
            "cache_valid": self.is_cache_valid(),
            "tools_cached": [tool for tool in self._scan_cache.keys() if tool != "all"],
        }


def create_error_database(
    path: str, tool_type: str, error: Exception
) -> ConversationDatabase:
    """Create a ConversationDatabase entry for an error case."""
    return ConversationDatabase(
        path=path,
        tool_type=tool_type,
        size_bytes=0,
        last_modified=0.0,
        conversation_count=None,
        is_accessible=False,
        error_message=str(error),
    )

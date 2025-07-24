"""
Database scanner for detecting conversation databases across different agentic tools.

This module scans the filesystem for conversation databases from supported
agentic tools like Cursor, Claude Code, and Windsurf without requiring
them to be running.
"""

import time
from pathlib import Path
from typing import Any

from src.config.constants.agentic import (
    AGENTIC_TOOL_CLAUDE_CODE,
    AGENTIC_TOOL_CURSOR,
    AGENTIC_TOOL_WINDSURF,
    SUPPORTED_AGENTIC_TOOLS,
)
from src.core.database_scanner_base import (
    ConversationDatabase,
    ScannerCache,
    ScannerConfig,
    timeout_context,
)
from src.core.tool_scanners import (
    ClaudeScanner,
    CursorScanner,
    ScannerFactory,
    WindsurfScanner,
)
from src.utils.common import log_debug, log_error, log_info


class DatabaseScanner:
    """Scanner for detecting conversation databases across agentic tools."""

    def __init__(self, project_root: Path | None = None) -> None:
        """Initialize scanner with project root and configuration."""
        self.config = ScannerConfig(project_root=project_root)
        self.cache = ScannerCache(self.config)
        self.databases: list[ConversationDatabase] = []

    def scan(self, force_rescan: bool = False) -> list[ConversationDatabase]:
        """Scan for conversation databases across all supported agentic tools."""
        # Check registry initialization and provide helpful feedback
        self._validate_registry_setup()

        if not force_rescan:
            cached_databases = self.cache.get_cached_databases()
            if cached_databases:
                log_debug("Using cached database scan results")
                self.databases = cached_databases
                return self.databases

        log_info("Scanning for conversation databases across agentic tools")
        start_time = time.time()

        all_databases = []

        try:
            with timeout_context(self.config.get_full_scan_timeout()):
                # Scan each supported agentic tool type
                for tool_type in SUPPORTED_AGENTIC_TOOLS:
                    try:
                        databases = self._scan_tool_databases(tool_type)
                        all_databases.extend(databases)

                        # Cache tool-specific results
                        self.cache.cache_tool_databases(tool_type, databases)

                        log_info(f"Found {len(databases)} databases for {tool_type}")
                    except (OSError, ValueError, AttributeError) as e:
                        log_error(e, f"scanning {tool_type} databases")
                        continue

            self.databases = all_databases
            self.cache.cache_databases(all_databases)

            scan_duration = time.time() - start_time
            log_info(
                f"Database scan completed in {scan_duration:.2f}s, "
                f"found {len(all_databases)} total databases"
            )

        except TimeoutError as e:
            log_error(
                e,
                f"Full database scan timed out after {self.config.get_full_scan_timeout()} seconds",
            )
        except (OSError, ValueError, AttributeError) as e:
            log_error(e, "scanning all databases")

        return all_databases

    def _scan_tool_databases(self, tool_type: str) -> list[ConversationDatabase]:
        """Scan databases for a specific tool type."""
        scanner: CursorScanner | ClaudeScanner | WindsurfScanner
        if tool_type == AGENTIC_TOOL_CURSOR:
            scanner = ScannerFactory.create_cursor_scanner(self.config.scan_timeout)
            return scanner.scan_databases()
        elif tool_type == AGENTIC_TOOL_CLAUDE_CODE:
            scanner = ScannerFactory.create_claude_scanner(self.config.scan_timeout)
            return scanner.scan_databases()
        elif tool_type == AGENTIC_TOOL_WINDSURF:
            scanner = ScannerFactory.create_windsurf_scanner(self.config.scan_timeout)
            return scanner.scan_databases()
        else:
            log_debug(f"Unknown agentic tool type for scanning: {tool_type}")
            return []

    def get_databases_by_tool(self, tool_type: str) -> list[ConversationDatabase]:
        """Get databases filtered by agentic tool type."""
        if not self.databases:
            self.scan()

        return [db for db in self.databases if db.tool_type == tool_type]

    def get_accessible_databases(self) -> list[ConversationDatabase]:
        """Get only databases that are accessible."""
        if not self.databases:
            self.scan()

        return [db for db in self.databases if db.is_accessible]

    def get_databases_with_conversations(self) -> list[ConversationDatabase]:
        """Get databases that have conversation data."""
        if not self.databases:
            self.scan()

        return [
            db
            for db in self.databases
            if db.is_accessible and (db.conversation_count or 0) > 0
        ]

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of discovered databases."""
        if not self.databases:
            self.scan()

        summary: dict[str, Any] = {
            "total_databases": len(self.databases),
            "accessible_databases": len(self.get_accessible_databases()),
            "databases_with_conversations": len(
                self.get_databases_with_conversations()
            ),
            "total_conversations": sum(
                db.conversation_count or 0 for db in self.databases
            ),
            "tools": {},
            "cache_info": self.cache.get_cache_stats(),
        }

        # Group by agentic tool type
        for tool_type in SUPPORTED_AGENTIC_TOOLS:
            tool_databases = self.get_databases_by_tool(tool_type)
            if tool_databases:  # Only include tools that have databases
                accessible_count = len(
                    [db for db in tool_databases if db.is_accessible]
                )
                with_conversations = len(
                    [
                        db
                        for db in tool_databases
                        if db.is_accessible and (db.conversation_count or 0) > 0
                    ]
                )

                summary["tools"][tool_type] = {
                    "database_count": len(tool_databases),
                    "accessible_count": accessible_count,
                    "with_conversations": with_conversations,
                    "conversation_count": sum(
                        db.conversation_count or 0 for db in tool_databases
                    ),
                    "total_size_mb": sum(db.get_size_mb() for db in tool_databases),
                }

        return summary

    def _validate_registry_setup(self) -> None:
        """Validate that the agentic tools registry is properly initialized."""
        try:
            from src.core.registry import read_registry

            registered_tools = read_registry()

            if not registered_tools:
                log_info(
                    "Registry is empty. Consider running './gandalf registry auto-register' "
                    "to improve conversation detection accuracy."
                )
            else:
                log_debug(
                    f"Registry initialized with tools: {list(registered_tools.keys())}"
                )

                # Check if registered paths exist
                missing_paths = []
                for tool_name, tool_path in registered_tools.items():
                    if not Path(tool_path).exists():
                        missing_paths.append(f"{tool_name}: {tool_path}")

                if missing_paths:
                    log_info(
                        f"Registry contains invalid paths for: {', '.join(missing_paths)}. "
                        "Consider running './gandalf registry auto-register' to update."
                    )

        except Exception as e:
            log_debug(f"Registry validation failed: {e}")

    def get_recent_databases(self, hours: int = 24) -> list[ConversationDatabase]:
        """Get databases modified within specified hours."""
        if not self.databases:
            self.scan()

        return [db for db in self.databases if db.is_recent(hours)]

    def get_large_databases(self, mb_threshold: int = 10) -> list[ConversationDatabase]:
        """Get databases larger than specified threshold in MB."""
        if not self.databases:
            self.scan()

        return [db for db in self.databases if db.is_large(mb_threshold)]

    def clear_cache(self) -> None:
        """Clear the scanner cache to force fresh scans."""
        self.cache.clear_cache()
        self.databases = []

    def get_diagnostics(self) -> dict[str, Any]:
        """Get diagnostic information about the scanner."""
        return {
            "config": {
                "cache_ttl": self.config.cache_ttl,
                "scan_timeout": self.config.scan_timeout,
                "project_root": str(self.config.project_root),
            },
            "cache_stats": self.cache.get_cache_stats(),
            "database_stats": {
                "total_loaded": len(self.databases),
                "accessible": len(self.get_accessible_databases()),
                "with_conversations": len(self.get_databases_with_conversations()),
            },
        }


def get_available_agentic_tools(silent: bool = False) -> list[str]:
    """Get list of agentic tools that have conversation databases available."""
    try:
        with timeout_context(45):  # 45 second timeout for the full operation
            scanner = DatabaseScanner()
            databases = scanner.scan()

            available_tools = set()
            tools_with_databases = set()

            for db in databases:
                tools_with_databases.add(db.tool_type)

                # Consider tool available if database is accessible, even if count is 0
                # This fixes the silent failure issue where databases exist but return 0 conversations
                if db.is_accessible:
                    # If conversation count is None (error), try size-based estimation
                    if db.conversation_count is None and db.size_bytes > 1024:  # > 1KB
                        if not silent:
                            log_info(
                                f"Database accessible but count failed for {db.tool_type}, including anyway"
                            )
                        available_tools.add(db.tool_type)
                    elif (db.conversation_count or 0) > 0:
                        available_tools.add(db.tool_type)
                    elif (
                        db.size_bytes > 10240
                    ):  # > 10KB, likely has data even if count failed
                        if not silent:
                            log_info(
                                f"Large database found for {db.tool_type} with 0 count, including anyway"
                            )
                        available_tools.add(db.tool_type)

            result = list(available_tools)

            if not silent:
                log_info(f"Found databases for tools: {list(tools_with_databases)}")
                log_info(f"Available tools with conversation data: {result}")

                # Log diagnostic info for tools with databases but no conversations
                missing_tools = tools_with_databases - available_tools
                if missing_tools:
                    log_info(
                        f"Tools with databases but no detected conversations: {list(missing_tools)}"
                    )

            return result

    except TimeoutError as e:
        if not silent:
            log_error(
                e,
                "detecting available agentic tools timed out after 45 seconds",
            )
        return []
    except (OSError, ValueError, AttributeError) as e:
        if not silent:
            log_error(e, "detecting available agentic tools")
        return []


def quick_scan_available_tools() -> dict[str, Any]:
    """Quick scan to get available tools without full database analysis."""
    scanner = DatabaseScanner()
    summary = scanner.get_summary()

    available_tools = []
    for tool_type, stats in summary.get("tools", {}).items():
        if stats.get("with_conversations", 0) > 0:
            available_tools.append(tool_type)

    return {
        "available_tools": available_tools,
        "summary": summary,
        "scan_timestamp": time.time(),
    }

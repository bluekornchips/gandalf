"""
Project-level operations for Gandalf MCP server.
"""

import json
import subprocess  # nosec B404 - safe git/find operations with fixed commands
import time
from pathlib import Path
from typing import Any

from src.config.constants.server_config import (
    GANDALF_SERVER_VERSION,
    MCP_PROTOCOL_VERSION,
    SUBPROCESS_TIMEOUT,
)
from src.core.file_scoring import get_files_list
from src.utils.access_control import AccessValidator, create_mcp_tool_result
from src.utils.common import log_debug, log_error, log_info
from src.utils.performance import get_duration, start_timer
from src.utils.project import ProjectContext


def validate_project_root(project_root: Path) -> bool:
    """Validate project root exists and is accessible."""
    try:
        return project_root.exists() and project_root.is_dir()
    except (OSError, PermissionError):
        log_debug(f"Project root does not exist: {project_root}")
        return False


def get_git_info(project_root: Path) -> dict[str, Any]:
    """Get Git repository information."""

    git_info: dict[str, Any] = {}

    log_debug(f"Checking if {project_root} is a git repository")

    try:
        result = subprocess.run(  # nosec B603,B607 - safe read-only git operation with fixed command array
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=SUBPROCESS_TIMEOUT,
            check=False,
        )

        if result.returncode == 0:
            git_info["is_git_repo"] = True
            log_debug(f"Project {project_root} is a git repository")

            try:
                result = subprocess.run(  # nosec B603,B607 - safe read-only git operation with fixed command array
                    ["git", "branch", "--show-current"],
                    cwd=project_root,
                    capture_output=True,
                    text=True,
                    timeout=SUBPROCESS_TIMEOUT,
                    check=False,
                )
                if result.returncode == 0:
                    git_info["current_branch"] = result.stdout.strip()
                    log_debug(f"Current branch: {git_info['current_branch']}")

            except (
                subprocess.SubprocessError,
                subprocess.TimeoutExpired,
                OSError,
            ):
                log_debug(f"Failed to get current branch for {project_root}")

            try:
                result = subprocess.run(  # nosec B603,B607 - safe read-only git operation with fixed command array
                    ["git", "rev-parse", "--show-toplevel"],
                    cwd=project_root,
                    capture_output=True,
                    text=True,
                    timeout=SUBPROCESS_TIMEOUT,
                    check=False,
                )

                if result.returncode == 0:
                    git_info["repo_root"] = result.stdout.strip()
                    log_debug(f"Repository root: {git_info['repo_root']}")

            except (
                subprocess.SubprocessError,
                subprocess.TimeoutExpired,
                OSError,
            ):
                log_debug(f"Failed to get repository root for {project_root}")
        else:
            git_info["is_git_repo"] = False
            log_info(f"Project {project_root} is not a git repository")

    except (
        subprocess.SubprocessError,
        subprocess.TimeoutExpired,
        OSError,
    ) as e:
        git_info["is_git_repo"] = False
        git_info["error"] = str(e)
        log_error(e, f"get_git_info for {project_root}")

    return git_info


def _get_file_stats_fast(project_root: Path) -> dict[str, Any]:
    """Get file statistics using fast shell 'find' commands."""
    try:
        file_result = subprocess.run(  # nosec B603,B607 - safe read-only find operation with fixed command array
            ["find", str(project_root), "-type", "f"],
            capture_output=True,
            text=True,
            timeout=SUBPROCESS_TIMEOUT,
            check=False,
        )

        dir_result = subprocess.run(  # nosec B603,B607 - safe read-only find operation with fixed command array
            ["find", str(project_root), "-type", "d"],
            capture_output=True,
            text=True,
            timeout=SUBPROCESS_TIMEOUT,
            check=False,
        )

        if file_result.returncode == 0 and dir_result.returncode == 0:
            lines = [line for line in file_result.stdout.splitlines() if line.strip()]
            file_count = len(lines)
            dir_lines = [
                line for line in dir_result.stdout.splitlines() if line.strip()
            ]
            dir_count = max(0, len(dir_lines) - 1)  # Exclude root

            return {
                "total_files": file_count,
                "total_directories": max(0, dir_count),
                "method": "find_command",
            }
        else:
            log_debug(f"Find command failed for {project_root}")
            return {
                "total_files": 0,
                "total_directories": 0,
                "method": "find_failed",
            }

    except (
        subprocess.SubprocessError,
        subprocess.TimeoutExpired,
        OSError,
    ) as e:
        log_debug(f"Find command failed for {project_root}: {e}")
        return {
            "total_files": 0,
            "total_directories": 0,
            "method": "find_error",
        }


def _get_file_stats_with_cache_optimization(
    project_root: Path,
) -> dict[str, Any]:
    """Get file statistics with cache optimization for performance."""
    try:
        # Try to get cached files first for optimization
        cached_files = get_files_list(project_root)

        if cached_files:
            # Use cached count as baseline and just count directories with find
            dir_result = subprocess.run(  # nosec B603,B607 - safe read-only find operation with fixed command array
                ["find", str(project_root), "-type", "d"],
                capture_output=True,
                text=True,
                timeout=SUBPROCESS_TIMEOUT,
                check=False,
            )

            if dir_result.returncode == 0:
                # Count directories, excluding the root directory itself
                dir_lines = [
                    line for line in dir_result.stdout.splitlines() if line.strip()
                ]
                dir_count = max(0, len(dir_lines) - 1)

                return {
                    "total_files": len(cached_files),
                    "total_directories": dir_count,
                    "method": "cached_optimized",
                }

        # Fallback when cache is not available
        return _get_file_stats_fast(project_root)

    except (
        subprocess.SubprocessError,
        subprocess.TimeoutExpired,
        OSError,
        ValueError,
    ) as e:
        log_debug(f"Cache optimization failed for {project_root}: {e}")
        return _get_file_stats_fast(project_root)


def _get_file_statistics(project_root: Path) -> dict[str, Any]:
    """Get file statistics using the most efficient method available."""
    if not project_root.exists():
        return {
            "total_files": 0,
            "total_directories": 0,
            "method": "path_not_found",
        }

    # Try cache-optimized method first, then fallback to 'find'
    try:
        return _get_file_stats_with_cache_optimization(project_root)
    except (OSError, ValueError) as e:
        log_debug(f"Cache optimization failed, using 'find': {e}")
        return _get_file_stats_fast(project_root)


def _create_basic_project_info(project_root: Path) -> dict[str, Any]:
    """Create basic project information structure."""
    # Use ProjectContext for consistent project name handling
    context = ProjectContext.from_path(project_root)

    project_info = {
        "project_root": str(project_root),
        "project_name": context.sanitized_name,
        "timestamp": time.time(),
        "valid_path": validate_project_root(project_root),
    }

    # Add transparency fields from ProjectContext
    project_info.update(context.get_transparency_fields())

    return project_info


def get_project_info(project_root: Path) -> dict[str, Any]:
    """

    Creates a comprehensive project information object, including:
    - Basic project information
    - Git information
    - File statistics
    - Processing time
    """
    start_time = start_timer()

    project_info = _create_basic_project_info(project_root)
    project_info["git"] = get_git_info(project_root)
    project_info["file_stats"] = _get_file_statistics(project_root)
    project_info["processing_time"] = get_duration(start_time)

    return project_info


def handle_get_project_info(
    arguments: dict[str, Any], project_root: Path, **_kwargs: Any
) -> dict[str, Any]:
    """Handle get_project_info tool call."""
    try:
        include_stats = arguments.get("include_stats", True)

        if not isinstance(include_stats, bool):
            return AccessValidator.create_error_response(
                "include_stats must be a boolean"
            )

        # Always return project info with valid_path set appropriately
        # rather than returning an error for nonexistent paths
        if include_stats:
            project_info = get_project_info(project_root)
        else:
            log_debug(f"Getting project info without stats for {project_root}")
            # Use consistent sanitization even without stats
            basic_info = _create_basic_project_info(project_root)
            project_info = {
                "project_root": basic_info["project_root"],
                "project_name": basic_info["project_name"],
                "timestamp": basic_info["timestamp"],
                "valid_path": basic_info["valid_path"],
                "sanitized": basic_info["sanitized"],
            }
            # Include raw name if it was sanitized for transparency
            if "raw_project_name" in basic_info:
                project_info["raw_project_name"] = basic_info["raw_project_name"]

        log_info(f"Retrieved project info for {project_root}")

        structured_data: dict[str, Any] = {
            "summary": {
                "project_root": project_info.get("project_root"),
                "project_name": project_info.get("project_name"),
                "is_git_repo": project_info.get("git", {}).get("is_git_repo", False),
                "current_branch": project_info.get("git", {}).get("current_branch"),
                "repo_root": project_info.get("git", {}).get("repo_root"),
                "file_count": project_info.get("file_stats", {}).get("total_files"),
                "directory_count": project_info.get("file_stats", {}).get(
                    "total_directories"
                ),
            },
            "project": {
                "valid": project_info.get("valid_path", True),
                "root": project_info.get("project_root"),
                "name": project_info.get("project_name"),
            },
            "metadata": {
                "sanitized": project_info.get("sanitized", False),
                "timestamp": project_info.get("timestamp", time.time()),
            },
            "conversations": [],
            "status": "project_info_retrieved",
        }

        if "raw_project_name" in project_info:
            structured_data["summary"]["original_name"] = project_info[
                "raw_project_name"
            ]
            structured_data["project"]["original_name"] = project_info[
                "raw_project_name"
            ]

        content_text = json.dumps(project_info, indent=2)
        return create_mcp_tool_result(content_text, structured_data)

    except (OSError, ValueError, TypeError, KeyError) as e:
        log_error(e, f"get_project_info for {project_root}")
        return AccessValidator.create_error_response(
            f"Error retrieving project info: {str(e)}"
        )


def handle_get_server_version(
    arguments: dict[str, Any],
    *,
    project_root: Path,
    **_kwargs: Any,  # noqa: ARG001
) -> dict[str, Any]:
    """Handle get_server_version tool call."""
    try:
        log_debug("Getting server version")

        timestamp = time.time()

        # Full structured data for MCP compliance
        structured_data = {
            "server_name": "gandalf",
            "server_version": GANDALF_SERVER_VERSION,
            "protocol_version": MCP_PROTOCOL_VERSION,
            "timestamp": timestamp,
            "capabilities": {
                "tools": {"conversation_aggregation": True, "project_analysis": True},
                "logging": {"level": "info"},
            },
        }

        mcp_structured_data = {
            "summary": {
                "server_name": "gandalf",
                "server_version": GANDALF_SERVER_VERSION,
                "protocol_version": MCP_PROTOCOL_VERSION,
                "timestamp": timestamp,
            },
            "capabilities": {
                "tools": {"conversation_aggregation": True, "project_analysis": True},
                "logging": {"level": "info"},
            },
            "status": "version_retrieved",
        }

        log_debug(f"Retrieved server version: {GANDALF_SERVER_VERSION}")

        content_text = json.dumps(structured_data, indent=2)
        return create_mcp_tool_result(content_text, mcp_structured_data)

    except (OSError, ValueError, RuntimeError) as e:
        log_error(e, "get_server_version")
        return AccessValidator.create_error_response(
            f"Error retrieving server version: {str(e)}"
        )


TOOL_GET_PROJECT_INFO = {
    "name": "get_project_info",
    "title": "Project Information & Statistics",
    "description": "Get project information including metadata and statistics",
    "inputSchema": {
        "type": "object",
        "properties": {
            "include_stats": {
                "type": "boolean",
                "default": True,
                "description": "Include file count and size statistics",
            }
        },
        "required": [],
    },
    "annotations": {
        "title": "Get Project Information",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
}


TOOL_GET_SERVER_VERSION = {
    "name": "get_server_version",
    "title": "Get Server Version",
    "description": "Get the current server version and protocol information",
    "inputSchema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
    "annotations": {
        "title": "Get Server Version",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
}


PROJECT_TOOL_HANDLERS = {
    "get_project_info": handle_get_project_info,
    "get_server_version": handle_get_server_version,
}

PROJECT_TOOL_DEFINITIONS = [
    TOOL_GET_PROJECT_INFO,
    TOOL_GET_SERVER_VERSION,
]

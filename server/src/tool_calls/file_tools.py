"""
File operations tools for the Gandalf MCP server.
"""

import json
from pathlib import Path
from typing import Any

from src.config.conversation_config import (
    HIGH_PRIORITY_DISPLAY_LIMIT,
    LOW_PRIORITY_DISPLAY_LIMIT,
    MAX_FILES_LIMIT,
    MEDIUM_PRIORITY_DISPLAY_LIMIT,
    TOP_FILES_DISPLAY_LIMIT,
)
from src.config.core_constants import (
    MAX_FILE_TYPES,
    MAX_PROJECT_FILES,
)
from src.core.file_scoring import (
    clear_file_scores,
    get_files_list,
    get_files_with_scores,
)
from src.utils.access_control import (
    AccessValidator,
    create_mcp_tool_result,
    validate_file_types,
)
from src.utils.common import log_debug
from src.utils.performance import log_operation_time, start_timer


def validate_max_files(max_files: int) -> tuple[bool, str]:
    """Validate max_files parameter."""

    if max_files < 1:
        return False, "max_files must be at least 1"

    if max_files > MAX_FILES_LIMIT:
        return False, f"max_files cannot exceed {MAX_FILES_LIMIT}"

    return True, ""


TOOL_LIST_PROJECT_FILES = {
    "name": "list_project_files",
    "title": "List Project Files",
    "description": "List project files with relevance scoring and filtering",
    "inputSchema": {
        "type": "object",
        "properties": {
            "file_types": {
                "type": "array",
                "items": {"type": "string"},
                "maxItems": MAX_FILE_TYPES,
                "description": "Filter by file extensions (e.g., ['.py', '.js', '.md'])",
            },
            "max_files": {
                "type": "integer",
                "minimum": 1,
                "maximum": MAX_FILES_LIMIT,
                "default": 1000,
                "description": "Maximum number of files to return",
            },
            "use_relevance_scoring": {
                "type": "boolean",
                "default": True,
                "description": "Enable relevance scoring and prioritization",
            },
            "scoring_enabled": {
                "type": "boolean",
                "default": True,
                "description": "Enable relevance scoring and prioritization (alias for use_relevance_scoring)",
            },
        },
        "required": [],
    },
    "annotations": {
        "title": "List Project Files",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
}


def handle_list_project_files(  # noqa: C901
    arguments: dict[str, Any], project_root: Path, **kwargs: Any
) -> dict[str, Any]:
    """Handle list_project_files tool call with enhanced security and error handling."""
    start_time = start_timer()

    try:
        file_types = arguments.get("file_types", [])
        max_files = arguments.get("max_files", MAX_PROJECT_FILES)
        # Support both parameter names for backward compatibility
        use_relevance_scoring = arguments.get("use_relevance_scoring") or arguments.get(
            "scoring_enabled", False
        )

        # Validate file_types parameter
        valid, error = validate_file_types(file_types)
        if not valid:
            return AccessValidator.create_error_response(error)

        # Validate scoring_enabled parameter
        if use_relevance_scoring is not None and not isinstance(
            use_relevance_scoring, bool
        ):
            return AccessValidator.create_error_response(
                "scoring_enabled must be a boolean"
            )

        # Validate max_files parameter
        if not isinstance(max_files, int) or max_files < 1:
            return AccessValidator.create_error_response(
                "max_files must be a positive integer"
            )

        if max_files > MAX_FILES_LIMIT:
            return AccessValidator.create_error_response(
                f"max_files cannot exceed {MAX_FILES_LIMIT}"
            )

        # project_root
        valid, error_msg = AccessValidator.validate_path(project_root, "project_root")
        if not valid:
            return AccessValidator.create_error_response(error_msg)

        if not project_root.exists() or not project_root.is_dir():
            return AccessValidator.create_error_response(
                "Invalid project root directory"
            )

        # Apply file filtering and scoring
        if use_relevance_scoring:
            log_debug("Using relevance scoring for file prioritization")
            scored_files = get_files_with_scores(project_root)

            # Re check security for cached files, no tricks
            if not _validate_cache_security(project_root, scored_files):
                log_debug("Cache security validation failed, refreshing cache")
                clear_file_scores(project_root)
                scored_files = get_files_with_scores(project_root)

            # Apply file type filtering if specified
            if file_types:
                filtered_scored_files: list[tuple[str, float]] = []
                extensions = set()
                for file_type in file_types:
                    if file_type.startswith("."):
                        extensions.add(file_type.lower())
                    else:
                        extensions.add(f".{file_type.lower()}")

                for item in scored_files:
                    try:
                        file_path, score = item
                        path_obj = Path(file_path)
                        if path_obj.suffix.lower() in extensions:
                            filtered_scored_files.append((file_path, score))
                    except OSError as e:
                        log_debug(f"Skipping file due to path error: {file_path}, {e}")
                        continue
                    except (TypeError, IndexError) as e:
                        log_debug(
                            f"Unexpected error unpacking scored file: {item}, error: {e}"
                        )
                        continue
                scored_files = filtered_scored_files

            # Sort by score: higher should always be first. Limit results.
            sorted_files = sorted(scored_files, key=lambda x: x[1], reverse=True)
            if max_files:
                sorted_files = sorted_files[:max_files]

            files_to_return = [f[0] for f in sorted_files]
            scores = {f[0]: f[1] for f in sorted_files}

            # Formatted output with priority levels
            high_priority = []
            medium_priority = []
            low_priority = []

            for f, s in scores.items():
                if s >= 0.8:
                    high_priority.append(f)
                elif 0.5 <= s < 0.8:
                    medium_priority.append(f)
                else:
                    low_priority.append(f)

            output_lines = []

            if high_priority:
                output_lines.append("HIGH PRIORITY FILES:")
                for file in high_priority[:HIGH_PRIORITY_DISPLAY_LIMIT]:
                    output_lines.append(f"  {file}")

            if medium_priority:
                output_lines.append("\nMEDIUM PRIORITY FILES:")
                for file in medium_priority[:MEDIUM_PRIORITY_DISPLAY_LIMIT]:
                    output_lines.append(f"  {file}")

            if low_priority:
                output_lines.append("\nLOW PRIORITY FILES:")
                for file in low_priority[:LOW_PRIORITY_DISPLAY_LIMIT]:
                    output_lines.append(f"  {file}")

            output_lines.append("\nTOP FILES BY RELEVANCE:")
            top_files = sorted_files[: min(TOP_FILES_DISPLAY_LIMIT, len(sorted_files))]
            for item in top_files:
                try:
                    file, score = item
                    output_lines.append(f"  {file} (score: {score:.2f})")
                except (TypeError, IndexError) as e:
                    log_debug(f"Error unpacking top file: {item}, error: {e}")
                    continue

            output_lines.append(f"\nSUMMARY: {len(files_to_return)} total files")
            output_lines.append(f"High priority: {len(high_priority)}")
            output_lines.append(f"Medium priority: {len(medium_priority)}")
            output_lines.append(f"Low priority: {len(low_priority)}")

            formatted_output = "\n".join(output_lines)

        else:
            log_debug("Using simple file listing without relevance scoring")
            files = get_files_list(project_root)

            if file_types:
                filtered_string_files: list[str] = []
                extensions = set()
                for file_type in file_types:
                    if file_type.startswith("."):
                        extensions.add(file_type.lower())
                    else:
                        extensions.add(f".{file_type.lower()}")

                for file_path in files:
                    try:
                        path_obj = Path(file_path)
                        if path_obj.suffix.lower() in extensions:
                            filtered_string_files.append(file_path)
                    except (OSError, ValueError) as e:
                        log_debug(f"Skipping file due to path error: {file_path}, {e}")
                        continue
                files = filtered_string_files

            if max_files:
                files = files[:max_files]

            formatted_output = f"FILES ({len(files)} total):\n" + "\n".join(
                f"  {f}" for f in files
            )

        # Create structured content for MCP 2025-06-18
        if use_relevance_scoring:
            structured_data = {
                "files": files_to_return,  # Array of strings as expected by schema
                "total_files": len(files_to_return),
                "project_root": str(project_root),
                "scoring_enabled": True,
                "file_types_filter": file_types if file_types else [],
            }
        else:
            structured_data = {
                "files": files,  # Array of strings as expected by schema
                "total_files": len(files),
                "project_root": str(project_root),
                "scoring_enabled": False,
                "file_types_filter": file_types if file_types else [],
            }

        log_operation_time("list_project_files", start_time)

        # Provide different text content based on use_relevance_scoring
        # When relevance scoring is enabled: formatted text for shell tests
        # When relevance scoring is disabled: JSON for Python tests
        if use_relevance_scoring:
            content_text = formatted_output
        else:
            content_text = json.dumps(structured_data, indent=2)

        return create_mcp_tool_result(content_text, structured_data)

    except (OSError, ValueError, TypeError, KeyError) as e:
        log_debug(f"Error in list_project_files: {e}")
        return AccessValidator.create_error_response(f"Error listing files: {str(e)}")


def _validate_cache_security(
    project_root: Path, scored_files: list[tuple[str, float]]
) -> bool:
    """Validate that cached files are still within project boundaries."""
    try:
        project_root_str = str(project_root.resolve())

        for item in scored_files:
            try:
                file_path, _ = item
                resolved_path = Path(file_path).resolve()
                if not str(resolved_path).startswith(project_root_str):
                    log_debug(f"Security: File outside project root: {file_path}")
                    return False
            except OSError as e:
                log_debug(f"Security: Invalid file path in cache: {file_path}, {e}")
                return False
            except (TypeError, ValueError, IndexError) as e:
                log_debug(f"Security: Error unpacking scored file: {item}, error: {e}")
                return False

        return True
    except (OSError, ValueError, PermissionError) as e:
        log_debug(f"Security validation error: {e}")
        return False


FILE_TOOL_HANDLERS = {
    "list_project_files": handle_list_project_files,
}

FILE_TOOL_DEFINITIONS = [
    TOOL_LIST_PROJECT_FILES,
]
